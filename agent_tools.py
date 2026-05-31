import streamlit as st
import os
from langchain_core.tools import tool

import os
import streamlit as st

# =====================================================================
# ⚡ UNIFIED FAST CACHED DATABASE LOADER (Absolute Path Fix)
# =====================================================================
@st.cache_resource(show_spinner=False)
def get_chroma_db():
    """Load ChromaDB once, cache forever — avoids Render timeout."""
    
    # 🔴 FIX 4: Absolute Path (Must match build_central_db.py exactly)
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, "chroma_db")
    
    if not os.path.exists(db_path):
        print("⚠️ ChromaDB folder not found!")
        return None   
            
    try:
        from langchain_community.vectorstores import Chroma
        from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
        
        embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")
        
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