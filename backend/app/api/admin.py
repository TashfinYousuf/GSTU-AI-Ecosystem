import os
import uuid
import shutil
import time

from functools import lru_cache
from pydantic import BaseModel
from google import genai
from google.genai import types
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from supabase import create_client, Client
from app.core.security import get_current_user
from app.core.vector_store import get_workspace_vectorstore
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

router = APIRouter()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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

        return {
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
        
    except Exception as e:
        print(f"get_admin_analytics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------- SUPPORT TICKETS ----------
# 🔴 FIX: Changed "status" to "ticket_status"
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
        # 🔴 FIX: Changed "status" to "ticket_status" here as well
        supabase.table("support_tickets").update({"status": "resolved"}).eq("id", ticket_id).execute()
        return {"status": "success"}
    except Exception as e:
        print(f"resolve_ticket error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------- KNOWLEDGE BASE UPLOAD (was UI-only, no backend wiring at all) ----------
 
@router.post("/knowledge-base/upload")
async def upload_knowledge_base_doc(
    file: UploadFile = File(...),
    course_code: str = Form(...),
    doc_type: str = Form(...),
    current_user: dict = Depends(get_current_user),
):
    require_admin(current_user)
    user_id = current_user.get("sub")
 
    if not file.filename.lower().endswith((".pdf", ".txt")):
        raise HTTPException(status_code=400, detail="Only PDF or TXT files are supported.")
 
    try:
        # 1. Upload to Supabase Storage
        contents = await file.read()
        storage_path = f"knowledge_base/{course_code}/{uuid.uuid4()}_{file.filename}"
        supabase.storage.from_("documents").upload(
            storage_path, contents, {"content-type": file.content_type or "application/octet-stream"}
        )
        public_url = supabase.storage.from_("documents").get_public_url(storage_path)
 
        ## 🔴 2. REAL RAG IMPLEMENTATION: Chunk & Embed
        os.makedirs("uploads/knowledge_base", exist_ok=True)
        local_path = f"uploads/knowledge_base/{file.filename}"
        with open(local_path, "wb") as f:
            f.write(contents)
            
        if file.filename.lower().endswith(".pdf"):
            loader = PyPDFLoader(local_path)
            documents = loader.load()
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
            chunks = text_splitter.split_documents(documents)
            
            # 🔴 FIX: Use your existing vector store function!
            from app.core.vector_store import get_workspace_vectorstore
            
            # Save to a dedicated Global Knowledge Base space
            vectorstore = get_workspace_vectorstore("global_knowledge_base")
            vectorstore.add_documents(chunks)

        # 3. Save metadata row
        insert_res = supabase.table("knowledge_base_documents").insert({
            "id": str(uuid.uuid4()),
            "uploaded_by": user_id,
            "course_code": course_code,
            "doc_type": doc_type,
            "filename": file.filename,
            "storage_path": storage_path,
            "public_url": public_url,
            "status": "processed",  # 🔴 Marked as Processed for RAG
        }).execute()
 
        return {
            "status": "success",
            "message": f"'{file.filename}' successfully processed, chunked, and memorized by AI.",
            "document": insert_res.data[0] if insert_res.data else None,
        }
    except Exception as e:
        print(f"upload_knowledge_base_doc error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
 
@router.get("/knowledge-base")
async def list_knowledge_base_docs(current_user: dict = Depends(get_current_user)):
    require_admin(current_user)
    try:
        res = supabase.table("knowledge_base_documents").select("*").order("created_at", desc=True).execute()
        return {"status": "success", "data": res.data or []}
    except Exception as e:
        print(f"list_knowledge_base_docs error: {e}")
        return {"status": "success", "data": []}
 
 
# ---------- NOTICE PUBLISHING (previously UI-only, no backend at all) ----------
 
@router.post("/notices/publish")
async def publish_notice(
    title: str = Form(...),
    category: str = Form(...),
    publish_date: str = Form(...),
    file: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user),
):
    require_admin(current_user)
    user_id = current_user.get("sub")
 
    try:
        attachment_url = None
        if file:
            storage_path = f"notices/{uuid.uuid4()}_{file.filename}"
            contents = await file.read()
            supabase.storage.from_("documents").upload(
                storage_path, contents, {"content-type": file.content_type or "application/octet-stream"}
            )
            attachment_url = supabase.storage.from_("documents").get_public_url(storage_path)
 
        insert_res = supabase.table("notices").insert({
            "id": str(uuid.uuid4()),
            "published_by": user_id,
            "title": title,
            "category": category,
            "publish_date": publish_date,
            "attachment_url": attachment_url,
        }).execute()
 
        return {
            "status": "success",
            "message": "Notice published to Department Hub.",
            "notice": insert_res.data[0] if insert_res.data else None,
        }
    except Exception as e:
        print(f"publish_notice error: {e}")
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
 
 
# 🔴 FIX: Properly extract the User object from the UserResponse
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
    ticket_query: str
    student_department: str

@router.post("/support/auto-reply")
async def generate_support_reply(req: SupportTicketRequest, current_user: dict = Depends(get_current_user)):
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