import os
import logging

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import List, Optional
from google import genai

from dotenv import load_dotenv
from sqlalchemy.orm import Session
from supabase import create_client, Client

from app.core.limiter import limiter
from app.core.security import get_current_user
from app.core.vector_store import get_workspace_vectorstore
from app.core.database import get_db
from app.models.user import Message

# 🔴 Force .env to load API Keys
load_dotenv(override=True)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

gemini_key = os.getenv("GEMINI_API_KEY")

router = APIRouter(tags=["Academic Tools"])

logger = logging.getLogger(__name__)

# ==========================
# 📌 Request Models
# ==========================

class RoutineRequest(BaseModel):
    model_config = {"extra": "forbid"}
    workspace_id: str
    study_hours: int = 4
    focus_areas: List[str] = ["International Relations Theories", "Political Geography"]

class ExamRequest(BaseModel):
    model_config = {"extra": "forbid"}
    workspace_id: str
    topic: str
    difficulty: str = "University Level"

# 🔴 STRICT SCHEMA: Frontend MUST send these exact keys!
class AcademicTaskRequest(BaseModel):
    model_config = {"extra": "ignore"}
    task_type: str         # "grading" | "formalize" | "rubric" | "summary" | "flashcards" | "notice"
    content: Optional[str] = ""
    topic: Optional[str] = "General"  
    workspace_id: Optional[str] = None
    extra_data: Optional[dict] = {}

class NoticeRequest(BaseModel):
    model_config = {"extra": "ignore"}
    raw_text: Optional[str] = None
    content: Optional[str] = None

# ==========================
# 📌 API Routes
# ==========================
@router.post("/mock-exam")
@limiter.limit("10/minute")

