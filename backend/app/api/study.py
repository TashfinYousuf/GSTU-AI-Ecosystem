import os
import json
import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from google import genai
from supabase import create_client, Client
from app.core.security import get_current_user, get_optional_current_user
from app.services.core_agents import generate_genz_features

SUPABASE_URL = os.getenv("SUPABASE_URL")
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
async def generate_study_content(req: StudyRequest, current_user: dict = Depends(get_optional_current_user)):
    response = generate_genz_features(topic=req.topic, feature_type=req.feature_type, extra_data=req.extra_data)
    if response.get("status") == "error":
        raise HTTPException(status_code=500, detail=response.get("message"))
    return response


@router.get("/profile")
async def get_gamification_profile(current_user: dict = Depends(get_optional_current_user)):
    user_id = current_user.get("sub") if current_user else "guest_session"
    if user_id == "guest_session":
        return {"status": "success", "xp": 0, "streak": 0, "leaderboard": []}

    try:
        user_res = supabase.table("user_profiles").select("total_xp, streak").eq("id", user_id).execute()
        user_data = user_res.data[0] if user_res.data else {"total_xp": 0, "streak": 0}

        leaderboard_res = supabase.table("user_profiles").select("full_name, total_xp").order("total_xp", desc=True).limit(5).execute()

        formatted_lb = [{"name": u.get("full_name", "Scholar"), "xp": u.get("total_xp", 0)} for u in (leaderboard_res.data or [])]

        return {
            "status": "success",
            "xp": user_data.get("total_xp", 0),
            "streak": user_data.get("streak", 0),
            "leaderboard": formatted_lb,
        }
    except Exception as e:
        print(f"get_gamification_profile error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/xp")
async def award_xp(amount: float, current_user: dict = Depends(get_optional_current_user)):
    user_id = current_user.get("sub") if current_user else "guest_session"
    if user_id == "guest_session":
        return {"status": "success", "xp": 0}

    try:
        existing = supabase.table("user_profiles").select("total_xp").eq("id", user_id).execute()
        current_xp = existing.data[0]["total_xp"] if existing.data else 0
        new_xp = max(0.0, current_xp + amount)

        supabase.table("user_profiles").update({
            "total_xp": new_xp,
        }).eq("id", user_id).execute()

        return {"status": "success", "xp": new_xp}
    except Exception as e:
        print(f"award_xp error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/routine")
async def generate_study_routine(req: RoutineRequest, current_user: dict = Depends(get_optional_current_user)):
    user_id = current_user.get("sub") if current_user else "guest_session"
    if user_id == "guest_session":
        raise HTTPException(status_code=401, detail="Authentication required.")

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
        supabase.table("smart_routines").insert({
            "user_id": user_id,
            "routine_data": data,
            "created_at": datetime.datetime.now().isoformat()
        }).execute()
        return {"status": "success", "data": data}
    except Exception as e:
        print(f"generate_study_routine error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate study routine.")


@router.get("/routine")
async def get_saved_routine(current_user: dict = Depends(get_optional_current_user)):
    user_id = current_user.get("sub") if current_user else "guest_session"
    if user_id == "guest_session":
        return {"status": "success", "data": None}

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
async def generate_mock_exam(req: AssessmentRequest, current_user: dict = Depends(get_optional_current_user)):
    user_id = current_user.get("sub") if current_user else "guest_session"
    if user_id == "guest_session": raise HTTPException(status_code=401)

    import random
    import datetime
    seed = random.randint(1000, 99999) # 🔴 Ensures fresh questions every time!
    current_time = datetime.datetime.now().isoformat()

    if req.role in ["Faculty", "Admin"]:
        prompt = f"""Act as an Elite Academic Question Setter for IR. Topic: {req.topic}.
Random Seed: {seed} | Time: {current_time}
Generate EXACTLY 10 tough, analytical Multiple Choice Questions. Do not repeat standard or common questions. Think out of the box.
Return EXACTLY this JSON shape:
{{
    "assessment_type": "Quiz",
    "mcqs": [
        {{"q": "Tough Question text?", "options": ["A", "B", "C", "D"], "answer": "Correct Option"}}
    ]
}}"""
    else:
        prompt = f"""Act as a strict university professor creating a mock exam on: '{req.topic}'. Difficulty: {req.difficulty}
Random Seed: {seed} | Time: {current_time}
Exam Rules: Time: 3 Hours | Full Marks: 60 | Answer any 4 questions (15 Marks each).
Generate EXACTLY 6 questions (2 Critical, 2 Medium, 2 Easy). Do NOT repeat common questions.
Return EXACTLY this JSON shape:
{{
    "assessment_type": "Mock Exam",
    "exam_rules": "Time: 3 Hours | Full Marks: 60 | Answer any 4 questions (15 Marks each).",
    "questions": [
        {{
            "q": "The question text",
            "difficulty": "Critical/Medium/Easy",
            "hints": ["hint 1", "hint 2"],
            "key_points": ["key point 1", "key point 2", "key point 3"],
            "model_answer": "A precise 60-word ideal answer."
        }}
    ]
}}"""

    try:
        data = call_gemini_json(prompt)
        return {"status": "success", "data": data}
    except Exception as e:
        print(f"generate_mock_exam error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate assessment.")
    

