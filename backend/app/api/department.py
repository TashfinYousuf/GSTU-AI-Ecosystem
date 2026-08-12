import os
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.core.security import get_current_user
from supabase import create_client, Client, ClientOptions

# 🔴 Bulletproof Supabase Connection
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

router = APIRouter()

@router.get("/notices")
async def get_department_notices(current_user: dict = Depends(get_current_user)):
    """Supabase থেকে রিয়েল-টাইম নোটিশ ফেচ করবে"""
    if not current_user.get("sub"): raise HTTPException(status_code=401)
    try:
        res = supabase.table("department_notices").select("*").order("created_at", desc=True).execute()
        return {"status": "success", "data": res.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/syllabus")
async def get_department_syllabus(current_user: dict = Depends(get_current_user)):
    """Supabase থেকে রিয়েল-টাইম সিলেবাস ফেচ করবে"""
    if not current_user.get("sub"): raise HTTPException(status_code=401)
    try:
        res = supabase.table("department_syllabus").select("*").order("code").execute()
        return {"status": "success", "data": res.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))