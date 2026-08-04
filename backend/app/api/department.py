from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.core.security import get_current_user
# from app.db.supabase import supabase

router = APIRouter()

@router.get("/notices")
async def get_department_notices(current_user: dict = Depends(get_current_user)):
    """Supabase থেকে ডাইনামিক্যালি ডিপার্টমেন্টের নোটিশ ফেচ করবে"""
    if not current_user.get("sub"):
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    try:
        # Fetching from Supabase table 'notices'
        # response = supabase.table("notices").select("*").order("created_at", desc=True).execute()
        # return {"status": "success", "data": response.data}
        
        # 🔴 Fallback Data until DB Table is populated
        return {
            "status": "success",
            "data": [
                {"id": 1, "title": "Mid-Term Examination Schedule Published", "date": "Aug 02, 2026", "type": "Academic"},
                {"id": 2, "title": "Seminar on South Asian Geopolitics", "date": "Jul 28, 2026", "type": "Event"},
                {"id": 3, "title": "Registration Deadline for Semester 2.1", "date": "Jul 25, 2026", "type": "Admin"},
            ]
        }
    except Exception as e:
        print(f"Notice DB Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch notices")

@router.get("/syllabus")
async def get_department_syllabus(current_user: dict = Depends(get_current_user)):
    """সিলেবাস এবং কোর্সের তালিকা ফেচ করবে"""
    if not current_user.get("sub"):
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    try:
        # Fetching from Supabase table 'courses'
        return {
            "status": "success",
            "data": [
                {"code": "IR-201", "title": "Political Geography", "credits": 3},
                {"code": "IR-202", "title": "Migration Theories", "credits": 3},
                {"code": "IR-203", "title": "Foreign Policy Analysis", "credits": 3},
                {"code": "IR-301", "title": "International Political Economy", "credits": 3},
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch syllabus")