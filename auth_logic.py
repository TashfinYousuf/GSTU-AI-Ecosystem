import os
import tempfile
import secrets
import logging
import html
from socket import AF_INET, SOCK_STREAM
import streamlit as st
from supabase import create_client, Client
import os
from dotenv import load_dotenv

# কনস্ট্যান্ট এবং লগার সেটআপ
logger = logging.getLogger(__name__)
SESSION_MAX_AGE_SEC = 86400
OTP_EXPIRY_SEC = 300

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") # Ensure this is correct in .env

@st.cache_resource
def get_supabase() -> Client:
    # 🔴  Added a fallback check to prevent the crash
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Supabase credentials missing! Check your .env file.")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase()

def init_auth_session():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "user_email" not in st.session_state:
        st.session_state.user_email = None
    if "username_id" not in st.session_state:
        st.session_state.username_id = None
    if "user_name" not in st.session_state: # 🔴 Added user_name to prevent crash
        st.session_state.user_name = "User"

def get_oauth_url(provider):
    # 🔴 STRICT WEB REDIRECT (Prevents Mobile Deep Link Crash on Browser)
    return f"{SUPABASE_URL}/auth/v1/authorize?provider={provider}&redirect_to=http://localhost:8501/"
    
def login_user(email, password):
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if response.user:
            st.session_state.logged_in = True
            st.session_state.user_email = response.user.email
            st.session_state.username_id = response.user.id
            
            # 🔴 Fetching actual name and role from Supabase Metadata
            meta = response.user.user_metadata
            st.session_state.user_name = meta.get("full_name", email.split("@")[0])
            st.session_state.user_role = meta.get("role", "Student")
            
            st.session_state.username_id = response.user.id # FIXED
            return True, "Login Successful!"
    except Exception as e:
        return False, f"Login Failed: {str(e)}"

def logout_user():
    try:
        supabase.auth.sign_out()
        st.session_state.logged_in = False
        st.session_state.user_email = None
        st.session_state.username_id = None # FIXED
        st.query_params.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")

import streamlit as st

def render_auth_interface():
    # 🎨 Silicon Valley Dark/Glassmorphism Theme
    st.markdown("""
        <style>
        /* Modern Dark Gradient Background */
        .stApp {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: white;
        }
        
        /* Glassmorphism Login Container */
        .login-box {
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            padding: 40px;
            max-width: 450px;
            margin: 10vh auto;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.3);
            text-align: center;
        }
        
        /* Premium Input Fields */
        div[data-baseweb="input"] > div {
            background-color: rgba(255, 255, 255, 0.05) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 8px !important;
            color: white !important;
        }
        div[data-baseweb="input"] > div:focus-within {
            border-color: #10a37f !important;
            box-shadow: 0 0 0 1px #10a37f !important;
        }
        
        /* Glowing Gradient Button */
        .stButton > button {
            width: 100%;
            background: linear-gradient(90deg, #10a37f, #0d8266) !important;
            color: white !important;
            border: none !important;
            padding: 12px !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            letter-spacing: 0.5px !important;
            transition: all 0.3s ease !important;
        }
        .stButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 8px 20px rgba(16, 163, 127, 0.4) !important;
        }
        </style>
        
        <div class="login-box">
            <h1 style="margin-bottom: 5px; font-weight: 700; background: -webkit-linear-gradient(#fff, #cbd5e1); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">GSTU AI System</h1>
            <p style="color: #94a3b8; font-size: 14px; margin-bottom: 30px;">Sign in to access elite agentic research tools</p>
        </div>
    """, unsafe_allow_html=True)

    # 🔐 Streamlit Native Inputs over the CSS box
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        email = st.text_input("University or Personal Email", placeholder="name@gstu.edu.bd")
        
        # Simple Logic Flow
        if st.button("Send Magic Link / OTP"):
            if email:
                # 🔴 Here you will call Supabase Auth API
                # supabase.auth.sign_in_with_otp({"email": email})
                st.success(f"Verification code sent to {email}!")
                st.session_state.show_otp_field = True
            else:
                st.error("Please enter a valid email.")
                
        if st.session_state.get("show_otp_field", False):
            otp = st.text_input("Enter 6-digit Code", type="password")
            if st.button("Verify & Login"):
                # 🔴 Verify OTP API Call here
                st.success("Welcome aboard!")
                # cookie_controller.set(...)
                st.rerun()

# Call this function when user is not authenticated
def render_auth_interface():
    st.markdown("""
        <style>
        .auth-container {
            background: linear-gradient(145deg, rgba(20,20,20,0.8), rgba(15,15,15,0.9));
            padding: 40px;
            border-radius: 20px;
            border: 1px solid rgba(16, 163, 127, 0.3);
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.6);
            backdrop-filter: blur(15px);
            text-align: center;
            max-width: 450px;
            margin: auto;
        }
        .social-btn {
            display: flex; align-items: center; justify-content: center; width: 100%;
            padding: 12px; margin-bottom: 15px; border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.1); background: rgba(30, 30, 30, 0.6);
            color: #e0e0e0 !important; text-decoration: none !important;
            font-size: 16px; font-weight: 500; transition: 0.3s;
        }
        .social-btn:hover { background: rgba(40, 40, 40, 0.9); border-color: #10a37f; color: #ffffff !important;}
        .social-icon { width: 24px; height: 24px; margin-right: 12px; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h2 style='text-align: center; color: white;'>Welcome to GSTU AI ✨</h2>", unsafe_allow_html=True)
    
    # 🔴 RESTORED SIGN UP TABS
    tab1, tab2 = st.tabs(["🔒 Sign In", "📝 Sign Up"])
    
    with tab1:
        st.markdown("<div class='auth-container'>", unsafe_allow_html=True)
        st.markdown(f"""
            <a href="{get_oauth_url('google')}" target="_self" class="social-btn">
                <img src="https://upload.wikimedia.org/wikipedia/commons/c/c1/Google_%22G%22_logo.svg" class="social-icon"> Continue with Google
            </a>
            <a href="{get_oauth_url('facebook')}" target="_self" class="social-btn">
                <img src="https://upload.wikimedia.org/wikipedia/commons/b/b8/2021_Facebook_icon.svg" class="social-icon"> Continue with Facebook
            </a>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='color:#777; margin: 15px 0;'>OR CONTINUE WITH EMAIL</div>", unsafe_allow_html=True)
        login_email = st.text_input("Email", key="login_email")
        login_password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Sign In →", use_container_width=True):
            success, msg = login_user(login_email, login_password)
            if success:
                st.rerun()
            else:
                st.error(msg)
        st.markdown("</div>", unsafe_allow_html=True)

    with tab2:
        st.markdown("<div class='auth-container'>", unsafe_allow_html=True)
        st.info("Sign up manually if you don't want to use Google/Facebook.")
        new_name = st.text_input("Full Name")
        new_email = st.text_input("Email Address", key="signup_email")
        new_dept = st.selectbox("Department", ["IR", "CSE", "EEE", "BBA", "Law"])
        new_pass = st.text_input("Create Password", type="password")
        
        if st.button("Create Account", use_container_width=True):
            if new_email and new_pass:
                # Basic signup logic (you can expand this to save to user_profiles table)
                res = supabase.auth.sign_up({"email": new_email, "password": new_pass})
                if res: st.success("Account Created! You can now Sign In.")
            else:
                st.warning("Fill all fields.")
        st.markdown("</div>", unsafe_allow_html=True)
