import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.security import get_current_user
from app.core.database import get_db
from app.models.user import Document
from app.core.vector_store import get_workspace_vectorstore

router = APIRouter(tags=["Documents & RAG"])
UPLOAD_DIR = "./temp_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_document(
    workspace_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if not current_user.get("sub"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files supported")

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # ১. RAG প্রসেসিং
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        # Source Metadata অ্যাড করা (ভবিষ্যতে Citation এর জন্য লাগবে)
        for doc in docs:
            doc.metadata["source"] = file.filename 

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        chunks = text_splitter.split_documents(docs)

        vectorstore = get_workspace_vectorstore(workspace_id)
        vectorstore.add_documents(chunks)

        # ২. ডেটাবেসে ফাইলের রেকর্ড সেভ করা
        new_doc = Document(workspace_id=workspace_id, filename=file.filename)
        db.add(new_doc)
        db.commit()

        return {"message": f"Successfully processed {file.filename}"}

    except Exception as e:
        print(f"Upload Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process document")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

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