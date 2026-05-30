import streamlit as st
from supabase import create_client, Client
from streamlit_cookies_controller import CookieController

# Initialize Cookie Controller for persistent sessions
controller = CookieController()

# Initialize Supabase Client
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
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