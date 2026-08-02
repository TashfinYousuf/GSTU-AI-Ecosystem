import os
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
CHROMA_PATH = os.path.join(BASE_DIR, "chroma_db")

def get_context(query: str) -> str:
    """
    ইউজারের প্রশ্ন নিয়ে ChromaDB তে খুঁজবে এবং রিলেভেন্ট টেক্সট বের করে আনবে
    """
    try:
        # Google Embeddings ইনিশিয়ালাইজ করা
        embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
        
        # ChromaDB লোড করা
        vector_store = Chroma(
            collection_name="gstu_core_v2",
            persist_directory=CHROMA_PATH, 
            embedding_function=embeddings
        )
        
        # সেরা ৩টি রিলেভেন্ট ডকুমেন্ট খোঁজা
        retriever = vector_store.as_retriever(search_kwargs={"k": 3})
        docs = retriever.invoke(query)
        
        # ডকুমেন্টগুলোকে একটি স্ট্রিংয়ে যুক্ত করে রিটার্ন করা
        context_text = "\n\n".join([doc.page_content for doc in docs])
        return context_text
        
    except Exception as e:
        print(f"⚠️ RAG Retrieval Error: {e}")
        return ""