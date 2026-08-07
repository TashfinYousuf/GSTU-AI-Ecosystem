import os
import shutil

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User, Workspace
from app.schemas.user import UserResponse
from app.core.security import get_current_user
from supabase import create_client, Client

router = APIRouter()

SUPABASE_URL = os.getenv("SUPABASE_URL")
# MUST use SERVICE_ROLE_KEY to update user metadata and bypass RLS
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") 
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

router = APIRouter()

class SyncUserResponse(BaseModel):
    message: str
    is_new_user: bool
    # user: UserResponse
class RoleUpdateRequest(BaseModel):
    role: str

@router.post("/sync")
def sync_user_with_db(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user) # Phase 0 এর JWT মিডলওয়্যার
):
    """
    ইউজার Supabase এ লগইন/সাইনআপ করার পর ফ্রন্টএন্ড থেকে এই এপিআই কল হবে
    """
    # Supabase টোকেন থেকে ইউজারের আইডি (sub) এবং ইমেইল বের করছি
    user_id = current_user.get("sub") 
    user_email = current_user.get("email")

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    # ১. চেক ইউজার আগে থেকেই ডেটাবেসে আছে কিনা
    existing_user = db.query(User).filter(User.id == user_id).first()
    
    if existing_user:
        return {
            "message": "User already exists",
            "is_new_user": False,
            "user": existing_user
        }

    # ২. না থাকলে নতুন ইউজার ক্রিয়েট
    new_user = User(
        id=user_id,
        email=user_email,
        # Supabase মেটাডেটা থেকে নাম নিচ্ছি, না পেলে ডিফল্ট স্ট্রিং বসবে
        full_name=current_user.get("user_metadata", {}).get("full_name", "Student")
    )
    db.add(new_user)
    
    # ৩. নতুন ইউজারের জন্য স্বয়ংক্রিয়ভাবে ৩টি ডিফল্ট ওয়ার্কস্পেস তৈরি
    default_workspaces = [
        Workspace(user_id=user_id, name="International Relations", description="Academic core, syllabus, and research"),
        Workspace(user_id=user_id, name="Projects", description="GSTU AI Assistant and startup ideas"),
        Workspace(user_id=user_id, name="Personal", description="Routine, goals, and personal tracking")
    ]
    db.add_all(default_workspaces)
    
    # ৪. ডেটাবেসে ফাইনালি সেভ
    db.commit()
    # db.refresh(new_user)
    
    return {
        "message": "New user and default workspaces initialized",
        "is_new_user": True,
        "user": new_user
    }


# 🔴 ROLE UPDATE ENDPOINT (Resolves the 404 Error)
@router.patch("/role")
async def update_user_role(req: RoleUpdateRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    try:
        # Update user metadata via Supabase Admin API
        res = supabase_admin.auth.admin.update_user_by_id(
            user_id, 
            {"user_metadata": {"role": req.role}}
        )
        return {"status": "success", "message": f"Role updated to {req.role}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 🔴 AVATAR UPLOAD ENDPOINT
@router.post("/avatar")
async def upload_avatar(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401)
        
    try:
        # Create directory if not exists
        os.makedirs("uploads/avatars", exist_ok=True)
        file_path = f"uploads/avatars/{user_id}_{file.filename}"
        
        # Save file locally (In production, use AWS S3 or Supabase Storage)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        avatar_url = f"http://127.0.0.1:8000/{file_path}"
        
        # Update user metadata with new avatar URL
        supabase_admin.auth.admin.update_user_by_id(
            user_id, 
            {"user_metadata": {"avatar_url": avatar_url}}
        )
        return {"status": "success", "avatar_url": avatar_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))