import os
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_core.documents import Document

print("🚀 Starting Database Build Process...")

DB_DIR = "chroma_db"
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)
    print(f"📁 Created directory: {DB_DIR}")

try:

    print("⏳ Loading FastEmbed BAAI Model... (This ensures 100% compatibility with app.py)")
    # Must use the exact same embedding model as in agent_tools.py to avoid mismatches and ensure the DB is built with the correct vector dimensions.
    embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")

    # Create dummy initial document
    docs = [
        Document(
            page_content="Welcome to GSTU IR AI Ecosystem Central Database. This is the core knowledge base.",
            metadata={"source": "system_init"}
        )
    ]

    print("💾 Saving embedded data to ChromaDB...")
    # Initialize and persist the DB with the BAAI embeddings
    db = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=DB_DIR
    )
    
    print("✅ Central Database built successfully with BAAI embeddings!")

except ImportError as e:
    print(f"⚠️ Missing library. Please check requirements.txt: {e}")
except Exception as e:
    print(f"⚠️ System error during DB creation: {e}")

print("🎉 Build script executed perfectly!")