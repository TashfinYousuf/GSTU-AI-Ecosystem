import os
import logging

from supabase import create_client, ClientOptions
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# এনভায়রনমেন্ট ভ্যারিয়েবল লোড করা নিশ্চিত করা
load_dotenv(override=True)

# 🔴 SAFE GLOBAL SUPABASE CLIENT (Strips spaces and catches invalid keys)
_supabase_url = os.getenv("SUPABASE_URL", "").strip()
_supabase_key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY", "")).strip()

supabase = None
if _supabase_url and _supabase_key:
    try:
        supabase = create_client(_supabase_url, _supabase_key, options=ClientOptions(flow_type="implicit"))
    except Exception as e:
        logger.error(f"❌ Supabase Client Init Error: {e}. Please check your .env file format.")
else:
    logger.warning("⚠️ Supabase URL or Key is missing in .env file.")

def get_vector_db():
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not supabase_url or not supabase_key: 
        return None
    try:
        supabase = create_client(supabase_url, supabase_key, options=ClientOptions(flow_type="implicit"))
        embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")
        return SupabaseVectorStore(client=supabase, embedding=embeddings, table_name="gstu_documents", query_name="match_documents")
    except Exception as e:
        print(f"Supabase Client Init Error: {e}")
        return None

def search_context(query: str, active_course: str = None):
    """Searches the Supabase PGVector database for context."""
    db = get_vector_db()
    if not db: 
        return "", []
    
    try:
        search_kwargs = {"k": 6}
        if active_course and active_course != "General":
            search_kwargs["filter"] = {"course": active_course}
            
        docs = db.as_retriever(search_kwargs=search_kwargs).invoke(query)
        if not docs: 
            return "", []
        
        context = "\n\n".join([doc.page_content for doc in docs])
        return context, docs
    except Exception as e:
        print(f"Vector DB Search Error: {e}")
        return "", []

def save_to_vector_db(*args, **kwargs):
    # This will be handled in the admin panel upload section later
    pass