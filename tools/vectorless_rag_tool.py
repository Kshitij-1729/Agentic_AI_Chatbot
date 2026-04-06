"""
Vectorless RAG Tool — an advanced document QA feature using LangGraph and PageIndex.
"""

import os
import json
import time
import logging
import hashlib
from typing import Optional, Annotated
from dataclasses import dataclass, field

from langchain_core.tools import tool
from config import Config

# ── PageIndex ─────────────────────────────────────────────────────────────────
from pageindex import PageIndexClient

# ── LangChain ─────────────────────────────────────────────────────────────────
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser

# ── LangGraph ─────────────────────────────────────────────────────────────────
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("VectorlessRAG")

@dataclass
class RetrievedNode:
    node_id:    str
    title:      str
    page:       str
    text:       str
    confidence: float = 1.0

@dataclass
class RAGResponse:
    query:     str
    answer:    str
    sources:   list[RetrievedNode]
    reasoning: str = ""
    node_ids:  list[str] = field(default_factory=list)

class RAGState(TypedDict):
    query:          str
    tree:           list
    expert_rules:   str
    min_confidence: float
    compressed_tree: list
    node_ids:       list[str]
    confidence_map: dict[str, float]
    reasoning:      str
    retrieved_nodes: list[RetrievedNode]
    answer:         str

TREE_SEARCH_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a precise document analyst. You will be given a user query and a hierarchical tree structure of a document (title, page, short preview per section).

Your job:
1. Identify which node IDs most likely contain the answer.
2. Explain your reasoning step by step.
3. Assign a confidence score (0.0 to 1.0) to each selected node.
4. Return at most {max_nodes} nodes — prefer precision over recall.

{expert_rules_section}

Reply ONLY in this exact JSON format (no extra text):
{{
  "thinking": "<your step-by-step reasoning>",
  "node_list": ["node_id1", "node_id2"],
  "confidence": {{"node_id1": 0.95, "node_id2": 0.80}}
}}"""),
    ("human", "Query: {query}\n\nDocument Tree:\n{compressed_tree}"),
])

GENERATE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a precise document analyst. Answer the question using ONLY the provided context sections.

Rules:
- Cite every factual claim as (Section: '<title>', p.<page>).
- If a section has low relevance, use it cautiously and note the uncertainty.
- If the context is insufficient, say so explicitly — do not hallucinate.
- Be concise and well-structured."""),
    ("human", "Question: {query}\n\nContext:\n{context}"),
])


