import os
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# 🔴 Force .env to override any pre-existing shell/system env variables
load_dotenv(override=True)

CHROMA_PERSIST_DIR = "./chroma_db_data"

def get_embedding_model():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing in .env")
        
    return GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=api_key
    )

def get_workspace_vectorstore(workspace_id: str):
    collection_name = f"workspace_{workspace_id.replace('-', '_')}"
    
    return Chroma(
        collection_name=collection_name,
        embedding_function=get_embedding_model(),
        persist_directory=CHROMA_PERSIST_DIR
    )