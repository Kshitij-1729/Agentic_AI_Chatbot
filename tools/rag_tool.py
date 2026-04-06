"""
RAG implementation and tools for document ingestion and retrieval.
"""

import os
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.tools import tool
from config import Config

# Initialize embeddings using Gemini model requested
embeddings = GoogleGenerativeAIEmbeddings(
    model="gemini-embedding-001", 
    google_api_key=Config.GOOGLE_API_KEY
)

def get_vectorstore():
    """Lazily load the Chroma vector database."""
    os.makedirs(Config.CHROMA_DB_DIR, exist_ok=True)
    return Chroma(
        embedding_function=embeddings,
        persist_directory=Config.CHROMA_DB_DIR
    )

def ingest_document(file_path: str, file_name: str) -> None:
    """Load, split, and embed a document into Chroma DB."""
    ext = os.path.splitext(file_path)[1].lower()
    
    # Load
    if ext == ".pdf":
        loader = PyPDFLoader(file_path)
    elif ext == ".txt":
        loader = TextLoader(file_path, encoding='utf-8')
    elif ext == ".docx":
        loader = Docx2txtLoader(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")
        
    docs = loader.load()
    if not docs:
        return
        
    # Split
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    splits = text_splitter.split_documents(docs)
    
    # Enrich metadata
    for chunk in splits:
        chunk.metadata["file_name"] = file_name
        
    # Persist
    vectorstore = get_vectorstore()
    vectorstore.add_documents(documents=splits)

@tool
def rag_qa_tool(query: str) -> str:
    """
    Search internal uploaded documents for answers.
    Use this tool when the user asks questions about their uploaded files (PDFs, Word docs, TXTs, etc.).
    Returns relevant excerpts from the documents.
    """
    vectorstore = get_vectorstore()
    # Perform similarity search with Top-K of 4
    results = vectorstore.similarity_search(query, k=4)
    
    if not results:
        return "No relevant information found in the uploaded documents."
        
    # Format results
    response_parts = []
    for doc in results:
        file_name = doc.metadata.get("file_name", "Unknown File")
        response_parts.append(f"--- Document: {file_name} ---\n{doc.page_content}")
        
    return "\n\n".join(response_parts)
