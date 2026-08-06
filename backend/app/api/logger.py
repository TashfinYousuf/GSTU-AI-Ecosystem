import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from supabase import create_client, Client
from app.core.security import get_current_user

SUPABASE_URL = os.getenv("SUPABASE_URL")
# 🔴 FIX: was using the anon key (SUPABASE_KEY) independently of chat.py's
# fix — this file creates its own Supabase client, so switching chat.py to
# service_role never touched this one. Same RLS-blocks-insert issue as
# before, just in a different file. Matching chat.py's pattern here too.
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

router = APIRouter(tags=["Study Logger"])


def award_xp(user_id: str, amount: int, display_name: str):
    """Shared XP-award helper — was duplicated inline in two endpoints below."""
    user_xp_res = supabase.table("user_gamification").select("xp").eq("user_id", user_id).execute()
    current_xp = user_xp_res.data[0]["xp"] if user_xp_res.data else 0
    supabase.table("user_gamification").upsert({
        "user_id": user_id,
        "xp": current_xp + amount,
        "name": display_name
    }).execute()


class LogRequest(BaseModel):
    topic: str
    minutes: int


@router.post("/log")
async def save_study_log(req: LogRequest, current_user: dict = Depends(get_current_user)):
    """Save daily study minutes to database and award XP"""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401)

    try:
        supabase.table("study_logs").insert({
            "user_id": user_id,
            "study_minutes": req.minutes,
            "focus_topic": req.topic
        }).execute()

        award_xp(user_id, 50, current_user.get("user_metadata", {}).get("full_name", "Scholar"))

        return {"status": "success", "message": f"Awesome! Logged {req.minutes} mins and earned 50 XP!"}
    except Exception as e:
        print(f"save_study_log error: {e}")  # 🔴 real error now visible server-side, not just in the response body
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/toast")
async def get_daily_toast(current_user: dict = Depends(get_current_user)):
    """Generates a dynamic AI motivational toast notification"""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401)

    try:
        logs_res = supabase.table("study_logs").select("study_minutes").eq("user_id", user_id).execute()
        total_mins = sum(log["study_minutes"] for log in logs_res.data) if logs_res.data else 0

        if total_mins == 0:
            msg = "Welcome to GSTU OS! Time to log your first study session and earn XP! 🚀"
        elif total_mins < 120:
            msg = f"You've studied {total_mins} mins so far. Don't let your batchmates beat you in the Leaderboard! 🔥"
        else:
            msg = f"Elite Scholar Alert! {total_mins} mins logged. You are going to ace your IR exams! 🏆"

        return {"status": "success", "message": msg}
    except Exception as e:
        print(f"get_daily_toast error: {e}")
        return {"status": "success", "message": "Welcome back, Scholar! Keep pushing your limits today! ✨"}


class DailyLogRequest(BaseModel):
    study_hours: float
    # 🔴 FIX: sleep_hours and mood were required, but DailyLogger.tsx's quick
    # form only collects study_hours/topics/notes and has no sleep or mood
    # fields at all — every submission from that component would have failed
    # Pydantic validation with a 422 even before touching the database. Made
    # optional with sensible defaults so ONE endpoint serves both the full
    # Settings-modal logger AND the quick-log card.
    sleep_hours: Optional[float] = None
    mood: Optional[str] = None
    topics_learned: Optional[str] = None
    notes: Optional[str] = None


@router.post("/daily-log")
async def save_daily_log(req: DailyLogRequest, current_user: dict = Depends(get_current_user)):
    """Save daily log — accepts either the full Settings-modal shape
    (study_hours, sleep_hours, mood) or the quick-log card shape
    (study_hours, topics_learned, notes). Both write to the same table."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401)

    try:
        focus_topic = req.topics_learned.strip() if req.topics_learned else "Daily General Log"

        insert_payload = {
            "user_id": user_id,
            "study_minutes": int(req.study_hours * 60),
            "focus_topic": focus_topic,
        }
        if req.sleep_hours is not None:
            insert_payload["sleep_hours"] = req.sleep_hours
        if req.mood:
            insert_payload["mood"] = req.mood
        if req.notes:
            insert_payload["notes"] = req.notes

        supabase.table("study_logs").insert(insert_payload).execute()

        award_xp(user_id, 100, current_user.get("user_metadata", {}).get("full_name", "Scholar"))

        return {"status": "success", "message": "Daily Log saved! +100 XP awarded. Student Mapping updated."}
    except Exception as e:
        print(f"save_daily_log error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mapping")
async def get_student_mapping(current_user: dict = Depends(get_current_user)):
    """Fetch logs and generate AI Evaluation for Settings -> Performance Tab"""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401)

    try:
        res = (
            supabase.table("study_logs")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(7)
            .execute()
        )
        logs = res.data if res.data else []
        logs.reverse()

        ai_eval = "Start logging your daily sessions to get AI insights."
        if logs:
            # 🔴 FIX: sleep_hours/study_minutes are now optional per-row (quick-log
            # entries may not include sleep_hours), so `l['sleep_hours']` would
            # raise a KeyError on any row that used the quick-log path. Using
            # .get(...) instead so mixed full-log/quick-log rows don't crash.
            logs_with_sleep = [l for l in logs if l.get("sleep_hours") is not None]
            avg_sleep = (sum(l.get("sleep_hours", 0) for l in logs_with_sleep) / len(logs_with_sleep)) if logs_with_sleep else None
            avg_study = sum(l.get("study_minutes", 0) for l in logs) / 60 / len(logs)

            if avg_sleep is not None and avg_sleep < 6:
                ai_eval = "⚠️ High Burnout Risk: You are sleeping less than 6 hours. Cognitive retention drops by 40%. Get some rest!"
            elif avg_sleep is not None and avg_study > 4 and avg_sleep >= 7:
                ai_eval = "🌟 Elite Performance: Outstanding study hours with balanced rest. Keep this momentum for your IR exams!"
            elif avg_sleep is not None:
                ai_eval = "✅ Steady Progress: Good balance, but try to push your study hours slightly higher for peak performance."
            else:
                ai_eval = f"📚 {avg_study:.1f}h/day logged on average. Add sleep tracking in the full logger for deeper insights."

        return {"status": "success", "data": logs, "ai_evaluation": ai_eval}
    except Exception as e:
        print(f"get_student_mapping error: {e}")
        raise HTTPException(status_code=500, detail=str(e))