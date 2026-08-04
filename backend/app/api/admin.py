from fastapi import APIRouter, Depends, HTTPException
from app.core.security import get_current_user
# প্রোডাকশনে ডাটাবেস (Supabase/PostgreSQL) কানেকশন এখানে থাকবে

router = APIRouter()

@router.get("/analytics")
def get_admin_analytics(current_user: dict = Depends(get_current_user)):
    """অ্যাডমিন ড্যাশবোর্ডের জন্য রিয়েল-টাইম সিস্টেম ডেটা"""
    
    # 🔴 Extracting role from Supabase's user_metadata safely
    user_meta = current_user.get("user_metadata", {})
    role = user_meta.get("role", "student").lower()
    
    # 🔴 Lowercase check
    if role not in ["admin", "faculty"]:
        raise HTTPException(status_code=403, detail="Clearance Level: Admin/Faculty required.")
    
    # ডেমো ডেটা (পরবর্তীতে ডাটাবেস থেকে আসবে)
    MOCK_STATS = {
        "total_users": 1250,
        "pro_users": 340,
        "free_users": 910,
        "active_models": 10,
        "est_revenue_bdt": 340 * 99,
        "trending_topics": [
            {"topic": "Neorealism vs Liberalism", "count": 450},
            {"topic": "South Asian Geopolitics", "count": 320},
            {"topic": "Foreign Policy of Bangladesh", "count": 210}
        ],
        "dept_users": [
            {"dept": "IR", "count": 850},
            {"dept": "Economics", "count": 250},
            {"dept": "Law", "count": 150}
        ]
    }
    
    return {"status": "success", "data": MOCK_STATS}