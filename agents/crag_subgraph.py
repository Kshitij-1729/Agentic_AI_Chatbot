"""
CRAG (Corrective Retrieval-Augmented Generation) Subgraph.

Implements the full CRAG pipeline using the same core logic as the reference:
  retrieve → eval_docs → [route]
    → CORRECT:                refine → generate → END
    → INCORRECT / AMBIGUOUS:  rewrite_query → web_search → refine → generate → END

Key features:
  - Uses the project's ChromaDB vector store (shared with rag_tool)
  - Uses OpenAI gpt-4o-mini for evaluation, filtering, rewriting, generation
  - Uses Tavily for corrective web search
  - Sentence-level decomposition + LLM filtering for refined context
  - Pydantic structured outputs for reliable schema adherence
"""

import re
import json
import time as _time
from typing import List, TypedDict

from pydantic import BaseModel
from langchain_core.documents import Document
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.graph import StateGraph, START, END

from agents.state import AgentState
from tools.rag_tool import get_vectorstore
from config import Config


# ═══════════════════════════════════════════════════════════
#  THRESHOLDS (same as reference implementation)
# ═══════════════════════════════════════════════════════════

UPPER_TH = 0.7   # Score above this → CORRECT
LOWER_TH = 0.3   # Score below this → INCORRECT


# ═══════════════════════════════════════════════════════════
#  CRAG INTERNAL STATE
# ═══════════════════════════════════════════════════════════

class CRAGState(TypedDict):
    question: str               # User's original question
    docs: list                  # Raw retrieved documents from vector store
    good_docs: list             # Docs that passed relevance threshold
    verdict: str                # "CORRECT", "INCORRECT", or "AMBIGUOUS"
    reason: str                 # Human-readable explanation for the verdict
    strips: list                # All sentences extracted from context
    kept_strips: list           # Sentences kept after LLM filtering
    refined_context: str        # Final clean context for generation
    web_query: str              # Rewritten query for web search
    web_docs: list              # Documents fetched from Tavily
    answer: str                 # Final generated answer


# ═══════════════════════════════════════════════════════════
#  PYDANTIC MODELS (structured output schemas)
# ═══════════════════════════════════════════════════════════

class DocEvalScore(BaseModel):
    """Relevance score for a single retrieved chunk."""
    score: float   # 0.0 to 1.0
    reason: str    # Short explanation


class KeepOrDrop(BaseModel):
    """Whether to keep a sentence in the refined context."""
    keep: bool


class WebQuery(BaseModel):
    """Rewritten web search query."""
    query: str


# ═══════════════════════════════════════════════════════════
#  PROMPTS (same logic as reference implementation)
# ═══════════════════════════════════════════════════════════

doc_eval_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a strict retrieval evaluator for RAG.\n"
        "You will be given ONE retrieved chunk and a question.\n"
        "Return a relevance score in [0.0, 1.0].\n"
        "- 1.0: chunk alone is sufficient to answer fully/mostly\n"
        "- 0.0: chunk is irrelevant\n"
        "Be conservative with high scores.\n"
        "Also return a short reason.\n"
        "Output JSON only.",
    ),
    ("human", "Question: {question}\n\nChunk:\n{chunk}"),
])

filter_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a strict relevance filter.\n"
        "Return keep=true only if the sentence directly helps answer the question.\n"
        "Use ONLY the sentence. Output JSON only.",
    ),
    ("human", "Question: {question}\n\nSentence:\n{sentence}"),
])

rewrite_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "Rewrite the user question into a web search query composed of keywords.\n"
        "Rules:\n"
        "- Keep it short (6-14 words).\n"
        "- If the question implies recency (e.g., recent/latest/last week/last month), "
        "add a constraint like (last 30 days).\n"
        "- Do NOT answer the question.\n"
        "- Return JSON with a single key: query",
    ),
    ("human", "Question: {question}"),
])

answer_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a knowledgeable and helpful assistant. "
        "Answer the question ONLY using the provided context.\n"
        "If the context is empty or insufficient, say: "
        "'I don't have enough information to answer this question.'\n"
        "Be clear, well-structured, and use markdown formatting.",
    ),
    ("human", "Question: {question}\n\nContext:\n{context}"),
])


