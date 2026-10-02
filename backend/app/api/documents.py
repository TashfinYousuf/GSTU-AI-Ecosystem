import os
import io
import uuid
import time
import logging

from pypdf import PdfReader
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form, BackgroundTasks
from app.services.database import supabase 

from langchain_core.documents import Document 
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.security import get_current_user
from app.core.vector_store import get_workspace_vectorstore
from app.core.limiter import limiter

router = APIRouter()

logger = logging.getLogger(__name__)

# 🔴 The Background Worker that updates DB in real-time
def background_embed_process(workspace_id: str, doc_id: str, chunks: list):
    try:
        vectorstore = get_workspace_vectorstore(workspace_id)
        batch_size = 50 
        processed = 0

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            try:
                vectorstore.add_documents(batch)
            except Exception as ai_err:
                # 🔴 Catch Daily Quota and stop immediately
                if "Daily AI embedding quota" in str(ai_err):
                    raise RuntimeError("Daily Quota Exhausted. Partially indexed.")
                raise ai_err
            
            processed += len(batch)
            supabase.table("documents").update({"processed_chunks": processed}).eq("id", doc_id).execute()

        supabase.table("documents").update({"status": "completed"}).eq("id", doc_id).execute()

    except Exception as e:
        logger.error(f"❌ Background RAG Error for {doc_id}: {e}")
        supabase.table("documents").update({
            "status": "failed", 
            "error_message": str(e)
        }).eq("id", doc_id).execute()


@router.post("/upload")
@limiter.limit("5/minute")
async def upload_document_to_memory(
    request: Request,
    background_tasks: BackgroundTasks,
    workspace_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user.get("sub")

    workspace = supabase.table("workspaces").select("user_id").eq("id", workspace_id).execute()
    if not workspace.data or workspace.data[0].get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    lower_name = file.filename.lower()
    allowed_exts = (".pdf", ".txt", ".md", ".docx", ".doc", ".csv", ".json")
    if not any(lower_name.endswith(ext) for ext in allowed_exts):
        raise HTTPException(status_code=400, detail="Supported formats: PDF, TXT, MD, DOCX, DOC, CSV, JSON")

    doc_id = str(uuid.uuid4())

    try:
        file_bytes = await file.read()
        docs = []

        if lower_name.endswith(".pdf"):
            pdf_reader = PdfReader(io.BytesIO(file_bytes))
            for i, page in enumerate(pdf_reader.pages):
                text = page.extract_text()
                if text and text.strip():
                    docs.append(Document(
                        page_content=text.strip(),
                        metadata={"source": file.filename, "filename": file.filename, "page": i + 1, "page_number": i + 1, "doc_id": doc_id}
                    ))
        elif lower_name.endswith((".docx", ".doc")):
            import zipfile
            import xml.etree.ElementTree as ET
            try:
                with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                    xml_content = z.read("word/document.xml")
                tree = ET.fromstring(xml_content)
                paragraphs = []
                for p in tree.iter():
                    if p.tag.endswith('}p'):
                        p_text = "".join([node.text for node in p.iter() if node.text and node.tag.endswith('}t')])
                        if p_text.strip():
                            paragraphs.append(p_text.strip())
                for sec_idx, i in enumerate(range(0, len(paragraphs), 5)):
                    sec_text = "\n\n".join(paragraphs[i:i + 5])
                    docs.append(Document(
                        page_content=sec_text,
                        metadata={"source": file.filename, "filename": file.filename, "page": sec_idx + 1, "page_number": sec_idx + 1, "doc_id": doc_id}
                    ))
            except Exception as docx_err:
                content = file_bytes.decode("utf-8", errors="ignore")
                docs.append(Document(
                    page_content=content,
                    metadata={"source": file.filename, "filename": file.filename, "page": 1, "page_number": 1, "doc_id": doc_id}
                ))
        else:
            try:
                content = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                content = file_bytes.decode("latin-1", errors="ignore")
            docs.append(Document(
                page_content=content,
                metadata={"source": file.filename, "filename": file.filename, "page": 1, "page_number": 1, "doc_id": doc_id}
            ))

        if not docs:
            raise HTTPException(status_code=400, detail="Document is empty or contains no selectable text.")

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
        chunks = text_splitter.split_documents(docs)
        total_chunks = len(chunks)

        # 🔴 Insert initial state into DB
        supabase.table("documents").insert({
            "id": doc_id,
            "workspace_id": workspace_id,
            "filename": file.filename,
            "chunk_count": total_chunks,
            "processed_chunks": 0,
            "status": "processing"
        }).execute()

        # 🔴 Trigger Background Task
        background_tasks.add_task(background_embed_process, workspace_id, doc_id, chunks)

        return {
            "status": "success", 
            "message": f"Upload started. Processing {total_chunks} chunks in background.", 
            "doc_id": doc_id
        }

    except HTTPException:
        raise
    except Exception as e:
        # 🔴 Delete the hardcoded string and show the REAL error to the terminal/UI
        logger.error(f"Upload Crash Details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File parsing failed: {str(e)}")


# 🔴 New API for Frontend to poll status
@router.get("/status/{doc_id}")
def get_document_status(doc_id: str, current_user: dict = Depends(get_current_user)):
    res = supabase.table("documents").select("status, chunk_count, processed_chunks, error_message").eq("id", doc_id).maybe_single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Document not found")
    return res.data


# 🔴 Update List to include status
@router.get("/list/{workspace_id}")
def get_documents(workspace_id: str, current_user: dict = Depends(get_current_user)):
    res = supabase.table("documents").select("id, filename, status, chunk_count, processed_chunks").eq("workspace_id", workspace_id).order("created_at", desc=True).execute()
    return res.data or []

@router.delete("/delete/{workspace_id}/{doc_id}")
def delete_document(workspace_id: str, doc_id: str, current_user: dict = Depends(get_current_user)):
    try:
        vectorstore = get_workspace_vectorstore(workspace_id)
        vectorstore.delete(where={"doc_id": doc_id}) 
    except Exception: pass
    supabase.table("documents").delete().eq("id", doc_id).execute()
    return {"status": "success"}