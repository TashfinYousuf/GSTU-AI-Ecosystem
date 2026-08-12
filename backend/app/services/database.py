import os
from supabase import create_client, ClientOptions
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings

def get_vector_db():
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
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