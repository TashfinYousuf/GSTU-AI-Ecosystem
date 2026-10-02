import os
import uuid
import time
import hashlib
import asyncio

from datetime import datetime
from pydantic import BaseModel
from google import genai
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, UploadFile, File, Form
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from supabase import create_client, Client

from app.core.limiter import limiter
from app.core.security import get_current_user, require_active_account
from app.core.vector_store import get_workspace_vectorstore

import mimetypes
import zipfile
import xml.etree.ElementTree as ET
from pypdf import PdfReader
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

router = APIRouter()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
gemini_key = os.getenv("GEMINI_API_KEY")

ADMIN_ROLES = {"admin", "faculty"}

def require_admin(current_user: dict):
    email = (current_user.get("email") or "").strip().lower()
    if email == "yousufaltashfin@gmail.com":
        return "admin"
    meta = current_user.get("app_metadata", {}) or {}
    user_meta = current_user.get("user_metadata", {}) or {}
    role = (meta.get("role") or user_meta.get("role") or "student").strip().lower()
    if role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Admin or faculty access required.")
    return role


# ---------- REAL ANALYTICS (previously the frontend had zero backend behind it) ----------

# 🧠 Cache the analytics data for 5 minutes (300 seconds) so the DB isn't hammered!
_analytics_cache = {"data": None, "timestamp": 0}

