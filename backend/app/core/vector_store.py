import os
import re
import time
from threading import Lock
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.embeddings import Embeddings

# .env ফাইল লোড করা
load_dotenv(override=True)

# Absolute Path Setup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHROMA_PERSIST_DIR = os.path.join(BASE_DIR, "chroma_db_data")

# ==========================================
# 🔴 THROTTLE SETUP (Prevents API Spamming)
# ==========================================
EMBED_RPM = int(os.getenv("GEMINI_EMBED_RPM", "12"))
_MIN_INTERVAL = 60.0 / EMBED_RPM
_lock = Lock()
_last_call = 0.0

def _throttle():
    global _last_call
    with _lock:
        wait = _last_call + _MIN_INTERVAL - time.time()
        if wait > 0:
            time.sleep(wait)
        _last_call = time.time()


# ==========================================
# 🔴 RATE-LIMITED EMBEDDINGS WRAPPER
# ==========================================
class RateLimitedEmbeddings(Embeddings):
    """Wraps Gemini embeddings to handle Quota Limits safely."""
    def __init__(self, inner: Embeddings, max_retries: int = 4):
        self.inner = inner
        self.max_retries = max_retries

    def _call_with_retry(self, fn, *args, **kwargs):
        for attempt in range(self.max_retries):
            _throttle()
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                msg = str(e)
                # 1. FAIL FAST: Daily Quota Exhausted
                if "PerDay" in msg or "Daily" in msg:
                    raise RuntimeError(
                        "Daily AI embedding quota exhausted for today. "
                        "This will reset automatically tomorrow — please try again later, or enable billing."
                    ) from e
                
                # 2. WAIT & RETRY: Per-Minute Quota Hit
                if "429" in msg or "quota" in msg.lower():
                    match = re.search(r"retry_delay\s*{\s*seconds:\s*(\d+)", msg)
                    wait = int(match.group(1)) + 2 if match else 15
                    print(f"Per-minute quota hit — waiting {wait}s (attempt {attempt+1}/{self.max_retries})")
                    time.sleep(wait)
                else:
                    raise
        raise RuntimeError("Embedding failed after repeated quota retries — please try again shortly.")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        batch_size = 50 # Batching to save quota
        results = []
        for i in range(0, len(texts), batch_size):
            results.extend(self._call_with_retry(self.inner.embed_documents, texts[i:i + batch_size]))
        return results

    def embed_query(self, text: str) -> list[float]:
        return self._call_with_retry(self.inner.embed_query, text)


# ==========================================
# 🔴 EXPORTS
# ==========================================
def get_embedding_model():
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GEMINI/GOOGLE API_KEY is missing in .env")

    base = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001", google_api_key=api_key)
    return RateLimitedEmbeddings(base)

def get_workspace_vectorstore(workspace_id: str | None = None):
    clean_ws = (workspace_id or "global_knowledge_base").strip()
    safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', clean_ws)
    collection_name = f"workspace_{safe_name}"
    return Chroma(
        collection_name=collection_name,
        embedding_function=get_embedding_model(),
        persist_directory=CHROMA_PERSIST_DIR,
    )