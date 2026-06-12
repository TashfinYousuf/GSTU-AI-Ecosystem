import os

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=True)

import time
import logging
import streamlit as st
from supabase import create_client, Client
from dotenv import load_dotenv
import base64

logger = logging.getLogger(__name__)
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

@st.cache_resource
def get_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Supabase credentials missing! Check your .env file.")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase()

def init_auth_session():
    if "authenticated" not in st.session_state: st.session_state.authenticated = False
    if "logged_in" not in st.session_state: st.session_state.logged_in = False
    if "user_email" not in st.session_state: st.session_state.user_email = None
    if "username_id" not in st.session_state: st.session_state.username_id = None
    if "user_name" not in st.session_state: st.session_state.user_name = "User"
    if "user_role" not in st.session_state: st.session_state.user_role = "Student"
    if "auth_mode" not in st.session_state: st.session_state.auth_mode = "login"

def get_oauth_url(provider):
    return f"{SUPABASE_URL}/auth/v1/authorize?provider={provider}&redirect_to=https://gstu-ai-backend.onrender.com/oauth-callback"

def login_user(email, password):
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if response.user:
            st.session_state.logged_in = True
            st.session_state.authenticated = True
            st.session_state.user_email = response.user.email
            st.session_state.username_id = response.user.id
            meta = response.user.user_metadata
            st.session_state.user_name = meta.get("full_name", email.split("@")[0])
            st.session_state.user_role = meta.get("role", "Student")
            st.session_state.just_logged_in = True 
            return True, "Login Successful!"
    except Exception as e:
        # 🔴 Explicit Error Tracking
        error_msg = str(e)
        if "Invalid login credentials" in error_msg:
            error_msg = "Incorrect Email or Password. Please try again."
        elif "Email not confirmed" in error_msg:
            error_msg = "Please verify your email address first."
        return False, f"Login Failed: {error_msg}"
    

def logout_user():
    try:
        supabase.auth.sign_out()
        st.session_state.clear()
        st.rerun()
    except: pass