# ═══════════════════════════════════════════════════════════
#  LLM FACTORY
# ═══════════════════════════════════════════════════════════

def _get_crag_llm():
    """Return OpenAI LLM for CRAG pipeline (gpt-4o-mini, temp=0)."""
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=Config.OPENAI_API_KEY,
    )


# ═══════════════════════════════════════════════════════════
#  HELPER: SENTENCE DECOMPOSER
# ═══════════════════════════════════════════════════════════

def decompose_to_sentences(text: str) -> List[str]:
    """Normalize whitespace and split on sentence-ending punctuation."""
    text = re.sub(r"\s+", " ", text).strip()
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if len(s.strip()) > 20]


# ═══════════════════════════════════════════════════════════
#  NODE 1: RETRIEVE — top-4 from ChromaDB
# ═══════════════════════════════════════════════════════════

def crag_retrieve_node(state: CRAGState) -> dict:
    """Fetch top-4 relevant chunks from the project's ChromaDB vector store."""
    try:
        vectorstore = get_vectorstore()
        results = vectorstore.similarity_search(state["question"], k=4)
        print(f"[CRAG Retrieve] Found {len(results)} chunks")
        return {"docs": results}
    except Exception as e:
        print(f"[CRAG Retrieve] Error: {e}")
        return {"docs": []}


# ═══════════════════════════════════════════════════════════
#  NODE 2: EVALUATE EACH DOCUMENT
#  Score 0.0–1.0, classify verdict: CORRECT / INCORRECT / AMBIGUOUS
# ═══════════════════════════════════════════════════════════

def crag_eval_docs_node(state: CRAGState) -> dict:
    """
    Score each retrieved chunk and assign overall verdict.
    Same logic as reference: CORRECT (any > 0.7), INCORRECT (all < 0.3), else AMBIGUOUS.
    """
    docs = state.get("docs", [])

    if not docs:
        return {
            "good_docs": [],
            "verdict": "INCORRECT",
            "reason": "No documents found in the knowledge base.",
        }

    llm = _get_crag_llm()
    eval_chain = doc_eval_prompt | llm.with_structured_output(DocEvalScore)

    q = state["question"]
    scores: List[float] = []
    good: List[Document] = []

    for d in docs:
        try:
            out = eval_chain.invoke({"question": q, "chunk": d.page_content})
            scores.append(out.score)
            if out.score > LOWER_TH:
                good.append(d)
        except Exception as e:
            print(f"[CRAG Eval] Error scoring chunk: {e}")
            scores.append(0.0)

    # CORRECT: at least one chunk is highly relevant
    if any(s > UPPER_TH for s in scores):
        print(f"[CRAG Eval] Verdict: CORRECT (max score = {max(scores):.2f})")
        return {
            "good_docs": good,
            "verdict": "CORRECT",
            "reason": f"At least one retrieved chunk scored > {UPPER_TH}.",
        }

    # INCORRECT: all chunks are irrelevant
    if all(s < LOWER_TH for s in scores):
        print(f"[CRAG Eval] Verdict: INCORRECT (max score = {max(scores):.2f})")
        return {
            "good_docs": [],
            "verdict": "INCORRECT",
            "reason": f"All retrieved chunks scored < {LOWER_TH}.",
        }

    # AMBIGUOUS: partial relevance
    print(f"[CRAG Eval] Verdict: AMBIGUOUS (scores = {scores})")
    return {
        "good_docs": good,
        "verdict": "AMBIGUOUS",
        "reason": f"No chunk scored > {UPPER_TH}, but not all were < {LOWER_TH}.",
    }


# ═══════════════════════════════════════════════════════════
#  NODE 3: REWRITE QUERY (for web search)
# ═══════════════════════════════════════════════════════════

def crag_rewrite_query_node(state: CRAGState) -> dict:
    """Rewrite the user question into concise web search keywords."""
    llm = _get_crag_llm()
    chain = rewrite_prompt | llm.with_structured_output(WebQuery)
    try:
        out = chain.invoke({"question": state["question"]})
        print(f"[CRAG Rewrite] Web query: {out.query}")
        return {"web_query": out.query}
    except Exception as e:
        print(f"[CRAG Rewrite] Error: {e}")
        return {"web_query": state["question"]}


