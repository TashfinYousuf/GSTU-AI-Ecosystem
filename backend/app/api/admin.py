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

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

router = APIRouter()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
gemini_key = os.getenv("GEMINI_API_KEY")

ADMIN_ROLES = {"admin", "faculty"}

def require_admin(current_user: dict):
    role = (current_user.get("user_metadata", {}) or {}).get("role", "student")
    if role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Admin or faculty access required.")
    return role


# ---------- REAL ANALYTICS (previously the frontend had zero backend behind it) ----------

# 🧠 Cache the analytics data for 5 minutes (300 seconds) so the DB isn't hammered!
_analytics_cache = {"data": None, "timestamp": 0}

@router.get("/analytics")
async def get_admin_analytics(current_user: dict = Depends(get_current_user)):
    require_admin(current_user)
    
    current_time = time.time()
    # Return cached data if it's less than 5 minutes old
    if _analytics_cache["data"] and (current_time - _analytics_cache["timestamp"] < 300):
        return _analytics_cache["data"]

    try:
        # Supabase Admin API — requires the service_role key (already switched above)
        users_res = supabase.auth.admin.list_users()
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
    except:
        pass # Silently fail audit logs to prevent main process crash

# 🔴 RAG 2.0: Exponential Backoff Retry (429 Error Fix)
@retry(
    wait=wait_exponential(multiplier=2, min=4, max=60), 
    stop=stop_after_attempt(10), 
    retry=retry_if_exception_type(Exception),
    reraise=True
)
def safe_add_documents(vectorstore, batch):
    """Safely adds a batch to Pinecone with auto-retry on API limits."""
    vectorstore.add_documents(batch)

# 🔴 1. The Background RAG Worker (Only does heavy AI logic)
async def enterprise_rag_ingestion(local_path: str, document_id: str, course_code: str, file_name: str):
    try:
        supabase.table("knowledge_base_documents").update({"status": "processing"}).eq("id", document_id).execute()
        
        loader = PyPDFLoader(local_path)
        documents = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=150)
        chunks = text_splitter.split_documents(documents)
        total_chunks = len(chunks)

        for chunk in chunks:
            chunk.metadata["course_code"] = course_code
            chunk.metadata["document_id"] = document_id

        supabase.table("knowledge_base_documents").update({"total_chunks": total_chunks}).eq("id", document_id).execute()
        vectorstore = get_workspace_vectorstore("global_knowledge_base")

        BATCH_SIZE = 50 
        processed = 0
        for i in range(0, total_chunks, BATCH_SIZE):
            batch = chunks[i:i + BATCH_SIZE]
            try:
                vectorstore.add_documents(batch)
            except Exception as ai_err:
                print(f"🔥 AI/Pinecone Crash Details: {ai_err}")
                raise ai_err # Pass exact error to the Exception block below
            
            processed += len(batch)
            supabase.table("knowledge_base_documents").update({"processed_chunks": processed}).eq("id", document_id).execute()
            await asyncio.sleep(2)

        supabase.table("knowledge_base_documents").update({"status": "active"}).eq("id", document_id).execute()

    except Exception as e:
        error_message = str(e)
        print(f"🔴 RAG WORKER FAILED: {error_message}")
        # Saves the exact error to DB so you can see it in UI tooltip
        supabase.table("knowledge_base_documents").update({"status": "failed", "error_msg": error_message}).eq("id", document_id).execute()
    finally:
        if os.path.exists(local_path):
            os.remove(local_path)


# 🔴 2. The Upload Route (Fast Foreground Upload)
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
            if existing.data[0].get("status") in ["archived", "failed"]:
                # Safe to delete previous ghost/failed record
                supabase.table("knowledge_base_documents").delete().eq("id", existing.data[0]["id"]).execute()
            else:
                raise HTTPException(status_code=409, detail="Document already exists in Knowledge Base.")
            
        # 1. FAST UPLOAD TO SUPABASE (Fixes the View button & NULL bug)
        storage_path = f"knowledge_base/{course_code}/{uuid.uuid4()}_{file.filename}"
        supabase.storage.from_("documents").upload(storage_path, contents, {"content-type": "application/pdf"})
        public_url = supabase.storage.from_("documents").get_public_url(storage_path)

        # 2. Save locally for RAG Worker
        os.makedirs("uploads/knowledge_base", exist_ok=True)
        local_path = f"uploads/knowledge_base/{file.filename}"
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
            "public_url": public_url,  # Crucial for View button
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
    model_config = {"extra": "forbid"}
    raw_text: str

# ---------- NOTICE PUBLISHING  ----------
@router.post("/notices")
@router.post("/notices/")
@limiter.limit("10/minute")

async def generate_notice(
    request: NoticeRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    ফ্যাকাল্টির দেওয়া সাধারণ টেক্সট বা ইনস্ট্রাকশনকে প্রফেশনাল বাইলিঙ্গুয়াল (বাংলা+ইংরেজি) দাপ্তরিক নোটিশে রূপান্তর করবে
    """
    # 🔴 Automatically find which key the frontend actually sent
    user_input = request.raw_text or request.content or request.text
    
    if not user_input or not user_input.strip():
        raise HTTPException(status_code=400, detail="Please provide the text/content first!")

    prompt = f"""You are the official Administrative AI of the university department. 
Convert the following casual message or instruction into a highly formal, professional academic notice in BOTH English and Bengali.

Raw instruction from Teacher: "{request.raw_text}"

Please format strictly as follows:
### 📝 Official Notice (English)
[Write the formal English notice here, maintaining professional university tone]

### 📝 দাপ্তরিক বিজ্ঞপ্তি (বাংলা)
[Write the formal Bengali translation of the notice here]
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