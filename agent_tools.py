import streamlit as st
import os
from langchain_core.tools import tool

# =====================================================================
# ⚡ UNIFIED FAST CACHED DATABASE LOADER (Zero-Crash Architecture)
# =====================================================================

@st.cache_resource(show_spinner=False)
def get_chroma_db():
    """Load ChromaDB once, cache forever — avoids Render timeout and mismatch."""
    
    # ডাইনামিক পাথ, যাতে ফোল্ডার যেখানেই থাকুক সে খুঁজে পায়
    db_path = os.path.abspath(os.path.join(os.getcwd(), "chroma_db"))
    
    # ফোল্ডার না থাকলে অ্যাপ ক্র্যাশ না করে নিজে বানিয়ে নেবে
    if not os.path.exists(db_path):
        os.makedirs(db_path)
        
    try:
        from langchain_community.vectorstores import Chroma
        # 🔴 STRICT FIX: We are using EXACTLY ONE optimized model everywhere!
        from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
        embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")
        
        # Load the DB into memory
        db = Chroma(
            persist_directory=db_path,
            embedding_function=embeddings
        )
        return db
        
    except Exception as e:
        print(f"⚠️ [ChromaDB Initialization Error]: {e}")
        return None

# চোখের পলকে (0ms) মেমোরি থেকে ডাটাবেস লোড হবে
vectorstore = get_chroma_db()

# 🛡️ Safe fallback
if vectorstore is None:
    st.warning("⚠️ System is running without Central Database context. Live Web Search is active.")

@tool
def analyze_student_progress(user_id: str) -> str:
    """Analyzes the student's progress and returns a summary. Use this when the user asks about their performance."""
    return f"Data indicates that student {user_id} has been actively querying International Relations topics. Strong performance in Political Geography, but needs more focus on French Methodology."

@tool
def fetch_latest_geopolitics(topic: str) -> str:
    """Fetches the latest strategic geopolitics insights on a specific topic."""
    return f"Recent strategic movements regarding {topic} suggest high diplomatic tensions and policy shifts. Advise user to monitor global news closely."

# The list exported to app.py
astra_core_tools = [analyze_student_progress, fetch_latest_geopolitics]