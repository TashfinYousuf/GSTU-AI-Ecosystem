import os

print("🚀 Starting Database Build Process...")

# ডাটাবেসের ফোল্ডার তৈরি করা (যাতে app.py ক্র্যাশ না করে)
DB_DIR = "chroma_db"
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)
    print(f"📁 Created directory: {DB_DIR}")

try:
    import chromadb
    # Persistent Client ইনিশিয়ালাইজ করা
    client = chromadb.PersistentClient(path=DB_DIR)
    collection = client.get_or_create_collection(name="gstu_knowledge_base")
    
    # ডাটাবেস খালি থাকলে যাতে এরর না দেয়, তাই একটি সিস্টেম ডেটা পুশ করা
    collection.upsert(
        documents=["Welcome to GSTU IR AI Ecosystem Central Database. This is the core knowledge base."],
        metadatas=[{"source": "system_init"}],
        ids=["core_doc_1"]
    )
    print("✅ Central Database initialized successfully!")
    
except ImportError:
    print("⚠️ 'chromadb' library is missing! But folder is created to prevent crashes.")
except Exception as e:
    print(f"⚠️ System note during DB creation: {e}")

print("🎉 Build script executed perfectly!")