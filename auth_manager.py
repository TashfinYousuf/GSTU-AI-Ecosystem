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


def get_oauth_url(provider: str):
    """
    Generates the secure OAuth login URL from Supabase.
    Provider must be either 'google' or 'facebook'.
    """
    # 🔴 IMPORTANT: Use your exact Render live URL here
    redirect_uri = "https://gstu-ir-backend.onrender.com" 
    
    try:
        # Requesting the OAuth URL from Supabase
        res = supabase.auth.sign_in_with_oauth({
            "provider": provider,
            "options": {
                "redirectTo": redirect_uri
            }
        })
        return res.url
    except Exception as e:
        return "#" # Fallback to a dead link if the API call fails