class VectorlessRAG:
    def __init__(
        self,
        model:             str   = "gpt-4o",
        temperature:       float = 0.0,
        max_retries:       int   = 3,
        summary_chars:     int   = 300,
        max_nodes:         int   = 12,
        expert_rules:      str   = "",
    ):
        self.summary_chars  = summary_chars
        self.max_nodes      = max_nodes
        self.expert_rules   = expert_rules

        pi_key  = Config.PAGEINDEX_API_KEY
        oai_key = Config.OPENAI_API_KEY

        if not pi_key:
            log.warning("PAGEINDEX_API_KEY not found in config.")
        else:
            self.pi_client = PageIndexClient(api_key=pi_key)

        self.llm = ChatOpenAI(
            model       = model,
            temperature = temperature,
            api_key     = oai_key,
            max_retries = max_retries,
        )

        self.doc_id:      Optional[str] = None
        self.tree:        list          = []
        self._tree_cache: dict          = {}

        self._tree_search_chain = (TREE_SEARCH_PROMPT | self.llm | JsonOutputParser())
        self._generate_chain = (GENERATE_PROMPT | self.llm | StrOutputParser())
        self._graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        builder = StateGraph(RAGState)
        builder.add_node("compress_tree", self._node_compress_tree)
        builder.add_node("tree_search",   self._node_tree_search)
        builder.add_node("retrieve",      self._node_retrieve)
        builder.add_node("generate",      self._node_generate)
        builder.add_node("no_results",    self._node_no_results)

        builder.add_edge(START, "compress_tree")
        builder.add_edge("compress_tree", "tree_search")
        builder.add_edge("tree_search", "retrieve")
        builder.add_conditional_edges(
            "retrieve",
            self._route_after_retrieve,
            {"generate": "generate", "no_results": "no_results"}
        )
        builder.add_edge("generate", END)
        builder.add_edge("no_results", END)
        return builder.compile()

    def _node_compress_tree(self, state: RAGState) -> dict:
        cache_key = hashlib.md5(f"{len(state['tree'])}-{self.summary_chars}".encode()).hexdigest()
        if cache_key in self._tree_cache:
            return {"compressed_tree": self._tree_cache[cache_key]}

        def _compress(nodes):
            out = []
            for n in nodes:
                entry = {
                    "node_id": n["node_id"],
                    "title":   n["title"],
                    "page":    str(n.get("page_index", "?")),
                    "preview": n.get("text", "")[:self.summary_chars].replace("\n", " "),
                }
                if n.get("nodes"):
                    entry["children"] = _compress(n["nodes"])
                out.append(entry)
            return out

        compressed = _compress(state["tree"])
        self._tree_cache[cache_key] = compressed
        return {"compressed_tree": compressed}

    def _node_tree_search(self, state: RAGState) -> dict:
        expert_rules_section = f"Expert Routing Rules:\n{state['expert_rules']}" if state.get("expert_rules") else ""
        result = self._tree_search_chain.invoke({
            "query": state["query"],
            "compressed_tree": json.dumps(state["compressed_tree"], indent=2),
            "max_nodes": self.max_nodes,
            "expert_rules_section": expert_rules_section,
        })
        return {
            "node_ids": result.get("node_list", []),
            "confidence_map": result.get("confidence", {}),
            "reasoning": result.get("thinking", ""),
        }

    def _node_retrieve(self, state: RAGState) -> dict:
        target_ids = state["node_ids"]
        confidence_map = state.get("confidence_map", {})
        min_conf = state.get("min_confidence", 0.0)
        found: list[RetrievedNode] = []

        def _walk(nodes):
            for node in nodes:
                if node["node_id"] in target_ids:
                    conf = confidence_map.get(node["node_id"], 1.0)
                    if conf >= min_conf:
                        found.append(RetrievedNode(
                            node_id    = node["node_id"],
                            title      = node["title"],
                            page       = str(node.get("page_index", "?")),
                            text       = node.get("text", "Content not available."),
                            confidence = conf,
                        ))
                if node.get("nodes"):
                    _walk(node["nodes"])
                    
        _walk(state["tree"])
        found.sort(key=lambda n: n.confidence, reverse=True)
        return {"retrieved_nodes": found}

    def _node_generate(self, state: RAGState) -> dict:
        nodes = state["retrieved_nodes"]
        context_parts = []
        for node in nodes:
            conf_note = f" [relevance: {node.confidence:.0%}]" if node.confidence < 0.85 else ""
            context_parts.append(f"[Section: '{node.title}' | Page {node.page}{conf_note}]\n{node.text}")
        context = ("\n\n" + "─" * 50 + "\n\n").join(context_parts)
        answer = self._generate_chain.invoke({"query": state["query"], "context": context})
        return {"answer": answer}

    def _node_no_results(self, state: RAGState) -> dict:
        return {"answer": "No sufficiently relevant sections were found using vectorless RAG."}

    def _route_after_retrieve(self, state: RAGState) -> str:
        return "generate" if state.get("retrieved_nodes") else "no_results"

    def load_document(self, pdf_path: str, poll_interval: int = 5) -> str:
        if not self.pi_client:
            raise ValueError("PageIndex client not initialized. Check API key.")
        result = self.pi_client.submit_document(pdf_path)
        self.doc_id = result["doc_id"]
        while True:
            status = self.pi_client.get_document(self.doc_id).get("status")
            if status == "completed": break
            if status == "failed": raise RuntimeError("PageIndex indexing failed.")
            time.sleep(poll_interval)
        self._fetch_tree()
        return self.doc_id

    def load_local_tree(self, json_path: str):
        with open(json_path, "r", encoding="utf-8") as f:
            self.tree = json.load(f)
        self.doc_id = None

    def _fetch_tree(self):
        tree_result = self.pi_client.get_tree(self.doc_id, node_summary=True)
        self.tree = tree_result.get("result", [])

    def save_tree(self, output_path: str):
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.tree, f, indent=2, ensure_ascii=False)

    def query(self, question: str) -> RAGResponse:
        final_state = self._graph.invoke({
            "query": question,
            "tree": self.tree,
            "expert_rules": self.expert_rules,
            "min_confidence": 0.0,
            "compressed_tree": [],
            "node_ids": [],
            "confidence_map": {},
            "reasoning": "",
            "retrieved_nodes": [],
            "answer": "",
        })
        return RAGResponse(
            query=question, answer=final_state["answer"], sources=final_state["retrieved_nodes"],
            reasoning=final_state["reasoning"], node_ids=final_state["node_ids"]
        )

# ──────────────────────────────────────────────────────────────────────────────
#  HELPER & TOOL
# ──────────────────────────────────────────────────────────────────────────────

def ingest_pdf_vectorless(file_path: str, filename: str) -> None:
    """Invoked during file upload to index the PDF via PageIndex and save local tree."""
    # Ensure uploads dir exists
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    tree_path = os.path.join(Config.UPLOAD_FOLDER, f"{filename}.tree.json")
    
    if os.path.exists(tree_path):
        log.info(f"Tree already exists for {filename}")
        return

    rag = VectorlessRAG()
    try:
        rag.load_document(file_path)
        rag.save_tree(tree_path)
        log.info(f"Successfully processed vectorless index for {filename}")
    except Exception as e:
        log.error(f"Failed to process vectorless doc {filename}: {e}")

@tool
def vectorless_rag_tool(query: str, filename: str) -> str:
    """
    Search internal uploaded documents for answers using advanced Vectorless RAG (PageIndex).
    Use this tool ONLY if the standard rag_qa_tool fails to answer the query, or if the user explicitly asks for 'vectorless rag'.
    A specific filename (e.g., 'document.pdf') MUST be provided. If you do not have a filename, you must ask the user which file they meant before calling this tool.
    Returns the analytical answer with reasoning context.
    """
    if not filename:
        return "Error: No filename provided. Please explicitly ask the user which file they want to query."

    tree_path = os.path.join(Config.UPLOAD_FOLDER, f"{filename}.tree.json")
    if not os.path.exists(tree_path):
        return f"Error: Advanced Vectorless index not found for {filename}. Ensure it was a PDF upload or fallback to the regular rag_qa_tool."

    try:
        rag = VectorlessRAG()
        rag.load_local_tree(tree_path)
        response = rag.query(query)
        
        # Build formatted output
        output_parts = [
            f"--- Vectorless RAG Answer for '{filename}' ---",
            response.answer,
            "\\n--- Sources Cited ---"
        ]
        for src in response.sources:
            output_parts.append(f"- Section: {src.title} (Page {src.page})")
            
        return "\\n".join(output_parts)
    except Exception as e:
        return f"Error executing Vectorless RAG: {e}"
