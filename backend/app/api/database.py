from supabase import create_client, Client
import os

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# --- Notices API ---
def get_department_notices(department="IR", limit=5):
    """সর্বশেষ নোটিশগুলো ফেচ করার জন্য"""
    try:
        response = supabase.table("notices") \
            .select("*") \
            .eq("department", department) \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()
        return response.data
    except Exception as e:
        return {"error": str(e)}

# --- Syllabus API ---
def get_semester_syllabus(semester="2.1"):
    """নির্দিষ্ট সেমিস্টারের (যেমন 2.1) সিলেবাস ফেচ করার জন্য"""
    try:
        response = supabase.table("syllabus") \
            .select("*") \
            .eq("semester", semester) \
            .execute()
        return response.data
    except Exception as e:
        return {"error": str(e)}