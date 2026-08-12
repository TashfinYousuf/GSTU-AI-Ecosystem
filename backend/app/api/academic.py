import os
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from google import genai
from dotenv import load_dotenv

from sqlalchemy.orm import Session
from app.core.security import get_current_user
from app.core.vector_store import get_workspace_vectorstore
from app.core.database import get_db
from app.models.user import Message
from supabase import create_client, Client

# 🔴 Force .env to load API Keys
load_dotenv(override=True)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

gemini_key = os.getenv("GEMINI_API_KEY")

router = APIRouter(tags=["Academic Tools"])

# ==========================
# 📌 Request Models
# ==========================

class RoutineRequest(BaseModel):
    workspace_id: str
    study_hours: int = 4
    focus_areas: List[str] = ["International Relations Theories", "Political Geography"]

class ExamRequest(BaseModel):
    workspace_id: str
    topic: str
    difficulty: str = "University Level"

# 🔴 STRICT SCHEMA: Frontend MUST send these exact keys!
class AcademicTaskRequest(BaseModel):
    task_type: str         # "grading" or "formalize"
    content: str           # The actual text to be processed
    topic: Optional[str] = "General"  
    extra_data: Optional[dict] = {}

class NoticeRequest(BaseModel):
    raw_text: str

# ==========================
# 📌 API Routes
# ==========================
@router.post("/mock-exam")
async def generate_mock_exam(
    request: ExamRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    ChromaDB (RAG) থেকে ডেটা নিয়ে নির্দিষ্ট টপিকের ওপর ডিপার্টমেন্টাল স্ট্যান্ডার্ডের মক এক্সাম জেনারেট করবে।
    """
    if not current_user.get("sub"):
        raise HTTPException(status_code=401, detail="Unauthorized")

    # 🔴 1. Fetch Context from ChromaDB
    context_text = ""
    try:
        vectorstore = get_workspace_vectorstore(request.workspace_id)
        similar_docs = vectorstore.similarity_search(request.topic, k=4)
        if similar_docs:
            context_text = "\n\n".join([doc.page_content for doc in similar_docs])
    except Exception as e:
        print(f"Vector Search Warning: {e}")

    # 🔴 2. Dynamic Prompting with RAG
    prompt = f"""You are a University Professor generating a {request.difficulty} level Mock Exam on the topic '{request.topic}'.
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
async def generate_academic_content(
    request: AcademicTaskRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Rubrics, Summary বা Flashcards তৈরি করার জন্য ইউনিভার্সাল রাউট।
    """
    if not current_user.get("sub"):
        raise HTTPException(status_code=401, detail="Unauthorized")

    context_text = ""
    try:
        vectorstore = get_workspace_vectorstore(request.workspace_id)
        similar_docs = vectorstore.similarity_search(request.topic, k=3)
        if similar_docs:
            context_text = "\n\n".join([doc.page_content for doc in similar_docs])

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if request.task_type == "rubric":
        prompt = f"Create a detailed university-level grading rubric for an assignment on '{request.topic}'. Context: {context_text}"
    elif request.task_type == "summary":
        prompt = f"Provide an academic summary of '{request.topic}'. Context: {context_text}"
    elif request.task_type == "flashcards":
        prompt = f"Create 5 academic flashcards for studying '{request.topic}'. Format as Q: and A:. Context: {context_text}"
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


@router.post("/notice")
async def generate_notice(
    request: NoticeRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    ফ্যাকাল্টির দেওয়া সাধারণ টেক্সট বা ইনস্ট্রাকশনকে প্রফেশনাল বাইলিঙ্গুয়াল (বাংলা+ইংরেজি) দাপ্তরিক নোটিশে রূপান্তর করবে।
    """
    if not current_user.get("sub"):
        raise HTTPException(status_code=401, detail="Unauthorized")

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