from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

router = APIRouter()

# ChromaDB পাথ
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
CHROMA_PATH = os.path.join(BASE_DIR, "chroma_db")

class TrainRequest(BaseModel):
    text: str

@router.post("/train")
async def train_ai(request: TrainRequest):
    """
    এই এপিআই দিয়ে আমরা সরাসরি AI-এর মাথায় নতুন তথ্য (Text) পুশ করব
    """
    try:
        embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
        vector_store = Chroma(
            collection_name="gstu_core_v2",
            persist_directory=CHROMA_PATH, 
            embedding_function=embeddings
        )
        
        # নতুন তথ্য ডাটাবেসে সেভ করা
        vector_store.add_texts(texts=[request.text])
        
        return {"message": "Knowledge successfully injected into GSTU AI Brain! 🧠"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))