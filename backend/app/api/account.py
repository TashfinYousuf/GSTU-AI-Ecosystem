import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from supabase import create_client, Client
from app.core.security import get_current_user

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

router = APIRouter()

# 🔴 The hardcoded admin allowlist you asked for. Only these emails can
# change ANYONE's role (including their own) to "admin" or "faculty".
# Add/remove emails here as your only source of truth — do not duplicate
# this list anywhere else, including the frontend, since a frontend-only
# check is not real security (any user could bypass client-side checks
# by calling the API directly).
ROLE_CHANGE_ALLOWLIST = {
    "yousufaltashfin@gmail.com",
}


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


class RoleUpdate(BaseModel):
    target_user_id: Optional[str] = None  # omit to change your own role
    role: str  # "student" | "faculty" | "admin"


@router.get("/profile")
async def get_profile(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    meta = current_user.get("user_metadata", {}) or {}
    return {
        "status": "success",
        "data": {
            "id": user_id,
            "email": current_user.get("email"),
            "full_name": meta.get("full_name", ""),
            "role": meta.get("role", "student"),
            "tier": meta.get("tier", "free"),
            "can_change_role": current_user.get("email") in ROLE_CHANGE_ALLOWLIST,
        }
    }


@router.patch("/profile")
async def update_profile(payload: ProfileUpdate, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        update_body = {}
        if payload.email:
            update_body["email"] = payload.email
        if payload.full_name is not None:
            existing_meta = current_user.get("user_metadata", {}) or {}
            update_body["user_metadata"] = {**existing_meta, "full_name": payload.full_name}

        if not update_body:
            raise HTTPException(status_code=400, detail="No fields to update.")

        supabase.auth.admin.update_user_by_id(user_id, update_body)
        return {"status": "success", "message": "Profile updated."}
    except HTTPException:
        raise
    except Exception as e:
        print(f"update_profile error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/role")
async def update_role(payload: RoleUpdate, current_user: dict = Depends(get_current_user)):
    """Change a role. Gated by ROLE_CHANGE_ALLOWLIST — only those emails
    may call this successfully, regardless of what the frontend sends or
    what the caller's current role already is. This is what makes the
    Settings dropdown's role-change actually safe to expose in the UI:
    the enforcement lives here, not in whether a <select> is disabled."""
    caller_email = current_user.get("email")
    if caller_email not in ROLE_CHANGE_ALLOWLIST:
        raise HTTPException(status_code=403, detail="You are not authorized to change roles.")

    if payload.role not in {"student", "faculty", "admin"}:
        raise HTTPException(status_code=400, detail="Invalid role.")

    target_id = payload.target_user_id or current_user.get("sub")

    try:
        # Preserve existing metadata on the target user rather than wiping it
        target_user = supabase.auth.admin.get_user_by_id(target_id)
        existing_meta = getattr(target_user, "user_metadata", None) or {}
        if isinstance(target_user, dict):
            existing_meta = target_user.get("user_metadata", {}) or {}

        supabase.auth.admin.update_user_by_id(target_id, {
            "user_metadata": {**existing_meta, "role": payload.role}
        })
        return {"status": "success", "message": f"Role updated to {payload.role}."}
    except Exception as e:
        print(f"update_role error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/account")
async def delete_account(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        # Clean up owned data first (mirrors the /chat/history/all wipe logic)
        ws_res = supabase.table("workspaces").select("id").eq("user_id", user_id).execute()
        workspace_ids = [w["id"] for w in (ws_res.data or [])]
        if workspace_ids:
            supabase.table("messages").delete().in_("workspace_id", workspace_ids).execute()
        supabase.table("workspaces").delete().eq("user_id", user_id).execute()
        supabase.table("projects").delete().eq("user_id", user_id).execute()
        supabase.table("study_logs").delete().eq("user_id", user_id).execute()
        supabase.table("user_gamification").delete().eq("user_id", user_id).execute()

        # Delete the auth account itself
        supabase.auth.admin.delete_user(user_id)

        return {"status": "success", "message": "Account permanently deleted."}
    except Exception as e:
        print(f"delete_account error: {e}")
        raise HTTPException(status_code=500, detail=str(e))