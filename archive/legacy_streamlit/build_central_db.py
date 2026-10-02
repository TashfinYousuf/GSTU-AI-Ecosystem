import os
import sys
import time
import random
import glob
from dotenv import load_dotenv

# Langchain & Pinecone Imports
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec

load_dotenv()  # Loads .env BEFORE anything else

# ── 1. Validate keys early ──────────────────────────────
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
GOOGLE_API_KEY   = os.environ.get("GOOGLE_API_KEY")

if not PINECONE_API_KEY:
    print("❌ FATAL: PINECONE_API_KEY missing from .env")
    sys.exit(1)
if not GOOGLE_API_KEY:
    print("❌ FATAL: GOOGLE_API_KEY missing from .env")
    sys.exit(1)

print("✅ API keys loaded successfully")
print("🚀 Starting Cloud Database Build Process (Pinecone + Gemini)...")

# ── 2. PDF Loading (Robust Engine) ──────────────────────────────────
DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
    print(f"⚠️ Created '{DATA_DIR}' folder. Please put your PDFs inside it and run again!")
    sys.exit(1)

pdf_files = glob.glob(f"{DATA_DIR}/**/*.pdf", recursive=True) + glob.glob(f"{DATA_DIR}/*.pdf")
if not pdf_files:
    print(f"❌ No PDFs found in ./{DATA_DIR}/ folder")
    sys.exit(1)

print(f"📚 Loading {len(pdf_files)} PDFs...")
all_docs = []
failed  = []

for pdf_path in pdf_files:
    try:
        loader = PyMuPDFLoader(pdf_path)
        docs   = loader.load()
        all_docs.extend(docs)
    except Exception as e:
        failed.append(pdf_path)
        print(f"  ⚠️ Skipped {pdf_path}: {e}")

print(f"✅ Loaded {len(all_docs)} pages ({len(failed)} PDFs skipped)")

# ── 3. Split Text into Chunks ───────────────────────────────────────
splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
chunks   = splitter.split_documents(all_docs)

# Clean empty chunks — Pinecone rejects empty strings
chunks = [c for c in chunks if c.page_content.strip()]
print(f"✂️  Split into {len(chunks)} clean chunks")

# ── 4. Initialize Embeddings ────────────────────────────────────────
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-2",
    google_api_key=GOOGLE_API_KEY,          
)
print("✅ Gemini Multi-modal embeddings ready")

# ── 5. Pinecone Initialization & Index Creation ─────────────────────
index_name = "gstu-knowledge-base"
pc = Pinecone(api_key=PINECONE_API_KEY)

existing = [i.name for i in pc.list_indexes()]
if index_name not in existing:
    print(f"📦 Creating Pinecone index: {index_name}")
    pc.create_index(
        name=index_name,
        dimension=3072,  # Fixed for gemini-embedding-2
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )

# ── 6. State Tracking (Resume Capability) ───────────────────────────
PROGRESS_FILE = "upload_progress.txt"

def get_uploaded_batches():
    if not os.path.exists(PROGRESS_FILE):
        return set()
    with open(PROGRESS_FILE) as f:
        return set(int(x) for x in f.read().split() if x.strip())

def mark_batch_done(batch_num):
    with open(PROGRESS_FILE, "a") as f:
        f.write(f"{batch_num}\n")

# ── 7. Smart Upload Logic with Exponential Backoff ──────────────────
def upload_with_retry(batch, embeddings, index_name, pinecone_api_key, batch_num, total_batches, max_retries=6):
    """Upload one batch with exponential backoff on 429 errors."""
    for attempt in range(max_retries):
        try:
            PineconeVectorStore.from_documents(
                documents=batch,
                embedding=embeddings,
                index_name=index_name,
                pinecone_api_key=pinecone_api_key,
            )
            return True
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e) or "quota" in str(e).lower():
                wait = (2 ** attempt) * 60 + random.randint(5, 15)
                print(f"  ⏳ Google API Rate Limit hit on batch {batch_num}/{total_batches}. "
                      f"Cooling down for {wait}s (Attempt {attempt+1}/{max_retries})...")
                time.sleep(wait)
            else:
                print(f"  ❌ Unknown error on batch {batch_num}: {e}")
                raise
    print(f"  ❌ Batch {batch_num} failed permanently after {max_retries} retries")
    return False

# ── 8. Execution Loop ───────────────────────────────────────────────
BATCH_SIZE  = 50     # Reduced to 50 to avoid hitting limits fast
SLEEP_SECS  = 45     # Safe delay between batches

total_batches = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE
failed_batches = []
uploaded = get_uploaded_batches()

print(f"\n☁️  Uploading {len(chunks)} chunks in {total_batches} batches "
      f"(Batch Size: {BATCH_SIZE}, Normal Sleep: {SLEEP_SECS}s)...")

for i in range(0, len(chunks), BATCH_SIZE):
    batch_num = i // BATCH_SIZE + 1
    
    if batch_num in uploaded:
        print(f"  ⏭️  Batch {batch_num}/{total_batches} already uploaded — skipping")
        continue
        
    batch = chunks[i:i + BATCH_SIZE]
    
    success = upload_with_retry(
        batch, embeddings, index_name, PINECONE_API_KEY,
        batch_num, total_batches
    )
    
    if success:
        print(f"  ✅ Uploaded Batch {batch_num}/{total_batches} "
              f"({min(i+BATCH_SIZE, len(chunks))}/{len(chunks)} total chunks)")
        mark_batch_done(batch_num)
    else:
        failed_batches.append(batch_num)
    
    # Don't sleep after the very last batch
    if i + BATCH_SIZE < len(chunks):
        time.sleep(SLEEP_SECS)

# ── 9. Final Summary ────────────────────────────────────────────────
if failed_batches:
    print(f"\n⚠️  {len(failed_batches)} batches failed: {failed_batches}")
    print("Please just re-run the script. It will automatically skip the successful ones and retry the failed ones!")
else:
    print(f"\n🎉 SUCCESS! All {len(chunks)} chunks safely uploaded to '{index_name}'!")