def render_auth_interface():
    
     # 🔴 Force Initialize auth_mode
    if "auth_mode" not in st.session_state:
        st.session_state.auth_mode = "login"

    # 🔴 1. GET LOGO
    logo_b64 = ""
    for path in ["logo.png", "data/logo.png"]:
        if os.path.exists(path):
            with open(path, "rb") as f: 
                logo_b64 = base64.b64encode(f.read()).decode()
                break
                
    # লোগো সাইজ কম্প্যাক্ট করা হয়েছে (55px)
    logo_html = f"<img src='data:image/png;base64,{logo_b64}' style='width: 55px; height: 55px; border-radius: 50%; margin-bottom: 5px; object-fit: cover; box-shadow: 0 4px 10px rgba(0,0,0,0.3);'>" if logo_b64 else "<span style='font-size: 45px;'>🎓</span>"

    # 🔴 2. GET BACKGROUND IMAGE
    bg_b64 = ""
    for path in ["background_pic.png", "data/background_pic.png"]:
        if os.path.exists(path):
            with open(path, "rb") as f:
                bg_b64 = base64.b64encode(f.read()).decode()
                break
    
    # 🔴 3. DYNAMIC CSS (Compact, Professional Silicon Valley Style)
    if bg_b64:
        bg_css = f"""
        .stApp {{
            background: linear-gradient(rgba(15, 23, 42, 0.88), rgba(15, 23, 42, 0.95)), url('data:image/jpeg;base64,{bg_b64}');
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
            color: white;
        }}
        """
    else:
        bg_css = ".stApp { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: white; }"

    st.markdown(f"""
        <style>
        {bg_css}
        
        /* 🔴 1. COMPACT VIEWPORT & HIDDEN EXTRAS TO PREVENT SCROLLING */
        header {{ visibility: hidden !important; }}
        footer {{ visibility: hidden !important; }}
        .block-container {{
            padding-top: 3vh !important;
            padding-bottom: 0px !important;
            max-width: 100% !important;
        }}
        
        /* 🔴 2. REDUCE STREAMLIT DEFAULT GAPS */
        div[data-testid="stVerticalBlock"] {{ gap: 0.6rem !important; }}
        
        /* 🔴 3. GLASSMORPHISM CONTAINER INJECTED TO COLUMN */
        div[data-testid="column"]:nth-child(2) {{
            background: rgba(15, 23, 42, 0.45);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 25px 35px 30px 35px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.8);
            margin-top: 1vh;
        }}

        /* Premium Social Buttons - Compact */
        .social-btn, .action-btn {{
            display: flex; align-items: center; justify-content: center; width: 100%;
            padding: 10px; margin-bottom: 5px; border-radius: 10px;
            border: 1px solid rgba(255, 255, 255, 0.15); background: rgba(30, 30, 30, 0.5);
            color: #ffffff !important; text-decoration: none !important;
            font-size: 13px; font-weight: 500; transition: all 0.3s ease; cursor: pointer;
        }}
        .social-btn:hover, .action-btn:hover {{ background: #000000 !important; border-color: #10a37f; color: #ffffff !important; transform: translateY(-2px); box-shadow: 0 5px 15px rgba(16, 163, 127, 0.3);}}
        .social-icon {{ width: 18px; height: 18px; margin-right: 10px; }}
        
        .divider {{ display: flex; align-items: center; margin: 15px 0 10px 0; color: #64748b; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;}}
        .divider::before, .divider::after {{ content: ""; flex: 1; border-bottom: 1px solid rgba(255, 255, 255, 0.15); }}
        .divider:not(:empty)::before {{ margin-right: 15px; }}
        .divider:not(:empty)::after {{ margin-left: 15px; }}
        
        /* 🔴 Input Fields - PERFECT Full Width Fix */
        div[data-baseweb="input"], div[data-baseweb="select"] > div {{ 
            background-color: rgba(0, 0, 0, 0.5) !important; 
            border: 1px solid rgba(255, 255, 255, 0.15) !important; 
            border-radius: 8px !important; 
            overflow: hidden !important; /* Keeps everything perfectly inside the border */
            min-height: 42px !important;
        }}

        /* Make inner wrapper transparent so the outer background shines through */
        div[data-baseweb="input"] > div {{
            background-color: transparent !important; 
            border: none !important;
        }}

        /* Make the actual text input transparent */
        div[data-baseweb="input"] input {{
            background-color: transparent !important;
            color: white !important;
            font-size: 14px !important;
            padding-left: 12px !important;
        }}

        /* The glowing focus ring */
        div[data-baseweb="input"]:focus-within {{
            border-color: #10a37f !important; 
            box-shadow: 0 0 0 1px #10a37f !important; 
        }}

        .stButton > button[kind="primary"]:hover {{ background: #000000 !important; transform: translateY(-2px) !important; box-shadow: 0 5px 15px rgba(16, 163, 127, 0.4) !important; }}
        
        /* 🔴 PREMUM LINK-STYLE SECONDARY BUTTON (Sign up toggle) */
        .stButton > button[kind="secondary"] {{
            background: transparent !important; color: #94a3b8 !important; border: none !important; 
            font-size: 12px !important; font-weight: 500 !important; padding: 0 !important; 
            height: auto !important; margin-top: 5px; transition: color 0.3s ease !important;
        }}
        .stButton > button[kind="secondary"]:hover {{ color: #10a37f !important; background: transparent !important; box-shadow: none !important; transform: none !important; }}
        </style>
    """, unsafe_allow_html=True)

    # 🔐 UI Rendering Structure (Centered, Column size adjusted for compactness)
    col1, col2, col3 = st.columns([1, 1.1, 1])
    
    with col2:
        # 🔴 PIN-POINT CENTER ALIGNMENT FIX
        st.markdown(f"""
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%; padding-left: 5px;">
            {logo_html}
            <h2 style='margin-bottom: 2px; margin-top: 0; font-weight: 800; font-size: 24px; color: #ffffff; letter-spacing: -0.5px; text-align: center;'>GSTU AI Ecosystem</h2>
            <p style='color: #94a3b8; font-size: 12px; margin-bottom: 15px; text-align: center;'>Sign in to access elite agentic research tools</p>
        </div>
        """, unsafe_allow_html=True)

        if st.session_state.auth_mode == "login":
            st.markdown(f"""
                <a href="{get_oauth_url('google')}" target="_self" class="social-btn"><img src="https://upload.wikimedia.org/wikipedia/commons/c/c1/Google_%22G%22_logo.svg" class="social-icon"> Continue with Google</a>
                <a href="{get_oauth_url('facebook')}" target="_self" class="social-btn"><img src="https://upload.wikimedia.org/wikipedia/commons/b/b8/2021_Facebook_icon.svg" class="social-icon"> Continue with Facebook</a>
            """, unsafe_allow_html=True)
            
            st.markdown("<div class='divider'>or continue with email</div>", unsafe_allow_html=True)

            login_email = st.text_input("Email", placeholder="name@gstu.edu.bd", label_visibility="collapsed")
            login_password = st.text_input("Password", type="password", placeholder="Password", label_visibility="collapsed")
            
            if st.button("Sign In →", use_container_width=True, type="primary"):
                success, msg = login_user(login_email, login_password)
                if success: st.rerun()
                else: st.error(msg)
                
            if st.button("Don't have an account? Sign up", use_container_width=True, type="secondary"):
                st.session_state.auth_mode = "signup"
                st.rerun()

        else:
            # SIGN UP FORM - Compact Layout
            st.markdown("<h4 style='text-align:center; font-size: 18px; margin-bottom: 10px; margin-top: 0;'>Create Account</h4>", unsafe_allow_html=True)
            new_name = st.text_input("Full Name", placeholder="Full Name", label_visibility="collapsed")
            new_email = st.text_input("Email Address", placeholder="name@gstu.edu.bd", label_visibility="collapsed")
            new_dept = st.selectbox("Department", ["IR", "CSE", "EEE", "BBA", "Law"], label_visibility="collapsed")
            new_pass = st.text_input("Create Password", type="password", placeholder="Password", label_visibility="collapsed")
            
            if st.button("Create Account", use_container_width=True, type="primary"):
                if new_email and new_pass and new_name:
                    try:
                        res = supabase.auth.sign_up({"email": new_email, "password": new_pass, "options": {"data": {"full_name": new_name, "role": "Student", "department": new_dept}}})
                        if res: 
                            st.success("Check email to verify!")
                            st.session_state.auth_mode = "login"
                            st.rerun()
                    except Exception as e: st.error(f"Sign Up Failed: {e}")
                else: st.warning("Please fill all fields.")
                
            if st.button("← Back to Login", use_container_width=True, type="secondary"):
                st.session_state.auth_mode = "login"
                st.rerun()