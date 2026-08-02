from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from app.core.database import get_db
from app.models.user import Workspace
from app.core.security import get_current_user # JWT ভেরিফায়ার

router = APIRouter()

# ফ্রন্টএন্ডে পাঠানোর জন্য Pydantic রেসপন্স স্কিমা
class WorkspaceResponse(BaseModel):
    id: str
    name: str
    description: str

    class Config:
        from_attributes = True

@router.get("", response_model=List[dict])
@router.get("/")
def get_user_workspaces(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    লগইন করা ইউজারের সবগুলো ওয়ার্কস্পেস ফেচ করার API
    """
    user_id = current_user.get("sub")
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized request")

    # ইউজারের আইডির ওপর ভিত্তি করে ডেটাবেস থেকে ওয়ার্কস্পেসগুলো খুঁজে বের করা
    workspaces = db.query(Workspace).filter(Workspace.user_id == user_id).all()
    
    # ফ্রন্টএন্ডে পাঠানোর জন্য ডিকশনারি ফরমেটে রিটার্ন করছি
    return [
        {
            "id": str(ws.id),
            "name": ws.name,
            "description": ws.description
        } for ws in workspaces
    ]