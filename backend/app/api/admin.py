import os
import uuid
import shutil

from pydantic import BaseModel
from google import genai
from google.genai import types

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

@router.get("/analytics")
async def get_admin_analytics(current_user: dict = Depends(get_current_user)):
    require_admin(current_user)

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
    except Exception as e:
        print(f"get_admin_analytics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------- SUPPORT TICKETS ----------

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
        contents = await file.read()
        storage_path = f"knowledge_base/{course_code}/{uuid.uuid4()}_{file.filename}"

        # Upload to Supabase Storage — bucket "documents" must exist
        # (Supabase Dashboard -> Storage -> New Bucket -> "documents")
        supabase.storage.from_("documents").upload(
            storage_path, contents, {"content-type": file.content_type or "application/octet-stream"}
        )
        public_url = supabase.storage.from_("documents").get_public_url(storage_path)

        # Save metadata row — this is what makes the file findable/listable later,
        # and what your RAG/embedding pipeline should read from to chunk+embed
        insert_res = supabase.table("knowledge_base_documents").insert({
            "id": str(uuid.uuid4()),
            "uploaded_by": user_id,
            "course_code": course_code,
            "doc_type": doc_type,
            "filename": file.filename,
            "storage_path": storage_path,
            "public_url": public_url,
            "status": "uploaded",  # flip to "processed" once your embedding job finishes
        }).execute()

        return {
            "status": "success",
            "message": f"'{file.filename}' uploaded and queued for processing.",
            "document": insert_res.data[0] if insert_res.data else None,
        }
    except Exception as e:
        print(f"upload_knowledge_base_doc error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge-base/upload")
async def upload_rag_document(
    file: UploadFile = File(...), 
    current_user: dict = Depends(get_current_user)
):
    user_role = current_user.get("user_metadata", {}).get("role", "student").lower()
    
    # 🔴 STRICT RBAC: Only approved admins/faculty can upload to the Global AI Brain
    if user_role not in ["admin", "faculty"]:
        raise HTTPException(status_code=403, detail="Clearance required. Only approved faculty can upload core documents.")
        
    try:
        # 1. Save file locally for processing
        os.makedirs("uploads/knowledge_base", exist_ok=True)
        file_path = f"uploads/knowledge_base/{file.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 2. Extract and Chunk Text (Exactly like original app.py)
        if file.filename.endswith(".pdf"):
            loader = PyPDFLoader(file_path)
            documents = loader.load()
            
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
            chunks = text_splitter.split_documents(documents)
            
            # 3. Add to Global Vector Store (FAISS/Chroma)
            get_workspace_vectorstore(chunks, metadata={"source": file.filename})
            
            return {"status": "success", "message": f"{len(chunks)} chunks embedded into Global AI Brain."}
        else:
            raise HTTPException(status_code=400, detail="Only PDF files are currently supported for academic ingestion.")
            
    except Exception as e:
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