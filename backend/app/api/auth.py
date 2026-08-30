import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel

from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User, Workspace
from app.schemas.user import UserResponse
from app.core.security import get_current_user
from app.core.database import supabase
from supabase import create_client, Client

router = APIRouter()

SUPABASE_URL = os.getenv("SUPABASE_URL")
# MUST use SERVICE_ROLE_KEY to update user metadata and bypass RLS
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") 
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

router = APIRouter()

class SyncUserResponse(BaseModel):
    model_config = {"extra": "forbid"}
    message: str
    is_new_user: bool
    # user: UserResponse
class RoleUpdateRequest(BaseModel):
    model_config = {"extra": "forbid"}
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


# 🔴 AVATAR UPLOAD ENDPOINT
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE_SIZE = 2 * 1024 * 1024 # 2 MB

@router.post("/avatar")
async def upload_avatar(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    try:
        user_id = current_user.get("sub")
        
        # 1. Check Extension
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Only images (JPG, PNG, WEBP) are allowed")
        
        # 2. Check Size
        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="File too large (Max 2MB)")

        # 3. Secure Filename
        safe_filename = f"{user_id}_{uuid.uuid4().hex}{ext}"
        storage_path = f"avatars/{safe_filename}"
        
        # 4. Upload to Supabase
        supabase.storage.from_("public_assets").upload(
            storage_path, 
            contents, 
            {"content-type": file.content_type or "image/jpeg"}
        )
        
        # 5. Get Public URL
        public_url = supabase.storage.from_("public_assets").get_public_url(storage_path)

        return {"status": "success", "avatar_url": public_url}
        
    except Exception as e:
        # 🔴 FIX: Catch all errors and return cleanly, so it doesn't cause a CORS/Fetch error in browser
        print(f"Avatar Upload Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))