# ═══════════════════════════════════════════════════════════
#  NODE 4: WEB SEARCH (Tavily)
# ═══════════════════════════════════════════════════════════

def crag_web_search_node(state: CRAGState) -> dict:
    """Run Tavily search and wrap results as LangChain Documents."""
    tavily = TavilySearchResults(max_results=5, api_key=Config.TAVILY_API_KEY)
    q = state.get("web_query") or state["question"]

    try:
        results = tavily.invoke({"query": q})
        web_docs: List[Document] = []
        for r in results or []:
            title = r.get("title", "")
            url = r.get("url", "")
            content = r.get("content", "") or r.get("snippet", "")
            text = f"TITLE: {title}\nURL: {url}\nCONTENT:\n{content}"
            web_docs.append(Document(
                page_content=text,
                metadata={"url": url, "title": title},
            ))
        print(f"[CRAG Web Search] Found {len(web_docs)} web results")
        return {"web_docs": web_docs}
    except Exception as e:
        print(f"[CRAG Web Search] Error: {e}")
        return {"web_docs": []}


# ═══════════════════════════════════════════════════════════
#  NODE 5: REFINE CONTEXT
#  Sentence decomposition + LLM filtering
# ═══════════════════════════════════════════════════════════

def crag_refine_node(state: CRAGState) -> dict:
    """
    Select document pool based on verdict, decompose into sentences,
    and filter each sentence for relevance via LLM.
      CORRECT   → use only good_docs
      INCORRECT → use only web_docs
      AMBIGUOUS → merge both
    """
    llm = _get_crag_llm()
    filt_chain = filter_prompt | llm.with_structured_output(KeepOrDrop)

    q = state["question"]
    verdict = state.get("verdict", "AMBIGUOUS")

    if verdict == "CORRECT":
        docs_to_use = state.get("good_docs", [])
    elif verdict == "INCORRECT":
        docs_to_use = state.get("web_docs", [])
    else:  # AMBIGUOUS: blend internal + web
        docs_to_use = state.get("good_docs", []) + state.get("web_docs", [])

    if not docs_to_use:
        return {"strips": [], "kept_strips": [], "refined_context": ""}

    context = "\n\n".join(d.page_content for d in docs_to_use).strip()
    strips = decompose_to_sentences(context)

    kept: List[str] = []
    for s in strips:
        try:
            if filt_chain.invoke({"question": q, "sentence": s}).keep:
                kept.append(s)
        except Exception as e:
            print(f"[CRAG Refine] Error filtering sentence: {e}")

    refined_context = "\n".join(kept).strip()
    print(f"[CRAG Refine] Kept {len(kept)} / {len(strips)} sentences")

    return {
        "strips": strips,
        "kept_strips": kept,
        "refined_context": refined_context,
    }


# ═══════════════════════════════════════════════════════════
#  NODE 6: GENERATE ANSWER
# ═══════════════════════════════════════════════════════════

def crag_generate_node(state: CRAGState) -> dict:
    """Produce the final answer from the refined context."""
    llm = _get_crag_llm()
    context = state.get("refined_context", "")

    if not context:
        return {
            "answer": "I don't have enough information to answer this question "
                      "based on the available documents and web search.",
        }

    try:
        out = (answer_prompt | llm).invoke({
            "question": state["question"],
            "context": context,
        })
        return {"answer": out.content}
    except Exception as e:
        print(f"[CRAG Generate] Error: {e}")
        return {"answer": f"An error occurred while generating the answer: {e}"}


# ═══════════════════════════════════════════════════════════
#  ROUTING LOGIC
# ═══════════════════════════════════════════════════════════

def route_after_eval(state: CRAGState) -> str:
    """
    CORRECT   → skip web search, go straight to refine
    INCORRECT / AMBIGUOUS → rewrite query → web search → refine
    """
    if state.get("verdict") == "CORRECT":
        return "refine"
    return "rewrite_query"


# ═══════════════════════════════════════════════════════════
#  BUILD & COMPILE INTERNAL CRAG PIPELINE
# ═══════════════════════════════════════════════════════════

