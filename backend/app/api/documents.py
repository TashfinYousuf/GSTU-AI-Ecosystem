import os
import io
from pypdf import PdfReader
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.security import get_current_user
from app.core.database import get_db
from app.models.user import Document
from app.core.vector_store import get_workspace_vectorstore

router = APIRouter()
UPLOAD_DIR = "./temp_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_document_to_memory(
    workspace_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Zero-Footprint RAG: ফাইল সার্ভারের ফোল্ডারে সেভ না করে সরাসরি মেমোরি থেকে ডাটাবেসে পাঠাবে"""
    if not current_user.get("sub"):
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files supported")

    try:
        # 🔴 1. Read bytes directly into RAM (Bypasses OS Hard Drive)
        file_bytes = await file.read()
        pdf_reader = PdfReader(io.BytesIO(file_bytes))
        
        docs = []
        for i, page in enumerate(pdf_reader.pages):
            text = page.extract_text()
            if text:
                # Meta data injection
                docs.append(Document(page_content=text, metadata={"source": file.filename, "page": i + 1}))

        if not docs:
            raise HTTPException(status_code=400, detail="PDF is empty or unreadable (scanned images).")

        # 🔴 2. Chunking in RAM
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
        chunks = text_splitter.split_documents(docs)

        # 🔴 3. Direct push to Pinecone Vector DB
        vectorstore = get_workspace_vectorstore(workspace_id)
        vectorstore.add_documents(chunks)

        return {"status": "success", "message": f"Super-fast memory upload successful for {file.filename} ({len(chunks)} chunks)."}

    except Exception as e:
        print(f"Memory RAG Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to parse document from memory.")


# 🔴 New Route: ওয়ার্কস্পেসের সব আপলোড করা ফাইলের লিস্ট পাওয়ার জন্য
@router.get("/list/{workspace_id}")
def get_documents(
    workspace_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if not current_user.get("sub"):
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    docs = db.query(Document).filter(Document.workspace_id == workspace_id).order_by(Document.created_at.desc()).all()
    return [{"id": str(d.id), "filename": d.filename} for d in docs]

# 🔴 New Route: নলেজ বেস থেকে ডকুমেন্ট ডিলিট করার জন্য
@router.delete("/delete/{workspace_id}/{doc_id}")
def delete_document(
    workspace_id: str,
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if not current_user.get("sub"):
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    doc = db.query(Document).filter(Document.id == doc_id, Document.workspace_id == workspace_id).first()
    if doc:
        db.delete(doc)
        db.commit()
        # Note: প্রোডাকশনে আমরা ChromaDB থেকেও ভেক্টরগুলো ডিলিট করব
    
    return {"message": "Document deleted successfully"}