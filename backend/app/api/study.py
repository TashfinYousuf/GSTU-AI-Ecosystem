import os
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from google import genai
from supabase import create_client, Client
from app.core.security import get_current_user
from app.services.core_agents import generate_genz_features

SUPABASE_URL = os.getenv("SUPABASE_URL")
# 🔴 FIX: same recurring bug as chat.py/logger.py before this — was using
# the anon key independently, subject to RLS blocking inserts/updates.
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

gemini_key = os.getenv("GEMINI_API_KEY")

router = APIRouter(tags=["Study Hub"])


class StudyRequest(BaseModel):
    topic: str
    feature_type: str
    extra_data: dict = {}


class RoutineRequest(BaseModel):
    weak_topics: list[str] = []
    strong_topics: list[str] = []
    target_cgpa: float = 3.5


class AssessmentRequest(BaseModel):
    topic: str
    difficulty: str = "Medium"


def call_gemini_json(prompt: str) -> dict:
    client = genai.Client(api_key=gemini_key)
    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
    raw_text = response.text.replace("```json", "").replace("```", "").strip()
    return json.loads(raw_text)


@router.post("/gamify")
async def generate_study_content(req: StudyRequest, current_user: dict = Depends(get_current_user)):
    if not current_user.get("sub"):
        raise HTTPException(status_code=401)
    response = generate_genz_features(topic=req.topic, feature_type=req.feature_type, extra_data=req.extra_data)
    if response.get("status") == "error":
        raise HTTPException(status_code=500, detail=response.get("message"))
    return response


@router.get("/profile")
async def get_gamification_profile(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401)

    try:
        user_res = supabase.table("user_gamification").select("*").eq("user_id", user_id).execute()
        user_data = user_res.data[0] if user_res.data else {"xp": 0, "streak": 0}

        leaderboard_res = supabase.table("user_gamification").select("name, xp").order("xp", desc=True).limit(3).execute()

        return {
            "status": "success",
            "xp": user_data.get("xp", 0),
            "streak": user_data.get("streak", 0),
            "leaderboard": leaderboard_res.data,
        }
    except Exception as e:
        print(f"get_gamification_profile error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/xp")
async def award_xp(amount: float, current_user: dict = Depends(get_current_user)):
    """🔴 NEW: this endpoint didn't exist at all — the React Study Hub page
    calls `setXp(prev => prev + 5)` on a correct flashcard answer, which
    only updates local state. Nothing persisted it, so XP reset to the
    last-saved DB value on every reload. Call this from the frontend
    alongside the local setXp update to actually save it."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401)

    safe_amount = int(float(amount))

    try:
        existing = supabase.table("user_gamification").select("xp").eq("user_id", user_id).execute()
        current_xp = existing.data[0]["xp"] if existing.data else 0
        new_xp = max(0, current_xp + amount)

        supabase.table("user_gamification").upsert({
            "user_id": user_id,
            "xp": new_xp,
            "name": current_user.get("user_metadata", {}).get("full_name", "Scholar"),
        }).execute()

        return {"status": "success", "xp": new_xp}
    except Exception as e:
        print(f"award_xp error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# 🔴 NEW: /routine and /assessment — these were called by
# AcademicCopilotPage.tsx (`fetchAPI("/study/routine")`,
# `fetchAPI("/study/assessment")`) but never existed in this file at all.
# Every "Smart Study Routine" and "Mock Exam Generator" click has been
# failing silently. Response shapes below match exactly what the frontend
# already expects to render (routineData.day_1..day_7, assessmentData.questions[]).
# ==========================================

@router.post("/routine")
async def generate_study_routine(req: RoutineRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401)

    prompt = f"""Act as an elite academic study planner for a university IR student.
Weak topics needing focus: {', '.join(req.weak_topics) or 'general review'}
Strong topics (light review only): {', '.join(req.strong_topics) or 'none specified'}
Target CGPA goal: {req.target_cgpa}

Design a personalized 7-day study routine. Return EXACTLY this JSON shape:
{{
    "day_1": {{"focus_subject": "Subject/topic name", "strategy": "1-2 sentence actionable plan for the day"}},
    "day_2": {{"focus_subject": "...", "strategy": "..."}},
    "day_3": {{"focus_subject": "...", "strategy": "..."}},
    "day_4": {{"focus_subject": "...", "strategy": "..."}},
    "day_5": {{"focus_subject": "...", "strategy": "..."}},
    "day_6": {{"focus_subject": "...", "strategy": "..."}},
    "day_7": {{"focus_subject": "...", "strategy": "..."}},
    "ai_advice": "One paragraph of overall strategic advice for hitting the target CGPA."
}}"""

    try:
        data = call_gemini_json(prompt)
        return {"status": "success", "data": data}
    except Exception as e:
        print(f"generate_study_routine error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate study routine.")


@router.get("/routine")
async def get_saved_routine(current_user: dict = Depends(get_current_user)):
    """Backs the Study Hub page's on-mount fetch of any existing routine."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401)

    try:
        res = (
            supabase.table("smart_routines")
            .select("routine_data")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if res.data:
            return {"status": "success", "data": {"routine_data": res.data[0]["routine_data"]}}
        return {"status": "success", "data": None}
    except Exception as e:
        print(f"get_saved_routine error: {e}")
        return {"status": "success", "data": None}


@router.post("/assessment")
async def generate_mock_exam(req: AssessmentRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401)

    prompt = f"""Act as a strict university IR professor creating a mock exam on: '{req.topic}'.
Difficulty level: {req.difficulty}

Generate 3 exam-style questions. Return EXACTLY this JSON shape:
{{
    "assessment_type": "Mock Exam",
    "exam_rules": "One sentence describing exam format/rules for the student.",
    "questions": [
        {{
            "q": "The question text",
            "difficulty": "{req.difficulty}",
            "hints": ["hint 1", "hint 2"],
            "key_points": ["key point the answer must cover 1", "key point 2", "key point 3"],
            "model_answer": "A full model answer paragraph."
        }}
    ]
}}"""

    try:
        data = call_gemini_json(prompt)
        return {"status": "success", "data": data}
    except Exception as e:
        print(f"generate_mock_exam error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate mock exam.")