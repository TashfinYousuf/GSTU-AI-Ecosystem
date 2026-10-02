import os
import uuid
import asyncio

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User, Workspace
from app.schemas.user import UserResponse
from app.core.security import get_current_user
from app.core.database import supabase
from app.services.database import get_vector_db
from supabase import create_client, Client


router = APIRouter()

SUPABASE_URL = os.getenv("SUPABASE_URL")
# MUST use SERVICE_ROLE_KEY to update user metadata and bypass RLS
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") 
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


class SyncUserResponse(BaseModel):
    model_config = {"extra": "forbid"}
    message: str
    is_new_user: bool
    # user: UserResponse
class RoleUpdateRequest(BaseModel):
    model_config = {"extra": "forbid"}
    role: str

@router.post("/sync")
async def sync_user_with_db(current_user: dict = Depends(get_current_user)):
    """Sync user and create default workspaces securely in Supabase"""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user token")

    try:
        # Check if workspaces already exist (Non-blocking)
        res = await asyncio.to_thread(
            lambda: supabase.table("workspaces").select("id").eq("user_id", user_id).execute()
        )
        
        # If no workspaces, create defaults in the right Supabase table!
        if not res.data:
            default_workspaces = [
                {"user_id": user_id, "name": "International Relations", "description": "Core academic materials"},
                {"user_id": user_id, "name": "Projects & Research", "description": "Thesis and assignments"},
                {"user_id": user_id, "name": "Personal Notes", "description": "Private study notes"}
            ]
            await asyncio.to_thread(
                lambda: supabase.table("workspaces").insert(default_workspaces).execute()
            )
            
        return {"status": "success", "message": "User synced and workspaces verified."}
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Sync error: {e}")
        raise HTTPException(status_code=500, detail="Database sync failed")


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