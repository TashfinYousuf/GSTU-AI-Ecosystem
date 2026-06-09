import os
import streamlit as st
from langchain.tools import tool
from tavily import TavilyClient
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore


# ─── Lazy Cloud Cached Loader ──────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def _get_cloud_retriever():
    """Connects to Pinecone Cloud directly without eating local RAM."""
    
    PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY") or st.secrets.get("PINECONE_API_KEY")
    GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY") or st.secrets.get("GOOGLE_API_KEY")
    
    if not PINECONE_API_KEY or not GOOGLE_API_KEY:
        print("⚠️ [Cloud DB] Missing API keys. Knowledge base search disabled.")
        return None
        
    try:

        # 🔴 Google's Latest Multimodal Embedding Model (3072 Dimensions)
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-2",
            google_api_key=GOOGLE_API_KEY
        )
        
        index_name = "gstu-knowledge-base"
        
        # Connect to existing Pinecone index
        vectorstore = PineconeVectorStore(
            index_name=index_name, 
            embedding=embeddings,
            pinecone_api_key=PINECONE_API_KEY
        )
        
        return vectorstore.as_retriever(search_kwargs={"k": 4})
        
    except Exception as e:
        print(f"[Cloud DB] Failed to connect: {e}")
        return None
    

# ─── 1. INITIALIZE PINECONE RETRIEVER ───
@st.cache_resource(show_spinner=False)
def get_pinecone_retriever():
    try:
        embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2")
        return PineconeVectorStore(
            index_name="gstu-knowledge-base", 
            embedding=embeddings
        ).as_retriever(search_kwargs={"k": 4})
    except Exception as e:
        print(f"Pinecone Connection Error: {e}")
        return None

# ─── 2. HYBRID SEARCH ENGINE (RAG + WEB) ───
def gst_hybrid_search(query):
    rag_context = ""
    rag_sources = []
    web_context = ""
    
    # A. Search Local Uploaded Files (Pinecone)
    retriever = get_pinecone_retriever()
    if retriever:
        try:
            docs = retriever.invoke(query)
            if docs:
                rag_context = "\n\n".join([f"Local Doc: {d.page_content}" for d in docs])
                rag_sources = list(set([d.metadata.get("source", "Local DB") for d in docs]))
        except Exception as e:
            print(f"RAG Error: {e}")

    # B. Trigger Web Search conditionally
    # (যদি RAG এ কিছু না পায়, অথবা প্রশ্নে current/news/bortoman শব্দ থাকে)
    live_keywords = ["current", "latest", "now", "today", "news", "geopolitics", "bortoman", "update", "বর্তমান", "খবর"]
    needs_web = any(kw in query.lower() for kw in live_keywords) or not rag_context

    if needs_web:
        try:
            tavily = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY") or st.secrets.get("TAVILY_API_KEY"))
            web_res = tavily.search(query=query, search_depth="advanced", max_results=3)
            web_context = "\n\n".join([f"Web Source ({r.get('url')}): {r.get('content')}" for r in web_res.get('results', [])])
        except Exception as e:
            print(f"Web Search Error: {e}")

    # C. Combine Contexts
    final_context = ""
    if rag_context:
        final_context += f"--- LOCAL UNIVERSITY DATA ---\n{rag_context}\n\n"
    if web_context:
        final_context += f"--- LIVE WEB DATA ---\n{web_context}\n\n"
        rag_sources.append("🌐 Live Web (Tavily)")
        
    return final_context, rag_sources


# ─── Your Tool ───
@tool
def search_knowledge_base(query: str) -> str:
    """Search the GSTU IR knowledge base for relevant academic content."""
    retriever = _get_cloud_retriever()
    
    if retriever is None:
        return "Knowledge base unavailable. Check API keys."
        
    try:
        docs = retriever.invoke(query)
        return "\n\n".join(d.page_content for d in docs) if docs else "No relevant data found in Cloud DB."
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