def _build_crag_pipeline():
    """
    Build the internal CRAG LangGraph pipeline.

    Flow:
      START → retrieve → eval_docs → [conditional]
        → CORRECT:              refine → generate → END
        → INCORRECT/AMBIGUOUS:  rewrite_query → web_search → refine → generate → END
    """
    builder = StateGraph(CRAGState)

    builder.add_node("retrieve",      crag_retrieve_node)
    builder.add_node("eval_docs",     crag_eval_docs_node)
    builder.add_node("rewrite_query", crag_rewrite_query_node)
    builder.add_node("web_search",    crag_web_search_node)
    builder.add_node("refine",        crag_refine_node)
    builder.add_node("generate",      crag_generate_node)

    builder.add_edge(START, "retrieve")
    builder.add_edge("retrieve", "eval_docs")

    builder.add_conditional_edges(
        "eval_docs",
        route_after_eval,
        {
            "refine":        "refine",         # CORRECT path
            "rewrite_query": "rewrite_query",  # INCORRECT / AMBIGUOUS path
        },
    )

    builder.add_edge("rewrite_query", "web_search")
    builder.add_edge("web_search",    "refine")
    builder.add_edge("refine",        "generate")
    builder.add_edge("generate",      END)

    return builder.compile()


# Pre-compile the internal CRAG pipeline at module load
_crag_pipeline = _build_crag_pipeline()
print("[CRAG] Internal CRAG pipeline compiled successfully")


# ═══════════════════════════════════════════════════════════
#  PUBLIC API — WRAPPER FUNCTION
#  Bridges parent AgentState ↔ internal CRAGState
# ═══════════════════════════════════════════════════════════

def crag_subgraph(state: AgentState) -> dict:
    """
    CRAG subgraph entry point for the main workflow.

    Receives the parent graph's AgentState, runs the full CRAG pipeline
    internally, and returns state updates (messages + agent_response)
    compatible with the parent graph.
    """
    user_input = state.get("user_input", "")
    start_time = _time.time()

    # Initialize internal CRAG state
    initial_crag_state: CRAGState = {
        "question":        user_input,
        "docs":            [],
        "good_docs":       [],
        "verdict":         "",
        "reason":          "",
        "strips":          [],
        "kept_strips":     [],
        "refined_context": "",
        "web_query":       "",
        "web_docs":        [],
        "answer":          "",
    }

    try:
        result = _crag_pipeline.invoke(initial_crag_state)

        elapsed_ms = int((_time.time() - start_time) * 1000)

        answer     = result.get("answer", "I couldn't find a relevant answer.")
        verdict    = result.get("verdict", "unknown")
        reason     = result.get("reason", "")
        web_query  = result.get("web_query", "")
        num_docs   = len(result.get("docs", []))
        num_good   = len(result.get("good_docs", []))
        num_kept   = len(result.get("kept_strips", []))
        num_strips = len(result.get("strips", []))

        # Build informative metadata footer
        metadata  = "\n\n---\n📋 **CRAG Analysis**\n"
        metadata += f"- **Verdict**: {verdict}\n"
        metadata += f"- **Reason**: {reason}\n"
        metadata += f"- **Chunks Retrieved**: {num_docs} | Relevant: {num_good}\n"
        metadata += f"- **Sentences**: {num_kept} kept out of {num_strips}\n"
        if verdict != "CORRECT" and web_query:
            metadata += f"- **Web Search Query**: {web_query}\n"
        metadata += f"- **Processing Time**: {elapsed_ms}ms"

        full_response = answer + metadata

        # Log the CRAG pipeline run as a tool call
        tool_calls_log = [{
            "name":              "crag_pipeline",
            "input":             json.dumps({"question": user_input, "verdict": verdict}),
            "output":            answer[:2000],
            "execution_time_ms": elapsed_ms,
            "status":            "success",
        }]

        response_msg = AIMessage(content=full_response)

        return {
            "messages":       [response_msg],
            "agent_response": full_response,
            "tool_calls_log": tool_calls_log,
        }

    except Exception as e:
        print(f"[CRAG] Error in pipeline: {e}")
        import traceback
        traceback.print_exc()

        error_response = (
            f"I encountered an error while processing your document query: {str(e)}"
        )
        response_msg = AIMessage(content=error_response)

        return {
            "messages":       [response_msg],
            "agent_response": error_response,
        }