# ==================================================================
# 🔒 INTERNAL SUBSCRIPTION & TRIAL ENGINE
# ==================================================================
def get_effective_tier(user_id: str):
    """Calculates if user gets the 30-Day Free Pro Advantage"""
    if user_id == "guest_session": return "free", 50
    
    try:
        res = supabase.table("user_profiles").select("subscription_tier, trial_started_at").eq("id", user_id).execute()
        if not res.data: return "free", 50
        
        user = res.data[0]
        tier = user.get("subscription_tier", "free")
        
        # Admins and Paid users
        if tier in ["pro_scholar", "premium", "Admin"]:
            return "pro", 100
            
        # 🔴 30-Day Free Trial Logic
        trial_start = user.get("trial_started_at")
        if trial_start:
            start_date = datetime.datetime.fromisoformat(trial_start.replace("Z", "+00:00")).replace(tzinfo=None)
            days_used = (datetime.datetime.utcnow() - start_date).days
            if days_used <= 30:
                return "pro_trial", 100 # They get Pro limits!
                
        return "free", 50 # Trial expired, downgrade to free
    except:
        return "free", 50


# ==================================================================
# 🃏 FLASHCARD ENGINE (Authoritative Logic)
# ==================================================================
@router.post("/flashcards/generate")
async def generate_flashcards(req: StudyRequest, current_user: dict = Depends(get_optional_current_user)):
    user_id = current_user.get("sub") if current_user else "guest_session"
    tier, daily_limit = get_effective_tier(user_id)
    
    if user_id != "guest_session":
        # 1. Check Limits & Cooldown
        user_res = supabase.table("user_profiles").select("flashcards_used_today, last_flashcard_time").eq("id", user_id).execute()
        if user_res.data:
            used_today = user_res.data[0].get("flashcards_used_today", 0)
            last_time = user_res.data[0].get("last_flashcard_time")
            
            if used_today >= daily_limit:
                raise HTTPException(status_code=429, detail=f"Daily limit reached ({daily_limit}/{daily_limit}). Upgrade to Pro.")
                
            if last_time:
                last_dt = datetime.datetime.fromisoformat(last_time.replace("Z", "+00:00")).replace(tzinfo=None)
                if (datetime.datetime.utcnow() - last_dt).total_seconds() < 3600:
                    raise HTTPException(status_code=429, detail="Brain cooling down! Flashcards locked for 1 hour.")

    # 2. Generate EXACTLY 10 UNIQUE Cards
    req.extra_data = req.extra_data or {}
    req.extra_data["count"] = 10 
    
    res = generate_genz_features(req.topic, "flashcards", req.extra_data)
    
    if res["status"] == "success" and user_id != "guest_session":
        supabase.table("user_profiles").update({
            "last_flashcard_time": datetime.datetime.utcnow().isoformat()
        }).eq("id", user_id).execute()
        
    return res

@router.post("/flashcards/submit")
async def submit_flashcard_answer(is_correct: bool, current_user: dict = Depends(get_optional_current_user)):
    """Backend Authoritative XP Calculator"""
    user_id = current_user.get("sub") if current_user else "guest_session"
    if user_id == "guest_session": return {"status": "guest", "xp_delta": 0}
    
    # 🔴 Strict Business Rules from app.py
    xp_delta = 5.0 if is_correct else -2.5
    
    try:
        # Secure XP Transaction
        supabase.table("xp_transactions").insert({
            "user_id": user_id, "amount": xp_delta, "source": "flashcard"
        }).execute()
        
        # Update User Total (Aggregate) & Usage Count
        user_res = supabase.table("user_profiles").select("total_xp, flashcards_used_today").eq("id", user_id).execute()
        current_xp = user_res.data[0].get("total_xp", 0)
        new_xp = max(0, current_xp + xp_delta)
        new_usage = user_res.data[0].get("flashcards_used_today", 0) + 1
        
        supabase.table("user_profiles").update({
            "total_xp": new_xp, "flashcards_used_today": new_usage
        }).eq("id", user_id).execute()
        
        return {"status": "success", "xp_delta": xp_delta, "total_xp": new_xp}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================================================================
# ⚔️ DEBATE ARENA ENGINE (Authoritative Timers)
# ==================================================================
@router.post("/debate/start")
async def start_debate(duration_mins: int, current_user: dict = Depends(get_optional_current_user)):
    user_id = current_user.get("sub") if current_user else "guest_session"
    tier, _ = get_effective_tier(user_id)
    
    # 🔴 Server-Side Duration Enforcement
    if tier == "free" and duration_mins > 15:
        raise HTTPException(status_code=403, detail="Free users can only debate up to 15 mins. Upgrade for 60-min endurance battles.")
    if duration_mins > 60:
        raise HTTPException(status_code=400, detail="Maximum debate time is 60 mins.")
        
    return {
        "status": "success", 
        "duration_seconds": duration_mins * 60,
        "started_at": datetime.datetime.utcnow().isoformat()
    }

@router.post("/debate/judge")
async def judge_debate(req: StudyRequest, duration_mins: int, current_user: dict = Depends(get_optional_current_user)):
    user_id = current_user.get("sub") if current_user else "guest_session"
    
    res = generate_genz_features(req.topic, "judge", req.extra_data)
    
    if res["status"] == "success" and user_id != "guest_session":
        verdict = res["data"]
        # 🔴 XP = Duration if User Wins!
        if verdict.get("winner", "").lower() == "user":
            xp_reward = float(duration_mins)
            
            supabase.table("xp_transactions").insert({
                "user_id": user_id, "amount": xp_reward, "source": "debate_win"
            }).execute()
            
            # Aggregate XP
            user_res = supabase.table("user_profiles").select("total_xp").eq("id", user_id).execute()
            new_xp = user_res.data[0].get("total_xp", 0) + xp_reward
            supabase.table("user_profiles").update({"total_xp": new_xp}).eq("id", user_id).execute()
            
            res["xp_rewarded"] = xp_reward
            res["total_xp"] = new_xp
            
    return res