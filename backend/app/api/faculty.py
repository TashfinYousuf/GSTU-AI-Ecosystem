import os
import logging
import asyncio

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from supabase import create_client, Client
from app.core.security import get_current_user,require_faculty_or_admin
from app.services.core_agents import generate_smart_assessment

# 🔴 Direct Supabase Init
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/overview")
async def get_faculty_overview(current_user: dict = Depends(require_faculty_or_admin)):
    active_students = 0
    try:
        users_res = supabase.auth.admin.list_users()
        all_users = users_res if isinstance(users_res, list) else getattr(users_res, "users", [])
        for user in all_users:
            metadata = getattr(user, "app_metadata", None) or (user.get("app_metadata") if isinstance(user, dict) else {}) or {}
            user_metadata = getattr(user, "user_metadata", None) or (user.get("user_metadata") if isinstance(user, dict) else {}) or {}
            role = metadata.get("role") or user_metadata.get("role")
            if str(role).strip().lower() == "student":
                active_students += 1
    except Exception as e:
        logger.error(f"[FACULTY OVERVIEW] list_users failed: {repr(e)}")

    open_tickets = 0
    try:
        tickets = supabase.table("support_tickets").select("id", count="exact").eq("ticket_status", "open").execute()
        open_tickets = tickets.count or 0
    except Exception as e:
        logger.error(f"[FACULTY OVERVIEW] support_tickets query failed: {repr(e)}")

    return {
        "status": "success",
        "data": {
            "active_students": active_students,
            "open_tickets": open_tickets,
            "faculty_hours_saved": 0,
            "questions_generated": 0,
        }
    }

    
@router.get("/tickets")
async def get_support_tickets(current_user: dict = Depends(get_current_user)):
    """Fetch support desk tickets dynamically"""
    if current_user.get("role") not in ["faculty", "admin"]:
        raise HTTPException(status_code=403)
        
    try:
        res = supabase.table("support_tickets").select("*").order("created_at", desc=True).execute()
        return {"status": "success", "data": res.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class AssessmentRequest(BaseModel):
    model_config = {"extra": "forbid"}
    topic: str

@router.post("/assessment")
async def create_assessment(req: AssessmentRequest, current_user: dict = Depends(get_current_user)):
    """Smart Assessment Generator for Faculty"""
    # 🔴 RBAC Protection: Only Faculty or Admin can generate exams
    user_role = current_user.get("role", "student")
    if user_role not in ["faculty", "admin"]:
        raise HTTPException(status_code=403, detail="Clearance Level: Faculty required.")
        
    try:
        response = generate_smart_assessment(topic=req.topic, user_role=user_role)
        if response.get("status") == "error":
            raise HTTPException(status_code=500, detail=response.get("message"))
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))