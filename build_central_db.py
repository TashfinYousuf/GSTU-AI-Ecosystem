import os
import sys

print("🚀 Starting Database Build Process...")

# 🔴 FIX 4: Absolute Path for Render Compatibility
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "chroma_db")

os.makedirs(DB_DIR, exist_ok=True)
print(f"📁 Database path: {DB_DIR}")

try:
    from langchain_community.vectorstores import Chroma
    from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
    from langchain_core.documents import Document

    print("⏳ Loading FastEmbed BAAI Model...")
    embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")

    docs = [
        Document(
            page_content="Welcome to GSTU IR AI Ecosystem Central Database. This is the core knowledge base.",
            metadata={"source": "system_init"}
        )
    ]

    print("💾 Saving embedded data to ChromaDB...")
    db = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=DB_DIR
    )
    
    print(f"✅ Central Database built successfully at {DB_DIR}!")

except ImportError as e:
    # 🔴 FIX 2: Actually FAIL the build if a library is missing!
    print(f"❌ FATAL: Missing library — {e}")
    print("Make sure chromadb, fastembed, and langchain-community are in requirements.txt")
    sys.exit(1) 

except Exception as e:
    print(f"❌ FATAL: Build failed — {e}")
    sys.exit(1)

# Only reaches here if everything succeeded!
print("🎉 Build script executed perfectly!")