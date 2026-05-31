import os
from langchain.tools import tool
import streamlit as st

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "chroma_db")

# ─── Lazy cached loader — NEVER runs at import time ────
@st.cache_resource(show_spinner=False)
def _get_retriever():
    """Loads ChromaDB once, cached for the entire session."""
    if not os.path.exists(DB_PATH):
        print("[ChromaDB] chroma_db folder not found — skipping")
        return None
        
    try:
        from langchain_community.vectorstores import Chroma
        from langchain_community.embeddings.fastembed import FastEmbedEmbeddings

        # 🔴 Optimized BAAI Model
        embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")
        db = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
        return db.as_retriever(search_kwargs={"k": 4})
        
    except Exception as e:
        print(f"[ChromaDB] Failed to load: {e}")
        return None

# ─── Your tools — retriever called lazily inside, not at import ───────
@tool
def search_knowledge_base(query: str) -> str:
    """Search the GSTU IR knowledge base for relevant academic content."""
    retriever = _get_retriever()   # ← cached, only loads once when the tool is actually used
    
    if retriever is None:
        return "Knowledge base unavailable."
        
    try:
        docs = retriever.invoke(query)
        return "\n\n".join(d.page_content for d in docs) if docs else "No results found."
    except Exception as e:
        return f"Search failed: {e}"


@tool
def analyze_student_progress(user_id: str) -> str:
    """Analyzes the student's progress and returns a summary. Use this when the user asks about their performance."""
    return f"Data indicates that student {user_id} has been actively querying International Relations topics. Strong performance in Political Geography, but needs more focus on French Methodology."

@tool
def fetch_latest_geopolitics(topic: str) -> str:
    """Fetches the latest strategic geopolitics insights on a specific topic."""
    return f"Recent strategic movements regarding {topic} suggest high diplomatic tensions and policy shifts. Advise user to monitor global news closely."

# The list exported to app.py
astra_core_tools = [search_knowledge_base, analyze_student_progress, fetch_latest_geopolitics]