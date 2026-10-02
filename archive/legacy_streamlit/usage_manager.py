import datetime
from auth_manager import supabase

# =====================================================================
# ⚙️ SAAS CONFIGURATION (BETA PHASE)
# =====================================================================
FREE_BETA_LIMIT = 20  # Free users get 20 queries per cycle
RESET_HOURS = 6       # Quota resets every 6 hours instead of 24

PREMIUM_MODELS = [
    "openai/gpt-4o-2024-08-06", 
    "anthropic/claude-3.5-sonnet", 
    "gemini-2.5-pro", 
    "qwen/qwen-2.5-72b-instruct",
    "llama-3.3-70b-versatile"
]

def is_model_premium(selected_model):
    """Returns True if the selected model requires a Pro subscription."""
    return selected_model in PREMIUM_MODELS

def check_rate_limit(user_id, user_tier):
    """
    Validates if the free user has remaining queries for the current cycle.
    Returns: (True/False, "Message")
    """
    # 1. Pro Scholar & Admin Bypass: Unlimited Access
    if user_tier in ["pro_scholar", "Admin"]:
        return True, "Success"

    # 2. Free Tier Usage Check
    try:
        res = supabase.table("usage_tracking").select("*").eq("user_id", user_id).execute()
        
        # Create record if new user
        if not res.data:
            supabase.table("usage_tracking").insert({"user_id": user_id, "daily_requests": 0}).execute()
            return True, "Success"
        
        usage = res.data[0]
        last_reset = datetime.datetime.fromisoformat(usage["last_reset"].replace('Z', '+00:00'))
        now = datetime.datetime.now(datetime.timezone.utc)
        
        # Reset logic (Every 6 hours for Beta)
        if (now - last_reset).total_seconds() >= (RESET_HOURS * 3600):
            supabase.table("usage_tracking").update({"daily_requests": 0, "last_reset": "now()"}).eq("user_id", user_id).execute()
            return True, "Success"
        
        # Limit Exceeded Check
        if usage["daily_requests"] >= FREE_BETA_LIMIT:
            return False, f"🛑 **Usage Limit Reached!** \n\nYou have exhausted your {FREE_BETA_LIMIT} free queries for this {RESET_HOURS}-hour cycle. Please upgrade to Pro Scholar for limitless access."
        
        return True, "Success"
    except Exception as e:
        return True, f"Bypass on database error: {e}" 

def increment_usage(user_id, user_tier):
    """Increments the query count for free users after a successful generation."""
    if user_tier in ["pro_scholar", "Admin"]:
        return 
        
    try:
        res = supabase.table("usage_tracking").select("daily_requests").eq("user_id", user_id).execute()
        if res.data:
            current_req = res.data[0]["daily_requests"]
            supabase.table("usage_tracking").update({"daily_requests": current_req + 1}).eq("user_id", user_id).execute()
    except:
        pass