async def generate_mock_exam(
    request: Request,
    req_body: ExamRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    ChromaDB (RAG) থেকে ডেটা নিয়ে নির্দিষ্ট টপিকের ওপর ডিপার্টমেন্টাল স্ট্যান্ডার্ডের মক এক্সাম জেনারেট করবে।
    """
    if not current_user.get("sub"):
        raise HTTPException(status_code=401, detail="Unauthorized")

    # 🔴 1. Fetch Context from ChromaDB (Workspace + Global Knowledge Base)
    retrieved_docs = []
    if req_body.workspace_id:
        try:
            ws_vs = get_workspace_vectorstore(req_body.workspace_id)
            ws_matches = ws_vs.similarity_search(req_body.topic, k=3)
            if ws_matches:
                retrieved_docs.extend(ws_matches)
        except Exception as e:
            logger.warning(f"Workspace Search Warning: {e}")

    try:
        kb_vs = get_workspace_vectorstore("global_knowledge_base")
        kb_matches = kb_vs.similarity_search(req_body.topic, k=3)
        if kb_matches:
            retrieved_docs.extend(kb_matches)
    except Exception as e:
        logger.warning(f"Global KB Search Warning: {e}")

    if retrieved_docs:
        context_parts = []
        for d in retrieved_docs:
            src = d.metadata.get("source") or d.metadata.get("filename") or "Knowledge Base"
            page = d.metadata.get("page_number") or d.metadata.get("page")
            page_info = f", Page {page}" if page else ""
            context_parts.append(f"[Source: 《{src}》{page_info}]\n{d.page_content}")
        context_text = "\n\n".join(context_parts)
    else:
        context_text = "No internal departmental syllabus or textbook excerpts found for this topic."

    # 🔴 2. Dynamic Prompting with RAG
    prompt = f"""You are a University Professor generating a {req_body.difficulty} level Mock Exam on the topic '{req_body.topic}'.
Please generate 3 broad analytical questions and 5 short conceptual questions.
Use the following context from the department's syllabus/past papers if available. Provide an Answer Key or grading criteria at the end.

--- KNOWLEDGE BASE CONTEXT ---
{context_text}
------------------------------
"""
    try:
        client = genai.Client(api_key=gemini_key)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return {"status": "success", "result": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to generate mock exam.")


@router.post("/generate")
@limiter.limit("10/minute")

async def generate_academic_content(
    request: Request,
    req_body: AcademicTaskRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Rubrics, Summary বা Flashcards তৈরি করার জন্য ইউনিভার্সাল রাউট
    """
    if not current_user.get("sub"):
        raise HTTPException(status_code=401, detail="Unauthorized")

    context_text = ""
    retrieved_gen_docs = []
    if req_body.workspace_id:
        try:
            ws_vs = get_workspace_vectorstore(req_body.workspace_id)
            ws_matches = ws_vs.similarity_search(req_body.topic or "international relations", k=3)
            if ws_matches:
                retrieved_gen_docs.extend(ws_matches)
        except Exception as e:
            logger.warning(f"Workspace Search Warning: {e}")

    try:
        kb_vs = get_workspace_vectorstore("global_knowledge_base")
        kb_matches = kb_vs.similarity_search(req_body.topic or "international relations", k=3)
        if kb_matches:
            retrieved_gen_docs.extend(kb_matches)
    except Exception as e:
        logger.warning(f"Global KB Search Warning: {e}")

    if retrieved_gen_docs:
        parts = []
        for d in retrieved_gen_docs:
            src = d.metadata.get("source") or d.metadata.get("filename") or "Knowledge Base"
            page = d.metadata.get("page_number") or d.metadata.get("page")
            page_info = f", Page {page}" if page else ""
            parts.append(f"[Source: 《{src}》{page_info}]\n{d.page_content}")
        context_text = "\n\n".join(parts)

    if req_body.task_type == "rubric":
        topic_title = (req_body.topic or req_body.content or "University Assignment").strip()
        additional_info = f"\nSpecific Instructions / Criteria: {req_body.content}" if req_body.content and req_body.content != req_body.topic else ""
        prompt = f"""You are a University Professor and Senior Academic Evaluator in International Relations.
Create a comprehensive, professional, curriculum-standard grading rubric for: '{topic_title}'.{additional_info}

Structure the rubric clearly with Markdown tables:
1. **Assignment Overview & Objective**
2. **Evaluation Criteria Breakdown** (Table with columns: Criteria, Weight %, Exemplary (A: 80-100%), Proficient (B: 65-79%), Developing (C: 50-64%), Unsatisfactory (F: <50%))
3. **Core Performance Dimensions**:
   - Theoretical Grounding & IR Frameworks (Realism, Liberalism, Constructivism, etc.)
   - Critical Analysis & Empirical Evidence
   - Structure, Coherence, & Academic Tone
   - Citation & Referencing Integrity
4. **Scoring Scale & Conversion Guidelines**
5. **Guidance Notes for Evaluators & Students**
Context: {context_text}"""
    elif req_body.task_type == "notice":
        topic_or_content = (req_body.content or req_body.topic or "").strip()
        prompt = f"""You are the official Academic Administrative Assistant of the university department of International Relations.
Convert the following casual message or instruction into a highly formal, professional academic notice in BOTH English and Bengali.

Raw instruction from Teacher: "{topic_or_content}"

Please format strictly as follows:
### 📝 Official Notice (English)
[Write the formal English notice here, maintaining professional university tone, subject header, reference number, and date format]

### 📝 দাপ্তরিক বিজ্ঞপ্তি (বাংলা)
[Write the formal Bengali translation of the notice here, maintaining official academic language]"""
    elif req_body.task_type == "summary":
        prompt = f"Provide an academic summary of '{req_body.topic}'. Context: {context_text}"
    elif req_body.task_type == "flashcards":
        prompt = f"Create 5 academic flashcards for studying '{req_body.topic}'. Format as Q: and A:. Context: {context_text}"
    elif req_body.task_type == "grading":
        prompt = f"Grade the following student submission on '{req_body.topic}' and give detailed feedback with a suggested score. Content: {req_body.content}. Context: {context_text}"
    elif req_body.task_type == "formalize":
        prompt = f"Rewrite the following text in formal academic English: {req_body.content}"
    else:
        raise HTTPException(status_code=400, detail="Invalid task type.")

    try:
        client = genai.Client(api_key=gemini_key)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return {"status": "success", "result": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Generation failed.")


@router.get("/analytics/{user_id}")
def get_student_analytics(user_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """স্টুডেন্টদের ড্যাশবোর্ডের জন্য ডাটাবেস থেকে রিয়েল-টাইম ডেটা"""
    if user_id != current_user.get("sub") and current_user.get("user_metadata", {}).get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to view this user's analytics.")
        
    try:
        # 🔴 SQLAlchemy Query: Fetch actual message count for this user
        # total_queries = db.query(Message).filter(Message.user_id == user_id).count()
        
        # ✅ Supabase Code (Get workspaces first, then count messages):
        workspaces_res = supabase.table("workspaces").select("id").eq("user_id", user_id).execute()
        workspace_ids = [w["id"] for w in (workspaces_res.data or [])]

        total_queries = supabase.table("messages").select("*", count="exact").in_("workspace_id", workspace_ids).execute().count or 0
  
        # 🔴 Dynamic Calculation based on real usage
        hours_saved = round((total_queries * 15) / 60, 1)
        retention = min(15 + (total_queries * 2), 85)
        cgpa_boost = min(2.50 + (total_queries * 0.05), 4.00)

        return {
            "status": "success",
            "data": {
                "hours_saved": hours_saved,
                "retention_boost": retention,
                "predicted_cgpa": format(cgpa_boost, ".2f")
            }
        }
    except Exception as e:
        print(f"Analytics DB Error: {e}")
        return {"status": "success", "data": {"hours_saved": 0, "retention_boost": 0, "predicted_cgpa": "0.00"}}