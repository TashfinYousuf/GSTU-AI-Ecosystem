import streamlit as st
import os
from supabase import create_client, Client
from streamlit_cookies_controller import CookieController

# Initialize Cookie Controller for persistent sessions
controller = CookieController()

# Initialize Supabase Client
@st.cache_resource
def init_supabase() -> Client:
    # 🔴 NUCLEAR FIX: 1st priority to Render Environment Variables, 2nd to local secrets
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    # If not found in Env Vars, safely try to get from secrets (for local PC)
    if not url or not key:
        try:
            url = st.secrets.get("SUPABASE_URL")
            key = st.secrets.get("SUPABASE_KEY")
        except Exception:
            pass
            
    # If still not found, stop the app safely without throwing dirty tracebacks
    if not url or not key:
        st.error("⚠️ SUPABASE_URL or SUPABASE_KEY is missing in Render Environment Variables!")
        st.stop()
        
    return create_client(url, key)

supabase = init_supabase()

def login_user(email, password):
    """Handles User Login and sets persistent session"""
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if response.user:
            # Store auth token in cookies to prevent auto-logout on refresh
            controller.set('auth_token', response.session.access_token)
            st.session_state['user_id'] = response.user.id
            st.session_state['authenticated'] = True
            
            # Update last active status in usage_tracking (Optional but good for analytics)
            update_usage_tracking(response.user.id)
            return True, "Login Successful!"
    except Exception as e:
        return False, str(e)

def get_user_profile(user_id):
    """Fetches profile data. RLS ensures they can only fetch their own."""
    try:
        # Notice we don't need a WHERE clause for security, RLS handles it automatically!
        response = supabase.table('profiles').select('*').eq('id', user_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        st.error(f"Error fetching profile: {e}")
        return None

def update_usage_tracking(user_id):
    """Example of an RPC or direct update for rate limiting logic"""
    try:
        supabase.table('usage_tracking').upsert({
            'user_id': user_id,
            'last_reset': 'now()'
        }).execute()
    except Exception as e:
        pass # Handle silently in production


# auth_manager.py

def get_oauth_url(provider: str, supabase_client):
    """
    Generates the native Implicit Flow URL using the implicit client options.
    Returns a clean URL containing target redirect destination.
    """
    redirect_uri = "https://gstu-ai-backend.onrender.com" 
    
    try:
        # Client options-এ implicit থাকায় এটি অটোমেটিক্যালি response_type=token ফায়ার করবে
        res = supabase_client.auth.sign_in_with_oauth({
            "provider": provider,
            "options": {
                "redirect_to": redirect_uri
            }
        })
        return res.url
    except Exception as e:
        print(f"❌ OAuth URL Generation Failed: {e}")
        return None

def get_user_profile(user_id: str, supabase_client):
    """
    Fetches user data (like Role/Name) from the database after email login.
    """
    try:
        response = supabase_client.table("users").select("*").eq("id", user_id).single().execute()
        return response.data if response.data else {}
    except Exception as e:
        print(f"Profile fetch info: {e}")
        return {}