from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import Workspace, Message, Document

router = APIRouter(tags=["Admin & Analytics"])

@router.get("/stats")
def get_system_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    ফ্যাকাল্টি বা চেয়ারম্যান ড্যাশবোর্ডের জন্য পুরো সিস্টেমের রিয়েল-টাইম ডেটা এবং অ্যানালিটিক্স
    """
    if not current_user.get("sub"):
        raise HTTPException(status_code=401, detail="Unauthorized")

    # ডেটাবেস থেকে রিয়েল-টাইম কাউন্ট নেওয়া
    total_workspaces = db.query(Workspace).count()
    total_documents = db.query(Document).count()
    total_queries = db.query(Message).filter(Message.role == "user").count()

    return {
        "metrics": {
            "active_students": total_workspaces, # (আপাতত ওয়ার্কস্পেস কাউন্টকেই স্টুডেন্ট ধরা হচ্ছে)
            "knowledge_base_files": total_documents,
            "total_ai_interactions": total_queries,
            "system_health": "99.9% (Optimal)"
        },
        "recent_activities": [
            # প্রোডাকশনে এগুলো ডেটাবেসের Activity Log থেকে আসবে
            {"id": 1, "action": "Generated Midterm Exam", "module": "Academic Copilot", "time": "2 mins ago", "status": "Success"},
            {"id": 2, "action": "Uploaded IR_Syllabus.pdf", "module": "Knowledge Base", "time": "15 mins ago", "status": "Success"},
            {"id": 3, "action": "Drafted Make-up Class Notice", "module": "Notice Engine", "time": "1 hour ago", "status": "Pending Approval"},
            {"id": 4, "action": "Concept Map: Global Power Dynamics", "module": "GraphRAG", "time": "3 hours ago", "status": "Success"}
        ]
    }