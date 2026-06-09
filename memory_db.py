# memory_db.py
import os
import logging
import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Initialize Supabase Client securely
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# 1. USER PROFILE & WEAKNESS GRAPH LOGIC
# ==========================================
def get_or_create_student_profile(user_id: str, email: str, name: str):
    """Fetch profile or create a default one for a new student."""
    try:
        res = supabase.table("user_profiles").select("*").eq("id", user_id).execute()
        if res.data:
            return res.data[0]
        else:
            # Create new profile with default academic baseline
            new_profile = {
                "id": user_id,
                "email": email,
                "full_name": name,
                "role": "Student",
                "academic_weaknesses": {} 
            }
            supabase.table("user_profiles").insert(new_profile).execute()
            return new_profile
    except Exception as e:
        logger.error(f"Profile Error: {e}")
        return None


def update_weakness_graph(user_id: str, course_name: str, status: str):
    """Update dynamic weakness based on AI chats and quizzes (e.g., status='Weak' or 'Mastered')."""
    try:
        profile = supabase.table("user_profiles").select("academic_weaknesses").eq("id", user_id).execute()
        if profile.data:
            current_weaknesses = profile.data[0].get("academic_weaknesses", {})
            current_weaknesses[course_name] = status
            
            supabase.table("user_profiles").update({
                "academic_weaknesses": current_weaknesses
            }).eq("id", user_id).execute()
            return True
    except Exception as e:
        logger.error(f"Weakness Update Error: {e}")
        return False

# ==========================================
# 2. DYNAMIC STUDY PLAN LOGIC
# ==========================================
def save_study_plan(user_id: str, plan_type: str, plan_data: dict):
    """Save the AI-generated routine to the database."""
    try:
        supabase.table("study_plans").insert({
            "user_id": user_id,
            "plan_type": plan_type,
            "generated_plan": plan_data
        }).execute()
        return True
    except Exception as e:
        # 🔴 এররটি গিলে না খেয়ে সরাসরি X-Ray Debugger-এর কাছে পাঠিয়ে দেবে
        raise Exception(f"Supabase Database Error: {str(e)}")
    

def update_student_onboarding(user_id: str, semester: str, interest: str, career_goal: str):
    """স্টুডেন্টের অনবোর্ডিং ডেটা সেভ করে"""
    try:
        supabase.table("user_profiles").update({
            "current_semester": semester,
            "core_interest": interest,
            "career_goal": career_goal,
            "is_onboarded": True
        }).eq("id", user_id).execute()
        return True
    except Exception as e:
        logger.error(f"Onboarding Save Error: {e}")
        return False
    

def log_study_session(user_id, topic, hours_spent, mood_score):
    """
    ইউজারের প্রতিদিনের স্টাডি ডাটা সেভ করে।
    mood_score: ১ থেকে ৫ (৫ মানে দারুণ পড়াশোনা হয়েছে)।
    """
    try:
        supabase.table("study_sessions").insert({
            "user_id": user_id,
            "topic": topic,
            "hours": hours_spent,
            "mood": mood_score,
            "date": datetime.datetime.now().isoformat()
        }).execute()
        
        # Trigger an immediate analysis to see if they need a retention boost
        if hours_spent < 1 and mood_score < 3:
            return "alert: low_productivity"
        return "success"
    except Exception as e:
        logger.error(f"Study Session Log Error: {e}")
        return "error"