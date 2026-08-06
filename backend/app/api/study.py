import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from supabase import create_client, Client
from app.core.security import get_current_user
from app.services.core_agents import generate_genz_features

# 🔴 Bulletproof Supabase Connection
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

router = APIRouter()

class StudyRequest(BaseModel):
    topic: str
    feature_type: str
    extra_data: dict = {}

@router.post("/gamify")
async def generate_study_content(req: StudyRequest, current_user: dict = Depends(get_current_user)):
    if not current_user.get("sub"): raise HTTPException(status_code=401)
    response = generate_genz_features(topic=req.topic, feature_type=req.feature_type, extra_data=req.extra_data)
    if response.get("status") == "error": raise HTTPException(status_code=500, detail=response.get("message"))
    return response

@router.get("/profile")
async def get_gamification_profile(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id: raise HTTPException(status_code=401)
    
    try:
        user_res = supabase.table("user_gamification").select("*").eq("user_id", user_id).execute()
        user_data = user_res.data[0] if user_res.data else {"xp": 0, "streak": 0}
        
        # 🔴 Get Real Leaderboard (Top 3)
        leaderboard_res = supabase.table("user_gamification").select("name, xp").order("xp", desc=True).limit(3).execute()
        
        return {
            "status": "success",
            "xp": user_data.get("xp", 0),
            "streak": user_data.get("streak", 0),
            "leaderboard": leaderboard_res.data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))