@router.get("/stats")
@router.get("/analytics")
async def get_admin_analytics(current_user: dict = Depends(get_current_user)):
    require_admin(current_user)
    
    current_time = time.time()
    # Return cached data if it's less than 5 minutes old
    if _analytics_cache["data"] and (current_time - _analytics_cache["timestamp"] < 300):
        return _analytics_cache["data"]

    try:
        # Supabase Admin API — run in background thread to prevent event loop blocking
        users_res = await asyncio.to_thread(supabase.auth.admin.list_users)
        all_users = users_res if isinstance(users_res, list) else getattr(users_res, "users", [])

        total_users = len(all_users)
        pro_users = 0
        free_users = 0
        dept_counts: dict[str, int] = {}

        for u in all_users:
            meta = getattr(u, "user_metadata", None) or (u.get("user_metadata") if isinstance(u, dict) else {}) or {}
            tier = meta.get("tier", "free")
            if tier == "pro_scholar":
                pro_users += 1
            else:
                free_users += 1

            dept = meta.get("department")
            if dept:
                dept_counts[dept] = dept_counts.get(dept, 0) + 1

        # Real trending topics from actual study_logs.focus_topic entries,
        # instead of a hardcoded/mock list
        logs_res = supabase.table("study_logs").select("focus_topic").execute()
        topic_counts: dict[str, int] = {}
        for row in (logs_res.data or []):
            topic = (row.get("focus_topic") or "").strip()
            if topic and topic != "Daily General Log":
                topic_counts[topic] = topic_counts.get(topic, 0) + 1

        trending_topics = [
            {"topic": t, "count": c}
            for t, c in sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        ]
        dept_users = [{"dept": d, "count": c} for d, c in sorted(dept_counts.items(), key=lambda x: x[1], reverse=True)]

        # ৳99/mo per pro user — matches the price shown in your Billing tab.
        # Update this constant if pricing changes rather than hardcoding it twice.
        PRICE_PER_PRO_USER_BDT = 99
        est_revenue_bdt = pro_users * PRICE_PER_PRO_USER_BDT

        response_data = {
            "status": "success",
            "data": {
                "total_users": total_users,
                "pro_users": pro_users,
                "free_users": free_users,
                "active_models": 10,  # count of AI engines you support — static by nature, not user data
                "est_revenue_bdt": est_revenue_bdt,
                "trending_topics": trending_topics,
                "dept_users": dept_users,
            }
        }

        # Save to cache
        _analytics_cache["data"] = response_data
        _analytics_cache["timestamp"] = current_time
        return response_data
    
    except Exception as e:
        print(f"get_admin_analytics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------- SUPPORT TICKETS ----------
# 🔴 Changed "status" to "ticket_status"
@router.get("/tickets")
async def get_tickets(current_user: dict = Depends(get_current_user)):
    require_admin(current_user)
    try:
        res = supabase.table("support_tickets").select("*").eq("status", "open").order("created_at", desc=True).execute()
        return {"status": "success", "data": res.data or []}
    except Exception as e:
        print(f"get_tickets error: {e}")
        return {"status": "success", "data": []}

@router.post("/tickets/{ticket_id}/resolve")
async def resolve_ticket(ticket_id: str, current_user: dict = Depends(get_current_user)):
    require_admin(current_user)
    try:
        # 🔴 Changed "status" to "ticket_status" here as well
        supabase.table("support_tickets").update({"status": "resolved"}).eq("id", ticket_id).execute()
        return {"status": "success"}
    except Exception as e:
        print(f"resolve_ticket error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------- KNOWLEDGE BASE UPLOAD ----------
# 🛡️ RAG 2.0 WORKER (Isolation, Fallback, Audit)

def log_audit(action: str, resource: str, details: str, user_id: str):
    """(18) Audit Log System"""
    try:
        supabase.table("audit_logs").insert({
            "action": action,
            "resource": resource,
            "details": details,
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat()
        }).execute()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Admin non-critical operation suppressed: {e}")


class DailyQuotaExhausted(Exception):
    """Raised when Google's daily embedding quota is hit — retrying won't help until reset."""
    pass

def _is_daily_quota_error(exc: Exception) -> bool:
    return "PerDay" in str(exc)

@retry(
    wait=wait_exponential(multiplier=2, min=4, max=60),
    stop=stop_after_attempt(10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def safe_add_documents(vectorstore, batch):
    try:
        vectorstore.add_documents(batch)
    except Exception as e:
        if _is_daily_quota_error(e):
            # Don't burn 10 retries and ~10 minutes on something that can't succeed today
            raise DailyQuotaExhausted(str(e)) from e
        raise

def load_file_chunks(local_path: str, file_name: str, course_code: str, document_id: str) -> list[Document]:
    """Extracts text chunks from PDF, DOCX, TXT, MD, CSV, or JSON with accurate page/section numbers."""
    lower_name = file_name.lower()
    raw_docs: list[Document] = []
    
    # 1. PDF Documents
    if lower_name.endswith(".pdf"):
        loaded_successfully = False
        try:
            loader = PyPDFLoader(local_path)
            loaded = loader.load()
            if loaded:
                for doc in loaded:
                    page_idx = doc.metadata.get("page", 0)
                    raw_docs.append(Document(
                        page_content=doc.page_content,
                        metadata={
                            "source": file_name,
                            "filename": file_name,
                            "course_code": course_code,
                            "document_id": document_id,
                            "page": page_idx + 1,
                            "page_number": page_idx + 1
                        }
                    ))
                loaded_successfully = True
        except Exception as e:
            print(f"PyPDFLoader warning, trying pypdf: {e}")

        if not loaded_successfully:
            try:
                reader = PdfReader(local_path)
                for i, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if text and text.strip():
                        raw_docs.append(Document(
                            page_content=text.strip(),
                            metadata={
                                "source": file_name,
                                "filename": file_name,
                                "course_code": course_code,
                                "document_id": document_id,
                                "page": i + 1,
                                "page_number": i + 1
                            }
                        ))
            except Exception as pdf_err:
                print(f"pypdf reader error: {pdf_err}")
                raise pdf_err

    # 2. Word Documents (.docx, .doc)
    elif lower_name.endswith((".docx", ".doc")):
        try:
            with zipfile.ZipFile(local_path) as z:
                xml_content = z.read("word/document.xml")
            tree = ET.fromstring(xml_content)
            paragraphs = []
            for p in tree.iter():
                if p.tag.endswith('}p'):
                    p_text = "".join([node.text for node in p.iter() if node.text and node.tag.endswith('}t')])
                    if p_text.strip():
                        paragraphs.append(p_text.strip())
            
            section_size = 5
            for sec_idx, i in enumerate(range(0, len(paragraphs), section_size)):
                sec_text = "\n\n".join(paragraphs[i:i + section_size])
                raw_docs.append(Document(
                    page_content=sec_text,
                    metadata={
                        "source": file_name,
                        "filename": file_name,
                        "course_code": course_code,
                        "document_id": document_id,
                        "page": sec_idx + 1,
                        "page_number": sec_idx + 1
                    }
                ))
        except Exception as docx_err:
            print(f"DOCX extraction fallback: {docx_err}")
            with open(local_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            raw_docs.append(Document(
                page_content=content,
                metadata={"source": file_name, "filename": file_name, "course_code": course_code, "document_id": document_id, "page": 1, "page_number": 1}
            ))

    # 3. Plain Text / Markdown / CSV / JSON
    else:
        try:
            with open(local_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(local_path, "r", encoding="latin-1", errors="ignore") as f:
                content = f.read()
        
        if "\x0c" in content:
            sections = content.split("\x0c")
            for page_idx, sec in enumerate(sections):
                if sec.strip():
                    raw_docs.append(Document(
                        page_content=sec.strip(),
                        metadata={
                            "source": file_name,
                            "filename": file_name,
                            "course_code": course_code,
                            "document_id": document_id,
                            "page": page_idx + 1,
                            "page_number": page_idx + 1
                        }
                    ))
        else:
            raw_docs.append(Document(
                page_content=content,
                metadata={
                    "source": file_name,
                    "filename": file_name,
                    "course_code": course_code,
                    "document_id": document_id,
                    "page": 1,
                    "page_number": 1
                }
            ))

    # Split documents into optimal chunks for embedding
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=150)
    chunks = text_splitter.split_documents(raw_docs)
    
    # Ensure all chunks retain clean, non-null metadata
    for chunk in chunks:
        chunk.metadata["source"] = file_name
        chunk.metadata["filename"] = file_name
        chunk.metadata["course_code"] = course_code
        chunk.metadata["document_id"] = document_id
        if "page" not in chunk.metadata:
            chunk.metadata["page"] = 1
            chunk.metadata["page_number"] = 1

    return chunks


# 🔴 1. The Background RAG Worker (Multi-format + Accurate Page Tracking)
async def enterprise_rag_ingestion(local_path: str, document_id: str, course_code: str, file_name: str):
    try:
        supabase.table("knowledge_base_documents").update({"status": "processing"}).eq("id", document_id).execute()
        
        chunks = load_file_chunks(local_path, file_name, course_code, document_id)
        total_chunks = len(chunks)
        if total_chunks == 0:
            raise ValueError("Document yielded no extractable text.")

        supabase.table("knowledge_base_documents").update({"total_chunks": total_chunks}).eq("id", document_id).execute()
        vectorstore = get_workspace_vectorstore("global_knowledge_base")

        BATCH_SIZE = 100 
        processed = 0
        
        for i in range(0, total_chunks, BATCH_SIZE):
            batch = chunks[i:i + BATCH_SIZE]
            try:
                safe_add_documents(vectorstore, batch)
            except DailyQuotaExhausted as e:
                print(f"🔴 Daily embedding quota exhausted — stopping ingestion, {processed}/{total_chunks} chunks done: {e}")
                supabase.table("knowledge_base_documents").update({
                    "status": "failed",
                    "error_msg": "Daily AI quota exhausted. This document is partially indexed — re-upload or resume tomorrow after quota resets.",
                }).eq("id", document_id).execute()
                return
            except Exception as ai_err:
                print(f"🔥 AI Vector Store Crash Details: {ai_err}")
                raise ai_err
            
            processed += len(batch)
            supabase.table("knowledge_base_documents").update({"processed_chunks": processed}).eq("id", document_id).execute()
            await asyncio.sleep(1)

        supabase.table("knowledge_base_documents").update({"status": "active"}).eq("id", document_id).execute()

    except Exception as e:
        error_message = str(e)
        print(f"🔴 RAG WORKER FAILED: {error_message}")
        supabase.table("knowledge_base_documents").update({"status": "failed", "error_msg": error_message}).eq("id", document_id).execute()
    finally:
        if os.path.exists(local_path):
            try:
                os.remove(local_path)
            except Exception:
                pass


# 🔴 2. The Upload Route (Fast Foreground Upload with Dynamic Content-Types)
@router.post("/knowledge-base/upload")
@limiter.limit("10/minute")

async def upload_knowledge_base_doc(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    course_code: str = Form(...),
    doc_type: str = Form(...),
    current_user: dict = Depends(get_current_user),
):
    require_admin(current_user)
    try:
        contents = await file.read()
        file_hash = hashlib.sha256(contents).hexdigest()
        
        # Smart Deduplication Check
        existing = supabase.table("knowledge_base_documents").select("id, status").eq("file_hash", file_hash).execute()
        if existing.data:
            for old_rec in existing.data:
                supabase.table("knowledge_base_documents").delete().eq("id", old_rec["id"]).execute()
            
        # 1. FAST UPLOAD TO SUPABASE (With Dynamic MIME types)
        safe_filename = file.filename.replace(" ", "_")
        storage_path = f"knowledge_base/{course_code}/{uuid.uuid4()}_{safe_filename}"
        content_type = mimetypes.guess_type(file.filename)[0] or "application/octet-stream"
        public_url = ""
        try:
            supabase.storage.from_("documents").upload(storage_path, contents, {"content-type": content_type})
            public_url = supabase.storage.from_("documents").get_public_url(storage_path)
        except Exception as storage_err:
            print(f"Non-fatal storage notice: {storage_err}")

        # 2. Save locally with collision-free path for RAG Worker
        os.makedirs("uploads/knowledge_base", exist_ok=True)
        local_path = f"uploads/knowledge_base/{uuid.uuid4()}_{safe_filename}"
        with open(local_path, "wb") as f:
            f.write(contents)

        # 3. Insert into Database securely
        document_id = str(uuid.uuid4())
        insert_res = supabase.table("knowledge_base_documents").insert({
            "id": document_id,
            "uploaded_by": current_user.get("sub"),
            "course_code": course_code,
            "doc_type": doc_type,
            "filename": file.filename,
            "storage_path": storage_path,
            "public_url": public_url,
            "file_hash": file_hash,
            "status": "queued",
        }).execute()
        
        # 4. Trigger Background Worker
        background_tasks.add_task(enterprise_rag_ingestion, local_path, document_id, course_code, file.filename)
 
        return {"status": "success", "message": "Document queued for processing.", "document": insert_res.data[0]}
    except Exception as e:
        print(f"Upload Route Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# 📊 RAG 2.0 GET ENDPOINT
# ==========================================
@router.get("/knowledge-base")
async def list_knowledge_base_docs(current_user: dict = Depends(get_current_user)):
    require_admin(current_user)
    try:
        res = supabase.table("knowledge_base_documents").select("*").neq("status", "archived").order("created_at", desc=True).execute()
        return {"status": "success", "data": res.data or []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# 🗑️ RAG 2.0 SOFT DELETE (Archive) ENDPOINT
# ==========================================
@router.put("/knowledge-base/{doc_id}/archive")
async def archive_knowledge_base_doc(doc_id: str, current_user: dict = Depends(get_current_user)):
    require_admin(current_user)
    try:
        # Changes status to archived so it doesn't show in UI and can be ignored by RAG
        supabase.table("knowledge_base_documents").update({"status": "archived"}).eq("id", doc_id).execute()
        return {"status": "success", "message": "Document archived."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# 🗑️ RAG 2.0 DELETE ENDPOINT
# ==========================================
@router.delete("/knowledge-base/{doc_id}")
async def delete_knowledge_base_doc(doc_id: str, current_user: dict = Depends(get_current_user)):
    require_admin(current_user)
    try:
        # 1. Fetch file path from DB
        doc = supabase.table("knowledge_base_documents").select("storage_path").eq("id", doc_id).execute()
        
        # 2. 🔴 SAFELY Delete from Supabase Storage (Ignore if already deleted manually)
        if doc.data:
            storage_path = doc.data[0].get("storage_path")
            if storage_path:
                try:
                    supabase.storage.from_("documents").remove([storage_path])
                except Exception as e:
                    print(f"Storage Warning: File already missing or error - {e}")

        # 3. Delete from Database
        supabase.table("knowledge_base_documents").delete().eq("id", doc_id).execute()
        
        return {"status": "success", "message": "Document permanently deleted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



class NoticeRequest(BaseModel):
    model_config = {"extra": "ignore"}
    raw_text: Optional[str] = None
    content: Optional[str] = None
    text: Optional[str] = None

# ---------- NOTICE PUBLISHING  ----------
@router.post("/notices")
@limiter.limit("10/minute")

async def generate_notice(
    request: Request,
    payload: NoticeRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    ফ্যাকাল্টির দেওয়া সাধারণ টেক্সট বা ইনস্ট্রাকশনকে প্রফেশনাল বাইলিঙ্গুয়াল (বাংলা+ইংরেজি) দাপ্তরিক নোটিশে রূপান্তর করবে
    """
    user_input = (payload.raw_text or payload.content or payload.text or "").strip()
    
    if not user_input:
        raise HTTPException(status_code=400, detail="Please provide the text/content first!")

    prompt = f"""You are the official Administrative AI of the university department of International Relations. 
Convert the following casual message or instruction into a highly formal, professional academic notice in BOTH English and Bengali.

Raw instruction from Teacher: "{user_input}"

Please format strictly as follows:
### 📝 Official Notice (English)
[Write the formal English notice here, maintaining professional university tone, subject header, and date/reference format]

### 📝 দাপ্তরিক বিজ্ঞপ্তি (বাংলা)
[Write the formal Bengali translation of the notice here, maintaining official academic language]
"""
    try:
        client = genai.Client(api_key=gemini_key)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return {"status": "success", "result": response.text}
    except Exception as e:
        print(f"Notice Gen Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate formal notice.")


@router.post("/notices/publish")
async def publish_notice(
    title: str = Form(...),
    date: str = Form(...),
    type: str = Form(...),
    file: UploadFile = File(None),
    current_user: dict = Depends(get_current_user)
):
    require_admin(current_user)
    try:
        file_url = None
        # If admin uploads a PDF with the notice
        if file:
            contents = await file.read()
            ext = os.path.splitext(file.filename)[1]
            safe_name = f"notices/{uuid.uuid4().hex}{ext}"
            supabase.storage.from_("public_assets").upload(safe_name, contents, {"content-type": file.content_type})
            file_url = supabase.storage.from_("public_assets").get_public_url(safe_name)

        # Save to database
        supabase.table("department_notices").insert({
            "id": str(uuid.uuid4()),
            "title": title,
            "date": date,
            "type": type,
            "file_url": file_url,
        }).execute()
        
        return {"status": "success", "message": "Notice published successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
 
 
@router.get("/notices")
async def list_notices():
    """Public — no auth dependency, since notices should be visible to
    students on the Department Hub. If notices should ever contain
    sensitive info, add Depends(get_current_user) back here."""
    try:
        res = supabase.table("notices").select("*").order("publish_date", desc=True).execute()
        return {"status": "success", "data": res.data or []}
    except Exception as e:
        print(f"list_notices error: {e}")
        return {"status": "success", "data": []}


@router.post("/notices/{notice_id}/approve")
async def approve_notice_and_memorize(
    notice_id: str, 
    background_tasks: BackgroundTasks, 
    current_user: dict = Depends(get_current_user)
):
    require_admin(current_user)
    try:
        # 1. Fetch Notice Details
        notice = supabase.table("department_notices").select("*").eq("id", notice_id).execute()
        if not notice.data:
            raise HTTPException(status_code=404, detail="Notice not found")
        
        notice_data = notice.data[0]
        
        # 2. Update Status to Approved
        supabase.table("department_notices").update({"status": "approved"}).eq("id", notice_id).execute()

        # 3. Create a temporary text file for the RAG worker
        temp_notice_path = f"/tmp/notice_{notice_id}.txt"
        with open(temp_notice_path, "w", encoding="utf-8") as f:
            f.write(f"NOTICE TITLE: {notice_data['title']}\n")
            f.write(f"DATE: {notice_data.get('created_at', '')}\n\n")
            f.write(f"CONTENT:\n{notice_data.get('content', 'Attached PDF Notice')}\n")

        # 4. Trigger the exact same RAG pipeline used for PDFs!
        # The AI will now process and memorize this notice.
        background_tasks.add_task(
            enterprise_rag_ingestion,
            local_path=temp_notice_path,
            document_id=notice_id,
            course_code="NOTICE_BOARD", # Scope isolation for notices
            file_name=f"Notice: {notice_data['title']}",
            file_bytes=b"", # Empty bytes as we read from text
            user_id=current_user.get("sub")
        )

        return {"status": "success", "message": "Notice Approved and sent to AI Knowledge Base."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
 
 
# ---------- PENDING FACULTY APPROVAL QUEUE ----------
 
@router.get("/pending-faculty")
async def list_pending_faculty(current_user: dict = Depends(get_current_user)):
    require_admin(current_user)
    try:
        users_res = supabase.auth.admin.list_users()
        all_users = users_res if isinstance(users_res, list) else getattr(users_res, "users", [])
        pending = []
        for u in all_users:
            meta = getattr(u, "user_metadata", None) or (u.get("user_metadata") if isinstance(u, dict) else {}) or {}
            if meta.get("role") == "faculty" and meta.get("account_status") == "pending":
                uid = getattr(u, "id", None) or (u.get("id") if isinstance(u, dict) else None)
                email = getattr(u, "email", None) or (u.get("email") if isinstance(u, dict) else None)
                pending.append({"id": uid, "email": email, "full_name": meta.get("full_name"), "department": meta.get("department"), "designation": meta.get("designation")})
        return {"status": "success", "data": pending}
    except Exception as e:
        print(f"list_pending_faculty error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
 
 
# 🔴 Properly extract the User object from the UserResponse
@router.post("/pending-faculty/{target_user_id}/approve")
async def approve_faculty(target_user_id: str, current_user: dict = Depends(get_current_user)):
    require_admin(current_user)
    try:
        user_resp = supabase.auth.admin.get_user_by_id(target_user_id)
        user_obj = user_resp.user if hasattr(user_resp, 'user') else user_resp
        
        existing_meta = getattr(user_obj, "user_metadata", {}) or {}
        if isinstance(user_obj, dict):
            existing_meta = user_obj.get("user_metadata", {}) or {}
            
        supabase.auth.admin.update_user_by_id(target_user_id, {
            "user_metadata": {**existing_meta, "account_status": "active"}
        })
        return {"status": "success", "message": "Faculty account approved."}
    except Exception as e:
        print(f"approve_faculty error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pending-faculty/{target_user_id}/reject")
async def reject_faculty(target_user_id: str, current_user: dict = Depends(get_current_user)):
    require_admin(current_user)
    try:
        user_resp = supabase.auth.admin.get_user_by_id(target_user_id)
        user_obj = user_resp.user if hasattr(user_resp, 'user') else user_resp
        
        existing_meta = getattr(user_obj, "user_metadata", {}) or {}
        if isinstance(user_obj, dict):
            existing_meta = user_obj.get("user_metadata", {}) or {}
            
        supabase.auth.admin.update_user_by_id(target_user_id, {
            "user_metadata": {**existing_meta, "account_status": "rejected"}
        })
        return {"status": "success", "message": "Faculty account rejected."}
    except Exception as e:
        print(f"reject_faculty error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    
class SupportTicketRequest(BaseModel):
    model_config = {"extra": "forbid"}
    ticket_query: str
    student_department: str

@router.post("/support/auto-reply")
@limiter.limit("10/minute")
async def generate_support_reply(req: SupportTicketRequest, request: Request, current_user: dict = Depends(get_current_user)):
    role = current_user.get("user_metadata", {}).get("role", "guest").lower()
    if role not in ["admin", "faculty"]:
        raise HTTPException(status_code=403, detail="Clearance required.")

    system_prompt = (
        "You are the GSTU Support AI. A student has submitted an issue to the administration. "
        "Write a professional, empathetic, and helpful response to address their query. "
        "Keep it concise (max 2 paragraphs). Do not hallucinate policies."
    )
    
    try:
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"{system_prompt}\n\nStudent Department: {req.student_department}\nIssue: {req.ticket_query}"
        )
        
        return {"status": "success", "reply": response.text}
    except Exception as e:
        return {"status": "error", "message": "Failed to generate AI reply."}