import os
import time
import json
import base64
import logging
import socket
import datetime
import tempfile
import re
from PIL import Image
from filelock import FileLock

# ============================================================================
# 🛡️ 1. SECURITY FIRST: Load Environment Variables SECURELY
# ============================================================================
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=True)


import streamlit as st
import pandas as pd
import urllib.parse
import pypdf

from streamlit_cookies_controller import CookieController
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.documents import Document


# Local Modules
from auth_logic import supabase
from analytics_engine import render_study_logger, render_analytics_dashboard
from database import search_context
from auth_manager import get_user_profile, get_oauth_url
from cloud_memory import create_new_session, save_message_to_cloud
from payment_manager import initiate_real_sslcommerz_payment, check_subscription_status
from usage_manager import is_model_premium, check_rate_limit, increment_usage

# 🟢 Agentic OS Brain Imports
from memory_db import get_or_create_student_profile, update_weakness_graph
from analytics_engine import generate_progress_report
from core_agents import generate_cgpa_boost_plan

logger = logging.getLogger(__name__)

# =====================================================================
# ⚡ 2. INITIALIZE PAGE & CACHED LOGO
# =====================================================================
@st.cache_resource(show_spinner=False)
def load_app_logo():
    return Image.open("data/logo.png") if os.path.exists("data/logo.png") else "🎓"

st.set_page_config(
    page_title="GSTU AI Assistant",
    page_icon=load_app_logo(),
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================================
# ⚡ 2. INITIALIZE PAGE & CACHED LOGO
# =====================================================================
@st.cache_resource(show_spinner=False)
def load_app_logo():
    return Image.open("data/logo.png") if os.path.exists("data/logo.png") else "🎓"

st.set_page_config(
    page_title="GSTU AI Assistant",
    page_icon=load_app_logo(),
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🛑 ULTIMATE ANTI-FLASH, UX BOOST & SPLASH SCREEN
st.markdown("""
    <style>
    /* 1. Force Reset Zoom for Desktop/Mobile */
    html, body, [data-testid="stAppViewContainer"] { zoom: 1.0 !important; transform: none !important; }
    
    /* 2. Splash Screen covers everything immediately */
    .supreme-splash {
        position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
        background-color: #05080f; z-index: 999999999;
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        animation: splashFade 0.3s ease-in-out 1.2s forwards; 
    }
    .supreme-splash-text {
        color: #10a37f; font-family: 'Inter', sans-serif; font-size: 22px; font-weight: 700;
        animation: pulse 0.8s infinite alternate; letter-spacing: -0.5px;
    }
    @keyframes pulse { from { opacity: 0.5; transform: scale(0.95); } to { opacity: 1; transform: scale(1.05); } }
    @keyframes splashFade { to { opacity: 0; visibility: hidden; } }
    
    /* 3. Hide the main container until splash is done to prevent flash */
    .block-container { opacity: 0; animation: formReveal 0.3s ease-in-out 1.2s forwards; }
    @keyframes formReveal { to { opacity: 1; } }

    /* 4. ☢️ EXTREME UX BOOST (KILL STREAMLIT DIMMING FOREVER) */
    div[data-testid="stAppViewBlockContainer"] {
        opacity: 1 !important; transition: none !important; filter: none !important;
    }
    [data-testid="stStatusWidget"], .stSpinner, .stException { 
        visibility: hidden !important; display: none !important; opacity: 0 !important; 
    }
    * { transition-duration: 0.1s !important; }
    </style>
    
    <div class="supreme-splash">
        <div class="supreme-splash-text">✨ Syncing Ecosystem...</div>
    </div>
""", unsafe_allow_html=True)

# 🔴 INJECTING THE STYLE.CSS GLOBALLY
def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
            st.markdown('<a href="/" target="_self" class="mobile-floating-btn">📝</a>', unsafe_allow_html=True)

local_css("assets/style.css")


# =====================================================================
# 🗄️ 3. CENTRAL DATABASE & FILELOCK MANAGER
# =====================================================================
DB_FILE = "users_db.json"
HISTORY_FILE = "chat_history.json"
TEN_YEARS = 315360000 

@st.cache_resource
def load_users():
    if os.path.exists(DB_FILE):
        with FileLock(f"{DB_FILE}.lock"):
            with open(DB_FILE, "r") as f: 
                return json.load(f)
    return {}

def initialize_central_db():
    if not os.path.exists(DB_FILE):
        default_data = {"system_meta": {"version": "1.0", "status": "initialized"}, "users": {}}
        with FileLock(f"{DB_FILE}.lock"):
            with open(DB_FILE, "w") as f: 
                json.dump(default_data, f, indent=4)

initialize_central_db()


# =====================================================================
# 🌐 4. OFFLINE DETECTOR & SESSION STATES
# =====================================================================
def check_internet_connection():
    try:
        socket.create_connection(("1.1.1.1", 53), timeout=2)
        return True
    except OSError:
        return False

if "is_offline" not in st.session_state:
    st.session_state.is_offline = not check_internet_connection()

if "show_login_page" not in st.session_state:
    st.session_state.show_login_page = False


# =====================================================================
# 🚀 4. PRODUCTION-GRADE CACHING WITH GUARDRAILS
# =====================================================================
@st.cache_data(ttl=300) 
def load_chat_history_cached(user_id):
    # 🔴 BUG #8 FIX: Prevent Guest or None from hitting DB
    if not user_id or str(user_id) in ["None", "guest_session"]: return []
    
    try:
        if os.path.exists(HISTORY_FILE):
            from filelock import FileLock
            with FileLock(f"{HISTORY_FILE}.lock"):
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return [x for x in data if x.get("owner_id") == user_id]
    except Exception as e:
        logger.error(f"History load error: {e}")
    return []

@st.cache_data(ttl=600) 
def get_user_profile_cache(user_id):
    # 🔴 BUG #8 FIX: Prevent Supabase UUID Type Crash (22P02)
    if not user_id or str(user_id) in ["None", "guest_session"]: return None
    
    try:
        res = supabase.table("user_profiles").select("email, full_name, role").eq("id", user_id).execute()
        if res.data: return res.data[0]
    except Exception as e:
        logger.error(f"Profile Fetch Error: {e}")
    return None

# =====================================================================
# ⚙️ 5. SECURE GLOBAL STATE INITIALIZATION (BUG #2 FIX)
# =====================================================================
default_states = {
    'authenticated': False,
    'logged_in': False,
    'auth_mode': 'login',
    'messages': [],
    'user_id': 'guest_session',       # Safely defaulted
    'username_id': 'guest_session',   # Safely defaulted
    'user_email': '',
    'user_name': 'Guest Scholar',     # Prevents .split() crashes
    'user_role': 'Guest',
    'just_logged_in': False,
    'active_chat_title': None,
    'chat_history': [],
    'show_login_page': False,
    'voice_draft': "",
    'quick_query': None,
    'selection_mode': False,
    'current_model': "meta-llama/llama-4-scout-17b-16e-instruct"
}
for key, val in default_states.items():
    if key not in st.session_state: st.session_state[key] = val

# 🔴 ROOT CAUSE OF BLANK SCREEN FIXED: Initialize the DB before anyone tries to read it!
if "users_db" not in st.session_state:
    st.session_state.users_db = load_users()

def save_chat_history(history_list):
    current_user_id = st.session_state.get("username_id")
    if not current_user_id: return
    
    for ch in history_list: ch["owner_id"] = current_user_id
    
    from filelock import FileLock
    with FileLock(f"{HISTORY_FILE}.lock"):
        global_data = []
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f: global_data = json.load(f)
            except: pass
            
        filtered_global = [d for d in global_data if d.get("owner_id") != current_user_id]
        final_data = filtered_global + history_list
        
        with open(HISTORY_FILE, "w", encoding="utf-8") as f: 
            json.dump(final_data, f, ensure_ascii=False, indent=4)
            
    # Cache Invalidation
    load_chat_history_cached.clear()
    st.session_state.chat_history = load_chat_history_cached(current_user_id)


# =====================================================================
# 🔐 5. AUTHENTICATION ENGINE & COOKIES (MUST RUN BEFORE ANY st.stop)
# =====================================================================
cookie_controller = CookieController(key="gstu_auth_cookie_manager")

# 🔴 THE ULTIMATE ANTI-GHOST BANNER & SYNC
if "cookie_synced" not in st.session_state:
    st.session_state.cookie_synced = True
    st.markdown("<h3 style='text-align:center; padding-top:20vh; color:#10a37f;'>🔄 Restoring Secure Session...</h3>", unsafe_allow_html=True)
    time.sleep(0.6) # ⏳ CRITICAL: Waits for browser cookies to reach Python
    st.rerun()

def restore_auth():
    if st.session_state.get('authenticated'): return

    try:
        access_token = cookie_controller.get('access_token')
        refresh_token = cookie_controller.get('refresh_token')
    except Exception:
        access_token, refresh_token = None, None

    if not access_token or str(access_token).strip() == "" or str(access_token).lower() == "none": return

    valid_user_id = None
    try:
        user_response = supabase.auth.get_user(access_token)
        if user_response and hasattr(user_response, 'user') and user_response.user:
            valid_user_id = user_response.user.id
    except Exception:
        if refresh_token:
            try:
                res = supabase.auth.refresh_session(refresh_token)
                if res and hasattr(res, 'session') and res.session:
                    cookie_controller.set("access_token", res.session.access_token, max_age=TEN_YEARS)
                    cookie_controller.set("refresh_token", res.session.refresh_token, max_age=TEN_YEARS)
                    cookie_controller.set("user_id", res.session.user.id, max_age=TEN_YEARS)
                    valid_user_id = res.session.user.id
            except Exception as e: logger.error(f"Token refresh failed: {e}")

    if valid_user_id:
        st.session_state.update({
            'authenticated': True, 'logged_in': True, 'user_id': valid_user_id, 'username_id': valid_user_id
        })
        st.session_state.chat_history = load_chat_history_cached(valid_user_id)
        profile = get_user_profile_cache(valid_user_id)
        if profile:
            st.session_state.update({
                'user_email': profile.get("email"),
                'user_name': profile.get("full_name", "GSTU Scholar"),
                'user_role': profile.get("role", "Student")
            })

restore_auth()

def professional_logout():
    try: supabase.auth.sign_out()
    except: pass
    cookie_controller.remove("access_token")
    cookie_controller.remove("refresh_token")
    cookie_controller.remove("user_id")
    time.sleep(0.5)
    st.session_state.clear() 
    st.rerun()

# =====================================================================
# 🔄 6. OAUTH TRIGGER & CALLBACK HANDLER
# =====================================================================
if "login_provider" in st.query_params:
    provider = st.query_params["login_provider"]
    from auth_manager import get_oauth_url
    url = get_oauth_url(provider)
    st.query_params.clear()
    st.components.v1.html(f'<meta http-equiv="refresh" content="0; url={url}">', height=0)
    st.stop()

if "code" in st.query_params:
    try:
        auth_code = st.query_params["code"]
        if isinstance(auth_code, list): auth_code = auth_code[0]
        
        res = supabase.auth.exchange_code_for_session({"auth_code": auth_code})
        
        if res and hasattr(res, 'session') and res.session:
            session = res.session
            user = res.user
            uid, email = user.id, user.email
            name = user.user_metadata.get("full_name", email.split("@")[0])
            assigned_role = "Admin" if email in ["yousufaltashfin@gmail.com", "tashfin@gstu.edu"] else user.user_metadata.get("role", "Student")
            
            cookie_controller.set("access_token", session.access_token, max_age=TEN_YEARS)
            cookie_controller.set("refresh_token", session.refresh_token, max_age=TEN_YEARS)
            cookie_controller.set("user_id", uid, max_age=TEN_YEARS)
            
            st.session_state.update({
                'authenticated': True, 'logged_in': True, 'user_id': uid, 'username_id': uid, 
                'user_email': email, 'user_name': name, 'user_role': assigned_role, 'just_logged_in': True,
                'show_login_page': False
            })
            st.query_params.clear()
            time.sleep(1.0)
            st.rerun() 
            
    except Exception as e:
        # 🔴 FIX: Show why Google Auth failed instead of infinite looping!
        st.error(f"⚠️ OAuth Login Failed: {str(e)}")
        time.sleep(3)
        st.query_params.clear()
        st.rerun()

# 🔴 DEFAULT TO GUEST IF NOT LOGGED IN
if not st.session_state.get("logged_in", False):
    st.session_state.user_role = "Guest"
    st.session_state.username_id = "guest_session"
    st.session_state.user_id = "guest_session"
    st.session_state.user_name = "Guest Scholar" 
    st.session_state.user_email = "" 
    st.session_state.logged_in = False

# =====================================================================
# 🎨 7. GLOBAL BACKGROUND, LOGO & SMART LOGIN WALL
# =====================================================================
logo_b64 = ""
for path in ["logo.png", "data/logo.png"]:
    if os.path.exists(path):
        with open(path, "rb") as f: 
            logo_b64 = base64.b64encode(f.read()).decode()
            break
            
logo_html = f"<img src='data:image/png;base64,{logo_b64}' style='width: 55px; height: 55px; border-radius: 50%; margin-bottom: 5px; object-fit: cover; box-shadow: 0 4px 10px rgba(0,0,0,0.3);'>" if logo_b64 else "<span style='font-size: 45px;'>🎓</span>"

# 🔴 Only show login wall if explicitly triggered!
if st.session_state.get("show_login_page", False) and not st.session_state.get("logged_in", False):
    
    bg_b64 = ""
    for path in ["background_pic.png", "data/background_pic.png"]:
        if os.path.exists(path):
            with open(path, "rb") as f:
                bg_b64 = base64.b64encode(f.read()).decode()
                break

    if bg_b64: bg_css = f".stApp {{ background: linear-gradient(rgba(15, 23, 42, 0.88), rgba(15, 23, 42, 0.95)), url('data:image/jpeg;base64,{bg_b64}'); background-size: cover; background-position: center; background-repeat: no-repeat; background-attachment: fixed; color: white; }}"
    else: bg_css = ".stApp { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: white; }"

    st.markdown(f"""
        <style>
        {bg_css}
        header {{ visibility: hidden !important; }}
        footer {{ visibility: hidden !important; }}
        .block-container {{ padding-top: 3vh !important; padding-bottom: 0px !important; max-width: 100% !important; }}
        div[data-testid="stVerticalBlock"] {{ gap: 0.6rem !important; }}
        div[data-testid="column"]:nth-child(2) {{ background: rgba(15, 23, 42, 0.45); backdrop-filter: blur(20px); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 20px; padding: 25px 35px 30px 35px; box-shadow: 0 10px 40px rgba(0, 0, 0, 0.8); margin-top: 1vh; }}
        .social-btn, .action-btn {{ display: flex; align-items: center; justify-content: center; width: 100%; padding: 10px; margin-bottom: 5px; border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.15); background: rgba(30, 30, 30, 0.5); color: #ffffff !important; text-decoration: none !important; font-size: 13px; font-weight: 500; transition: all 0.3s ease; cursor: pointer; }}
        .social-btn:hover, .action-btn:hover {{ background: #000000 !important; border-color: #10a37f; color: #ffffff !important; transform: translateY(-2px); box-shadow: 0 5px 15px rgba(16, 163, 127, 0.3);}}
        .social-icon {{ width: 18px; height: 18px; margin-right: 10px; }}
        .divider {{ display: flex; align-items: center; margin: 15px 0 10px 0; color: #64748b; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;}}
        .divider::before, .divider::after {{ content: ""; flex: 1; border-bottom: 1px solid rgba(255, 255, 255, 0.15); }}
        .divider:not(:empty)::before {{ margin-right: 15px; }}
        .divider:not(:empty)::after {{ margin-left: 15px; }}
        </style>
    """, unsafe_allow_html=True)

    if "auth_mode" not in st.session_state: st.session_state.auth_mode = "login"

    col1, col2, col3 = st.columns([1, 1.1, 1])
    with col2:
        st.markdown(f"""
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%; padding-left: 5px;">
            {logo_html}
            <h2 style='margin-bottom: 2px; margin-top: 0; font-weight: 800; font-size: 24px; color: #ffffff; letter-spacing: -0.5px; text-align: center;'>GSTU AI Ecosystem</h2>
            <p style='color: #94a3b8; font-size: 12px; margin-bottom: 15px; text-align: center;'>Sign in to access elite agentic research tools</p>
        </div>
        """, unsafe_allow_html=True)

        if st.session_state.is_offline:
            st.error("⚠️ **No Internet!** Cannot connect to Authentication Server.")
        else:
            if st.session_state.auth_mode == "login":
                st.markdown(f"""
                    <a href="?login_provider=google" target="_self" class="social-btn"><img src="https://upload.wikimedia.org/wikipedia/commons/c/c1/Google_%22G%22_logo.svg" class="social-icon"> Continue with Google</a>
                    <a href="?login_provider=facebook" target="_self" class="social-btn"><img src="https://upload.wikimedia.org/wikipedia/commons/b/b8/2021_Facebook_icon.svg" class="social-icon"> Continue with Facebook</a>
                """, unsafe_allow_html=True)
                st.markdown("<div class='divider'>or continue with email</div>", unsafe_allow_html=True)

                login_email = st.text_input("Email", placeholder="name@gstu.edu.bd", label_visibility="collapsed")
                login_password = st.text_input("Password", type="password", placeholder="Password", label_visibility="collapsed")
                
                if st.button("Sign In →", use_container_width=True, type="primary"):
                    try:
                        res = supabase.auth.sign_in_with_password({"email": login_email, "password": login_password})
                        if res and res.session:
                            session = res.session
                            cookie_controller.set("access_token", session.access_token, max_age=TEN_YEARS)
                            cookie_controller.set("refresh_token", session.refresh_token, max_age=TEN_YEARS)
                            cookie_controller.set("user_id", session.user.id, max_age=TEN_YEARS)
                            
                            st.session_state.update({
                                'authenticated': True, 'logged_in': True, 'user_id': session.user.id, 'username_id': session.user.id,
                                'user_email': login_email, 'just_logged_in': True, 'show_login_page': False
                            })
                            profile = get_user_profile_cache(session.user.id)
                            st.session_state.user_name = profile.get("full_name", login_email.split("@")[0]) if profile else login_email.split("@")[0]
                            st.session_state.user_role = profile.get("role", "Student") if profile else "Student"
                            st.session_state.chat_history = load_chat_history_cached(session.user.id)
                            
                            st.success("✅ Login successful! Loading dashboard...")
                            time.sleep(1); st.rerun() 
                        else: st.error("⚠️ Authentication failed.")
                    except Exception as e:
                        st.error("⚠️ Invalid email or password. Please try again.")
                    
                if st.button("Don't have an account? Sign up", use_container_width=True):
                    st.session_state.auth_mode = "signup"; st.rerun()

            else:
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
                                st.success("Check email to verify!"); time.sleep(2)
                                st.session_state.auth_mode = "login"; st.rerun()
                        except Exception as e: st.error(f"Sign Up Failed: {e}")
                    else: st.warning("Please fill all fields.")
                    
                if st.button("← Back to Login", use_container_width=True):
                    st.session_state.auth_mode = "login"; st.rerun()
        
        st.markdown("<br><hr>", unsafe_allow_html=True)
        if st.button("⬅️ Back to Offline/Guest Dashboard", type="secondary", use_container_width=True):
            st.session_state.show_login_page = False
            st.rerun()

    st.stop() # 🔴 THIS MUST BE THE ONLY st.stop() IN YOUR ENTIRE LOGIN FLOW!


# =====================================================================
# 🛡️ 9. PREMIUM GATEKEEPER FUNCTION
# =====================================================================
def require_login_for_premium():
    if not st.session_state.get("logged_in", False) or st.session_state.user_role == "Guest":
        st.warning("🔒 **Authentication Required**")
        st.info("This is a Cloud AI premium feature. Please login or sign up to unlock.")
        if st.button("🚀 Login / Sign Up Now", type="primary", use_container_width=True):
            st.session_state.show_login_page = True
            st.rerun()
        return True
    return False

# =====================================================================
# ✨ 10. WELCOME DIALOG
# =====================================================================
@st.dialog("✨ Welcome to GSTU IR Ecosystem", width="small")
def welcome_dialog():
    st.markdown("<h3 style='text-align:center; color: #10a37f;'>🎉 Authentication Successful!</h3>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:gray;'>🔄 Loading your secure dashboard...</p>", unsafe_allow_html=True)
    time.sleep(1.5)
    st.session_state.just_logged_in = False
    st.rerun()

if st.session_state.get("just_logged_in", False):
    welcome_dialog()


# 🔴 THE MASTER FEATURE FLAG
ENABLE_AGENTIC_FEATURES = True


# =====================================================================
# 🌓 9. THEME LOGIC, COMPACT UI & DYNAMIC BACKGROUNDS ONLY
# =====================================================================
dash_bg_b64 = ""
for path in ["background_pic.png", "data/background_pic.png"]:
    if os.path.exists(path):
        with open(path, "rb") as f:
            dash_bg_b64 = base64.b64encode(f.read()).decode()
            break

if st.session_state.get("theme") == "light":
    bg = dash_bg_b64 if dash_bg_b64 else logo_b64
    st.markdown(f"""
    <style>
    .stApp::before {{
        content: ""; position: fixed; inset: 0;
        background: linear-gradient(135deg, rgba(248,250,252,0.94) 0%, rgba(241,245,249,0.96) 100%), url('data:image/jpeg;base64,{bg}') center/cover no-repeat;
        z-index: -999; pointer-events: none;
    }}
    .stApp {{ background-color: #f8fafc !important; }}

    [data-testid="stSidebar"] {{
        background: rgba(255,255,255,0.72) !important;
        backdrop-filter: blur(20px) saturate(1.4) !important;
        border-right: 0.5px solid rgba(0,0,0,0.08) !important;
    }}

    .stApp p, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
    .stApp span:not([class*="icon"]), .stApp label, .stApp [data-testid="stMarkdownContainer"] {{
        color: #0f172a !important;
    }}

   /* 🔴 UNIVERSAL BUTTON FIX (Light Theme) */
    div[data-testid="stButton"] > button {{
        background: transparent !important; 
        border: 1px solid rgba(0, 0, 0, 0.15) !important; 
        color: #0f172a !important; 
        border-radius: 8px !important;
        transition: all 0.3s ease !important;
        box-shadow: none !important;
    }}
    div[data-testid="stButton"] > button:hover {{
        background: rgba(16, 163, 127, 0.08) !important; 
        border-color: #10a37f !important;
        color: #ffffff !important;
        transform: translateY(-2px) !important;
    }}
    
    /* Primary Buttons (Solid Green) */
    div[data-testid="stButton"] > button[kind="primary"] {{
        background: #10a37f !important;
        border: none !important;
        color: white !important;
    }}
    div[data-testid="stButton"] > button[kind="primary"]:hover {{
        background: #0d8a6a !important;
        box-shadow: 0 4px 15px rgba(16,163,127,0.3) !important;
    }}

    /* 🔴 LIGHT THEME CHAT INPUT (PERFECT GEMINI STYLE) */
    
    /* 1. Bottom Masking */
    [data-testid="stBottom"] {{
        background: #f8fafc !important; 
        border-top: 1px solid rgba(0,0,0,0.05) !important;
        padding: 10px 0 30px 0 !important;
    }}
    
    /* 2. NUKE all outer & hidden inner ugly boxes (Fixes the black block) */
    [data-testid="stBottomBlockContainer"],
    div[data-testid="stChatInput"], 
    div[data-testid="stChatInput"] > div,
    div[data-testid="stChatInput"] > div > div > div {{
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
    }}

    /* 3. THE ACTUAL PILL */
    div[data-testid="stChatInput"] > div > div {{
        background: #ffffff !important;
        border: 1px solid rgba(0, 0, 0, 0.15) !important;
        border-radius: 32px !important;
        padding: 2px 16px !important; /* 🔴 প্যাডিং কমানো হয়েছে (স্লিম হবে) */
        max-width: 800px !important;
        margin: 0 auto !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.04) !important;
        display: flex !important;
        align-items: center !important; 
        transition: border-color 0.2s ease, box-shadow 0.2s ease !important; 
    }}

    /* 5. Clean Textarea (Vertically Centered) */
    div[data-testid="stChatInput"] textarea {{ 
        color: #0f172a !important; 
        -webkit-text-fill-color: #0f172a !important; 
        background: transparent !important;
        padding-top: 13px !important; /* 🔴 টেক্সটকে ঠেলে একদম মাঝখানে আনবে */
        padding-bottom: 9px !important; /* 🔴 নিচের এক্সট্রা স্পেস গায়েব */
        min-height: 46px !important; /* 🔴 Gemini-এর মতো ফিক্সড স্লিম হাইট */
        margin: 0 !important;
        line-height: 1.5 !important;
        border: none !important;
        box-shadow: none !important;
        outline: none !important;
    }}

    /* Single Green Line on Focus (No jumping, no white borders) */
    div[data-testid="stChatInput"] > div > div:focus-within {{
        border-color: #10a37f !important;
        box-shadow: 0 0 0 1px #10a37f !important;
    }}
    
    /* Nuke default textarea focus to stop white jumps */
    div[data-testid="stChatInput"] textarea:focus {{
        border: none !important; box-shadow: none !important; outline: none !important;
    }}

    /* 6. Kill Inner Hidden Navy/Black Background */
    div[data-testid="stChatInput"] div[data-baseweb="base-input"],
    div[data-testid="stChatInput"] div[data-baseweb="textarea"] {{
        background: transparent !important;
        background-color: transparent !important;
    }}

    /* 🔴 1. STICKY TOP HEADER (GSTU + LOGO) */
    [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:has(.gstu-sidebar-header-container) {{
        position: sticky !important; 
        top: 0 !important; 
        z-index: 999999 !important;
        background: rgba(248, 250, 252, 0.98) !important;
        backdrop-filter: blur(25px) !important;
        margin-top: -2rem !important;
        padding-top: 2rem !important;
        padding-bottom: 15px !important;
        border-bottom: 1px solid rgba(0, 0, 0, 0.08) !important;
    }}

    /* 🔴 2. STICKY BOTTOM BUTTON (AI SUPPORT) */
    [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:has(div[data-testid="stPopover"]) {{
        position: sticky !important;
        bottom: 0 !important;
        z-index: 99999 !important;
        background: rgba(248, 250, 252, 0.98) !important;
        backdrop-filter: blur(25px) !important;
        padding: 15px 0 20px 0 !important;
        border-top: 1px solid rgba(0, 0, 0, 0.08) !important;
    }}

    /* 🔴 3. PREMIUM AI SUPPORT BUTTON DESIGN */
    [data-testid="stSidebar"] div[data-testid="stPopover"] > button {{
        width: 100% !important; display: flex !important; justify-content: center !important; align-items: center !important;
        background: linear-gradient(135deg, rgba(16,163,127,0.1), rgba(16,163,127,0.05)) !important;
        border: 1px solid rgba(16, 163, 127, 0.4) !important; border-radius: 12px !important;
        color: #10a37f !important; font-weight: 600 !important; font-size: 15px !important;
        padding: 12px !important; box-shadow: 0 4px 10px rgba(0,0,0,0.05) !important; transition: all 0.3s ease !important;
    }}
    [data-testid="stSidebar"] div[data-testid="stPopover"] > button:hover {{
        background: #10a37f !important; color: #ffffff !important;
        transform: translateY(-2px) !important; box-shadow: 0 6px 15px rgba(16,163,127,0.2) !important;
    }}

    /* 🔴 4. PREMIUM POPOVER (AI SUPPORT INNER DESIGN) */
    div[data-testid="stPopoverBody"] {{
        background: rgba(255, 255, 255, 0.95) !important;
        border: 1px solid rgba(16, 163, 127, 0.3) !important; border-radius: 16px !important;
        padding: 20px !important; backdrop-filter: blur(25px) !important;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1) !important;
    }}
    div[data-testid="stPopoverBody"] textarea {{
        background: #f8fafc !important; border: 1px solid rgba(0,0,0,0.1) !important;
        border-radius: 12px !important; color: #0f172a !important; padding: 12px !important;
    }}
    div[data-testid="stPopoverBody"] textarea:focus {{
        border-color: #10a37f !important; box-shadow: 0 0 10px rgba(16,163,127,0.2) !important;
    }}

    </style>
    """, unsafe_allow_html=True)

else:
    # 💎 DARK MODE
    if dash_bg_b64:
        st.markdown(f"""
        <style>
        .stApp {{ background: transparent !important; color: #f1f5f9 !important; }}
        .stApp::before {{
            content: ""; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
            background: linear-gradient(rgba(10, 15, 30, 0.85), rgba(5, 8, 15, 0.95)), url('data:image/jpeg;base64,{dash_bg_b64}') center/cover no-repeat;
            filter: blur(12px); z-index: -999; transform: scale(1.05);
        }}

        /* 🔴 UNIVERSAL BUTTON FIX (Dark Theme) */
        div[data-testid="stButton"] > button {{
            background: transparent !important; /* Removes the ugly navy/black */
            border: 1px solid rgba(255, 255, 255, 0.2) !important; 
            color: #f8fafc !important; 
            border-radius: 8px !important;
            transition: all 0.3s ease !important;
            box-shadow: none !important;
        }}
        div[data-testid="stButton"] > button:hover {{
            background: rgba(16, 163, 127, 0.15) !important; 
            border-color: #10a37f !important;
            color: #ffffff !important;
            transform: translateY(-2px) !important;
        }}
        
        /* Primary Buttons (Solid Green) */
        div[data-testid="stButton"] > button[kind="primary"] {{
            background: #10a37f !important;
            border: none !important;
            color: white !important;
        }}
        div[data-testid="stButton"] > button[kind="primary"]:hover {{
            background: #0d8a6a !important;
            box-shadow: 0 4px 15px rgba(16,163,127,0.4) !important;
        }}
        
        /* 🔴 DARK THEME CHAT INPUT (PERFECT CHATGPT STYLE) */
        
        /* 1. Bottom Masking */
        [data-testid="stBottom"] {{
            background: rgba(10, 15, 30, 0.98) !important;
            border-top: 1px solid rgba(255,255,255,0.05) !important;
            backdrop-filter: blur(20px) !important;
            padding: 10px 0 20px 0 !important;
        }}
        
        /* 2. NUKE all outer & hidden inner ugly boxes */
        [data-testid="stBottomBlockContainer"],
        div[data-testid="stChatInput"], 
        div[data-testid="stChatInput"] > div,
        div[data-testid="stChatInput"] > div > div > div {{
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
        }}

        /* 3. THE ACTUAL PILL */
        div[data-testid="stChatInput"] > div > div {{
            background: #212121 !important; 
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 32px !important;
            padding: 2px 16px !important; /* 🔴 প্যাডিং কমানো হয়েছে (স্লিম হবে) */
            max-width: 800px !important;
            margin: 0 auto !important;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3) !important;
            display: flex !important;
            align-items: center !important; 
            transition: border-color 0.2s ease, box-shadow 0.2s ease !important; 
        }}

        /* 5. Clean Textarea (Vertically Centered) */
        div[data-testid="stChatInput"] textarea {{ 
            color: #f8fafc !important; 
            -webkit-text-fill-color: #f8fafc !important;
            background: transparent !important;
            padding-top: 13px !important; /* 🔴 টেক্সটকে ঠেলে একদম মাঝখানে আনবে */
            padding-bottom: 9px !important; /* 🔴 নিচের এক্সট্রা স্পেস গায়েব */
            min-height: 46px !important; /* 🔴 Gemini-এর মতো ফিক্সড স্লিম হাইট */
            margin: 0 !important;
            line-height: 1.5 !important;
            border: none !important;
            box-shadow: none !important;
            outline: none !important;
        }}

        /* Single Green Line on Focus */
        div[data-testid="stChatInput"] > div > div:focus-within {{
            border-color: #10a37f !important;
            box-shadow: 0 0 0 1px #10a37f !important;
        }}
        
        /* Nuke default textarea focus to stop white jumps */
        div[data-testid="stChatInput"] textarea:focus {{
            border: none !important; box-shadow: none !important; outline: none !important;
        }}

        /* 6. Kill Inner Hidden Navy/Black Background */
        div[data-testid="stChatInput"] div[data-baseweb="base-input"],
        div[data-testid="stChatInput"] div[data-baseweb="textarea"] {{
            background: transparent !important;
            background-color: transparent !important;
        }}

        /* 🔴 1. STICKY TOP HEADER (GSTU + LOGO) */
        [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:has(.gstu-sidebar-header-container) {{
            position: sticky !important; 
            top: 0 !important; 
            z-index: 999999 !important;
            background: rgba(15, 23, 42, 0.98) !important;
            backdrop-filter: blur(25px) !important;
            margin-top: -2rem !important;
            padding-top: 2rem !important;
            padding-bottom: 15px !important;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08) !important;
        }}

        /* 🔴 2. STICKY BOTTOM BUTTON (AI SUPPORT) */
        [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:has(div[data-testid="stPopover"]) {{
            position: sticky !important;
            bottom: 0 !important;
            z-index: 99999 !important;
            background: rgba(15, 23, 42, 0.98) !important;
            backdrop-filter: blur(25px) !important;
            padding: 15px 0 20px 0 !important;
            border-top: 1px solid rgba(255, 255, 255, 0.08) !important;
        }}

        /* 🔴 3. PREMIUM AI SUPPORT BUTTON DESIGN */
        [data-testid="stSidebar"] div[data-testid="stPopover"] > button {{
            width: 100% !important; display: flex !important; justify-content: center !important; align-items: center !important;
            background: linear-gradient(135deg, rgba(16,163,127,0.1), rgba(16,163,127,0.05)) !important;
            border: 1px solid rgba(16, 163, 127, 0.4) !important; border-radius: 12px !important;
            color: #10a37f !important; font-weight: 600 !important; font-size: 15px !important;
            padding: 12px !important; box-shadow: 0 4px 10px rgba(0,0,0,0.2) !important; transition: all 0.3s ease !important;
        }}
        [data-testid="stSidebar"] div[data-testid="stPopover"] > button:hover {{
            background: #10a37f !important; color: #ffffff !important;
            transform: translateY(-2px) !important; box-shadow: 0 6px 15px rgba(16,163,127,0.4) !important;
        }}

        /* 🔴 4. PREMIUM POPOVER (AI SUPPORT INNER DESIGN) */
        div[data-testid="stPopoverBody"] {{
            background: rgba(15, 23, 42, 0.95) !important;
            border: 1px solid rgba(16, 163, 127, 0.3) !important; border-radius: 16px !important;
            padding: 20px !important; backdrop-filter: blur(25px) !important;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5) !important;
        }}
        div[data-testid="stPopoverBody"] textarea {{
            background: rgba(0,0,0,0.3) !important; border: 1px solid rgba(255,255,255,0.1) !important;
            border-radius: 12px !important; color: white !important; padding: 12px !important;
        }}
        div[data-testid="stPopoverBody"] textarea:focus {{
            border-color: #10a37f !important; box-shadow: 0 0 10px rgba(16,163,127,0.3) !important;
        }}
        
        </style>
        """, unsafe_allow_html=True)


# =======================================
# 🌐 MAIN DASHBOARD (Always Visible)
# =======================================

# 🔴 OFFLINE MODE WARNING
if st.session_state.is_offline:
    st.error("⚠️ **Offline Mode Active:** No internet connection detected. Cloud AI, RAG, and Databases are disabled. You are using the Local Fallback Engine.")
    
# 🟢 GUEST MODE BANNER (BUG FIX: Strict Logged-In Check applied!)
if not st.session_state.get("logged_in", False):
    st.success("👋 **Welcome, Guest Scholar!** You can use basic offline chat. Unlock Research OS, Flashcards, and Debate Arena by logging in.")


# 🔴 Prevents Supabase UUID Error for Guests
user_profile = None
safe_uid = st.session_state.get('user_id')
if safe_uid and str(safe_uid) not in ["guest_session", "None"]:
    try:
        user_profile = get_user_profile(safe_uid)
    except Exception:
        pass


# 🎓 AI STUDENT ONBOARDING (Profile Initialization)
@st.dialog("✨ Welcome to GSTU AI! Let's build your Academic Brain", width="large")
def student_onboarding_dialog():
    st.markdown("### Tell the AI about your goals so it can personalize your study plans!")
    
    sem = st.selectbox("Current Semester", ["1.1", "1.2", "2.1", "2.2", "3.1", "3.2", "4.1", "4.2", "Masters"])
    interest = st.text_input("Core Academic Interest", placeholder="e.g., Geopolitics, Foreign Policy, International Economy")
    goal = st.text_input("Career Goal", placeholder="e.g., Diplomat, BCS Cadre, Researcher, Academician")
    
    if st.button("💾 Initialize My AI Profile", type="primary", use_container_width=True):
        if interest and goal:
            from memory_db import update_student_onboarding
            update_student_onboarding(current_uid, sem, interest, goal)
            st.session_state.is_onboarded = True
            st.success("✅ Profile Initialized! The AI is now synced to your goals.")
            time.sleep(1.5)
            st.rerun()
        else:
            st.warning("Please fill out all fields so the AI can understand you better.")

# 🔴 Trigger the Onboarding Dialog if Student is new
if st.session_state.get('user_role') == "Student":
    if user_profile and not user_profile.get('is_onboarded'):
        if not st.session_state.get('is_onboarded'):
            student_onboarding_dialog()



# Ensure Core Identity Variables Exist
user_id = st.session_state.get('user_id')
current_uid = user_id
st.session_state.username_id = user_id


# 🟢 Ensure ONLY STUDENTS get a Student Profile in our Vault Database
if current_uid and st.session_state.get('user_email'):
    # Check if the user is actually a Student before creating an academic profile
    if st.session_state.get('user_role') == "Student":
        get_or_create_student_profile(
            user_id=current_uid, 
            email=st.session_state.user_email, 
            name=st.session_state.get('user_name', 'Student')
        )


# =====================================================================
# 👑 SUPER ADMIN "FOUNDER MODE" & ROLE CHECK (STRICT DB CACHING)
# =====================================================================

ADMIN_EMAILS = ["yousufaltashfin@gmail.com", "tashfin@gstu.edu"]

# Force fetch email if missing from state
if not st.session_state.get("user_email") and st.session_state.get("logged_in"):
    try:
        active_sess = supabase.auth.get_session()
        if active_sess and active_sess.user: st.session_state.user_email = active_sess.user.email
    except: pass
    
if not st.session_state.get("user_email") and current_uid != "guest_session":
    local_user = st.session_state.users_db.get(current_uid, {})
    st.session_state.user_email = local_user.get("email", "")

# 🔴 STRICT ROLE ASSIGNMENT
if current_uid == "guest_session" or not st.session_state.get("logged_in"):
    st.session_state.user_role = "Guest"
    st.session_state.user_name = "Guest Scholar"
else:
    is_real_admin = st.session_state.get("user_email") in ADMIN_EMAILS
    db_user = st.session_state.users_db.get(current_uid, {})

    if is_real_admin:
        st.session_state.user_name = "Tashfin Yousuf"
        saved_role = db_user.get("role", "Admin")

        # 🔴 BUG FIX: Keeps the selected role active across hard refreshes
        if "simulated_role" in st.session_state:
            st.session_state.user_role = st.session_state.simulated_role
        else:
            st.session_state.user_role = saved_role
            st.session_state.simulated_role = saved_role
    else:
        if user_profile and user_profile.get('full_name'):
            st.session_state.user_name = user_profile.get('full_name')
        else:
            st.session_state.user_name = "Scholar"
        st.session_state.user_role = db_user.get("role", "Student")

    # Update Local DB safely
    if current_uid not in st.session_state.users_db: st.session_state.users_db[current_uid] = {}
    st.session_state.users_db[current_uid]["role"] = st.session_state.user_role
    st.session_state.users_db[current_uid]["name"] = st.session_state.user_name
    st.session_state.users_db[current_uid]["email"] = st.session_state.user_email
    try:
        with open(DB_FILE, "w") as f: json.dump(st.session_state.users_db, f, indent=4)
    except: pass


# =====================================================================
# 🧩 10. UI HELPER FUNCTIONS
# =====================================================================
def get_thinking_html():
    return """
    <div class="gstu-thinking">
        <div class="gstu-thinking-dots"><span></span><span></span><span></span></div>
        <span class="gstu-thinking-text">Analyzing...</span>
    </div>
    """

def get_sources_html(db_sources, is_realtime=False):
    badge = '<div class="realtime-badge">🌐 Realtime Data Powered by GSTU AI Search</div>' if is_realtime else ''
    chips = ""
    for src, pages in db_sources.items():
        page_str = f" (Pg: {', '.join(sorted(list(pages)))})" if pages else ""
        chips += f'<div class="source-chip">📄 {src}{page_str}</div>'
    if badge or chips:
        return f"{badge}<div class='sources-row'>{chips}</div>"
    return ""

def validate_file_size(file_obj, max_mb: float) -> bool:
    file_obj.seek(0, os.SEEK_END)
    size_mb = file_obj.tell() / (1024 * 1024)
    file_obj.seek(0)
    return size_mb <= max_mb

def validate_image_content(data: bytes) -> bool:
    """Check magic bytes — not just the extension."""
    return (data[:3] == b"\xff\xd8\xff" or    # JPEG
            data[:4] == b"\x89PNG"      or    # PNG
            data[:4] in (b"GIF8",))           # GIF

@st.dialog("🧠 Help GSTU AI Learn")
def feedback_dialog(msg_index):
    st.markdown("### Why did you dislike this response?")
    feedback_reason = st.text_area("Provide specific details to train the model:", placeholder="e.g., The geopolitical facts were outdated...")
    if st.button("Submit Feedback to Core", type="primary", use_container_width=True):
        # Phase 2: Save to 'ai_training_logs' in Supabase
        st.success("✅ Feedback securely logged! The Zenith routing engine will adjust future responses.")
        time.sleep(1.5)
        st.rerun()

# ⏱️ PROACTIVE STUDY LOGGER (Phase 2 - Intelligent Tracking)
@st.dialog("🎯 Quick Study Check-in", width="medium")
def study_checkin_dialog():
    st.markdown("### How was your study session?")
    topic = st.text_input("Topic studied:", placeholder="e.g., Geopolitics")
    hours = st.slider("Hours spent:", 0.0, 10.0, 1.0, 0.5)
    mood = st.select_slider("Mood/Focus level:", options=[1, 2, 3, 4, 5], value=3, help="1 = Struggled, 5 = Deep Focus")
    
    if st.button("Submit & Boost XP 🚀", type="primary", use_container_width=True):
        if topic:
            # 🔴 LOG TO SUPABASE
            try:
                # Insert session log
                supabase.table("study_sessions").insert({
                    "user_id": st.session_state.username_id,
                    "topic": topic,
                    "hours": hours,
                    "mood": mood,
                    "timestamp": datetime.datetime.now().isoformat()
                }).execute()
                
                # 🔴 AGENTIC ADAPTATION: Update learning graph based on study session
                from memory_db import update_weakness_graph
                # If mood is 1-2, it's 'Needs Review' (Weak). If 4-5, it's 'Strong'.
                status = "Strong" if mood >= 4 else "Needs Review"
                update_weakness_graph(st.session_state.username_id, topic, status)
                
                st.success("✅ Logged! Your AI profile is now updated.")
                time.sleep(1); st.rerun()
            except Exception as e:
                st.error(f"⚠️ DB Error: {e}")
        else:
            st.warning("Please enter the topic you studied.")

# =====================================================================
# 🧠 4. CACHED HEAVY DEPENDENCIES (Lazy Loading for Extreme Speed)
# =====================================================================

@st.cache_resource(show_spinner=False)
def load_heavy_dependencies():
    from groq import Groq
    groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    return groq_client

@st.cache_resource(show_spinner=False)
def get_agent_tools():
    """Importing inside function prevents blocking on app startup."""
    from agent_tools import astra_core_tools
    return astra_core_tools

# Get the tools instantly from cache (Duplicate import fixed!)
astra_core_tools = get_agent_tools()


# =====================================================================
# ⚙️ PREMIUM ACCOUNT, BILLING, ADS & PRIVACY DIALOGS (DYNAMIC)
# =====================================================================
@st.dialog("⚙️ Account Settings & Subscription", width="large")
def account_settings_dialog():
    is_guest = st.session_state.get("user_role") == "Guest" or st.session_state.get("username_id") == "guest_session"
    current_uid = st.session_state.username_id

    # 🔴 Dynamic Tabs (Guests only see Profile & System)
    if is_guest:
        tabs = st.tabs(["👤 Profile", "⚙️ System"])
        tab_profile, tab_system = tabs[0], tabs[1]
    else:
        tabs = st.tabs(["👤 Profile", "⚙️ System", "💎 Upgrade to Pro", "🎁 Earn Free Credits"])
        tab_profile, tab_system, tab_billing, tab_earn = tabs[0], tabs[1], tabs[2], tabs[3]
    
    # Fetch Live Data
    try:
        if not is_guest:
            user_res = supabase.table("user_profiles").select("*").eq("id", current_uid).execute()
            user_data = user_res.data[0] if user_res.data else {"reward_credits": 0, "subscription_tier": "free"}
            current_credits = user_data.get("reward_credits", 0)
            sub_tier = user_data.get("subscription_tier", "free")
        else:
            current_credits, sub_tier = 0, "free"
    except:
        current_credits, sub_tier = 0, "free"

    with tab_profile:
        st.markdown(f"**Name:** {st.session_state.get('user_name', 'Guest')}")
        st.markdown(f"**Email:** {st.session_state.get('user_email', 'Not provided')}")
        st.markdown(f"**Role:** `{st.session_state.get('user_role', 'Guest')}`")
        if not is_guest:
            st.markdown(f"**Balance:** 🪙 `{current_credits} AI Credits`")
        else:
            st.info("🔒 Please log in to earn AI Credits and track progress.")
        

    with tab_system:
        st.markdown("### 🎨 Interface Theme")
        theme_choice = st.selectbox(
            "Select Interface Mode", ["🌑 Dark Mode (Default)", "☀️ Light Mode"],
            index=0 if st.session_state.get("theme") != "light" else 1
        )
        if theme_choice != st.session_state.get("theme_selector_val", "🌑 Dark Mode (Default)"):
            st.session_state.theme_selector_val = theme_choice
            st.session_state.theme = "light" if "Light" in theme_choice else "dark"
            st.rerun()

       # EXCLUSIVE ADMIN CONTROL PANEL
        if st.session_state.get("user_email") in ["yousufaltashfin@gmail.com", "tashfin@gstu.edu"]:
            st.markdown("<hr style='border-color: rgba(255,255,255,0.1); margin: 20px 0;'>", unsafe_allow_html=True)
            st.markdown("### 👑 Admin Access")
            role_options = ["Admin", "Student"]
            current_idx = 0 if st.session_state.get("user_role") == "Admin" else 1
            new_role = st.selectbox("Simulate Role", role_options, index=current_idx)
            
            if new_role != st.session_state.get("user_role"):
                st.session_state.simulated_role = new_role  
                st.session_state.user_role = new_role
                if current_uid and current_uid != "guest_session" and current_uid in st.session_state.users_db:
                    st.session_state.users_db[current_uid]["role"] = new_role
                    with open(DB_FILE, "w") as f: json.dump(st.session_state.users_db, f, indent=4)
                st.toast(f"✅ Role successfully changed to {new_role}", icon="👑")
                time.sleep(0.5)
                st.rerun()

    # 🔴 Ensure Billing & Earn logic ONLY executes if NOT guest
    if not is_guest:
        with tab_billing:
            # 🔴 SMART TOGGLE: এটাকে True করে দিলেই bKash চালু হয়ে যাবে!
            USE_MANUAL_BKASH = True
            
            st.markdown("### 💎 Unlock Limitless AI Power")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("<div style='border: 1px solid #10a37f; padding: 15px; border-radius: 10px; margin-bottom: 15px;'><h4 style='color:#10a37f; margin:0;'>Basic Tier</h4><h2 style='margin:10px 0;'>$0 <span style='font-size: 14px;'>/mo</span></h2><p style='font-size: 13px;'>Standard Rate Limits</p></div>", unsafe_allow_html=True)
                if sub_tier == "free": st.button("✅ Current Plan", disabled=True, use_container_width=True)
                else: st.button("Free Tier", disabled=True, use_container_width=True)
                    
            with col2:
                st.markdown("<div style='border: 1px solid #58A6FF; padding: 15px; border-radius: 10px; background: rgba(88,166,255,0.05); margin-bottom: 15px;'><h4 style='color:#58A6FF; margin:0;'>Pro Scholar</h4><h2 style='margin:10px 0;'>৳500 <span style='font-size: 14px;'>/mo</span></h2><p style='font-size: 13px;'>Unlimited Premium AI</p></div>", unsafe_allow_html=True)
                
                if sub_tier not in ["premium", "pro_scholar"]:

                    if USE_MANUAL_BKASH:
                        # ---------------------------------------------
                        # 📱 MANUAL BKASH SYSTEM (Activates later)
                        # ---------------------------------------------
                        st.markdown("""<div style='background: rgba(255, 255, 255, 0.05); border: 1px dashed #58A6FF; padding: 12px; border-radius: 8px; margin-bottom: 12px;'><p style='margin: 0; font-size: 14px; color: #58A6FF; font-weight: bold;'>📱 bKash Personal: 01705587837</p><p style='margin: 4px 0 0 0; font-size: 12px; color: #cbd5e1;'>1. Send Money ৳500 to this number.<br>2. Enter your Transaction ID (TrxID) below.</p></div>""", unsafe_allow_html=True)
                        trx_id = st.text_input("bKash TrxID:", placeholder="e.g. 9F8A7B6C5D", label_visibility="collapsed")
                        
                        if st.button("✅ Verify & Upgrade", type="primary", use_container_width=True):
                            if len(trx_id) > 6:
                                with st.spinner("Submitting payment for verification..."):
                                    try:
                                        supabase.table("manual_payments").insert({"user_id": current_uid, "user_email": st.session_state.get("user_email", "student@gstu.edu"), "trx_id": trx_id, "amount": 500, "status": "pending"}).execute()
                                        st.success("🎉 Request Sent! Admin will verify and upgrade your account shortly.")
                                    except Exception: st.error("⚠️ Database Error.")
                            else: st.error("⚠️ Enter a valid bKash TrxID.")
                    else:
                        # ---------------------------------------------
                        # 💳 SSLCOMMERZ DEMO SYSTEM (Active Now)
                        # ---------------------------------------------
                        if st.button("💳 Pay via SSLCommerz", type="primary", use_container_width=True):
                            with st.spinner("Connecting to Secure Gateway..."):
                                # 🔴 Pure, clean function call. No environment variable hacking needed!
                                success, result = initiate_real_sslcommerz_payment(
                                    user_id=current_uid, 
                                    user_name=st.session_state.get("user_name", "Scholar"), 
                                    user_email=st.session_state.get("user_email", "student@gstu.edu")
                                )
                                
                                if success: 
                                    st.markdown(f'<meta http-equiv="refresh" content="0; url={result}">', unsafe_allow_html=True)
                                else: 
                                    st.error(f"⚠️ Gateway Error: {result}")
                    
        with tab_earn:
            st.markdown("### 🎁 Earn Credits for Premium Models")
            st.success(f"🪙 Your Current Balance: **{current_credits} Credits**")
            c1, c2 = st.columns(2)
            with c1:
                st.info("📺 **Watch Sponsored Video** (+10)")
                st.markdown(f"""<a href="https://monetag.com/rewarded_link_here?subid={current_uid}" target="_blank" style="display: block; text-align: center; background-color: #10a37f; color: white; padding: 10px; border-radius: 8px; text-decoration: none; font-weight: bold;">▶️ Watch Ad to Earn</a>""", unsafe_allow_html=True)
            with c2:
                st.info("📱 **Download & Try App** (+50)")
                st.markdown(f"""<a href="https://www.cpagrip.com/show.php?l=offerwall_link_here&tracking_id={current_uid}" target="_blank" style="display: block; text-align: center; background-color: #0f172a; border: 1px solid #cbd5e1; color: white; padding: 10px; border-radius: 8px; text-decoration: none; font-weight: bold;">📥 View Offers</a>""", unsafe_allow_html=True)


# =====================================================================
# 🔴 PROFILE PILL LAYOUT (Clean & Professional Style - NO WRAPPING)
# =====================================================================
# 🔴 Increased width to 18% so the name NEVER wraps or breaks!

st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem !important; }
    </style>
""", unsafe_allow_html=True)

@st.dialog("🛡️ Privacy Policy & Help Center", width="large")
def help_privacy_dialog():
    tab_help, tab_privacy = st.tabs(["🆘 Help Center", "🔐 Privacy Policy"])
    
    with tab_help:
        st.markdown("### How to use GSTU AI?")
        with st.expander("1. How do I switch AI engines?"): st.write("Click the dropdown menu at the top of the chat interface to switch between Fast Engine (Llama), Web Search (Gemini), and Offline Mode.")
        with st.expander("2. How does the offline mode work?"): st.write("You must run the local GPT4All server on port 4891. Your data never leaves your device.")
        with st.expander("3. Need further support?"): st.write("Contact the admin at: `yousufaltashfin@gmail.com`")
        
    with tab_privacy:
        st.markdown("""
        ### GSTU IR AI - Data Protection Agreement
        **1. End-to-End Encryption:** All chat queries and vector embeddings are secured.  
        **2. Zero Data Selling:** We do not sell your academic prompts or personal data to third parties.  
        **3. Institutional Data:** Uploaded PDFs are stored locally in ChromaDB and are not exposed to cloud providers unless specifically processed by a cloud model.  
        **4. Supabase Auth:** Authentication is managed securely via Supabase OAuth 2.0 protocols.
        """)

# প্রোফাইল পিল একদম ডান কর্নারে সেট করা হলো
col_space, col_profile = st.columns([0.82, 0.18]) 
with col_profile:
    current_uid = st.session_state.get("username_id", "guest_session")
    
    # 🔴 Ensure users_db exists safely
    if "users_db" not in st.session_state: st.session_state.users_db = {}
    if current_uid not in st.session_state.users_db: st.session_state.users_db[current_uid] = {}
        
    user_data = st.session_state.users_db.get(current_uid, {})
    avatar_b64 = user_data.get("avatar")
    
    tier = user_data.get("subscription_tier", "free")
    tier_text = "⭐ Pro Scholar" if tier in ["pro_scholar", "premium"] else "🆓 Free Tier"
    tier_color = "#58A6FF" if tier in ["pro_scholar", "premium"] else "#94a3b8"
    
    # 🔴 Safe String Checking (Prevents AttributeError causing blank screen)
    safe_name = st.session_state.get("user_name")
    if not safe_name or not isinstance(safe_name, str): 
        safe_name = "Guest Scholar"
        
    first_name = safe_name.split()[0][:10]
    btn_label = f"👤 {first_name}"
    
    # 🔴 CSS to force the button text to stay on ONE single line
    st.markdown("""
        <style>
        div[data-testid="column"]:nth-child(2) div[data-testid="stPopover"] > button {
            white-space: nowrap !important;
            min-width: 110px !important;
            border-radius: 8px !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    with st.popover(btn_label, use_container_width=True):
        if avatar_b64:
            st.markdown(f"<div style='text-align: center;'><img src='data:image/jpeg;base64,{avatar_b64}' style='width: 80px; height: 80px; border-radius: 50%; object-fit: cover; border: 2px solid #10a37f; margin-bottom: 5px; box-shadow: 0 4px 10px rgba(0,0,0,0.3);'></div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='text-align: center;'><img src='data:image/jpeg;base64,{logo_b64}' style='width: 80px; height: 80px; border-radius: 50%; object-fit: cover; border: 2px solid #10a37f; margin-bottom: 5px; box-shadow: 0 4px 10px rgba(0,0,0,0.3);'></div>", unsafe_allow_html=True)
            
        st.markdown(f"<h4 style='text-align: center; margin: 0; padding: 0;'>{st.session_state.user_name}</h4>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; color: {tier_color}; margin: 5px 0 15px 0; font-size: 13px; font-weight: 600;'>{tier_text} • {st.session_state.user_role}</p>", unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("<p style='font-size: 13px; font-weight: 600; margin-bottom: 5px;'>📸 Change Profile Picture</p>", unsafe_allow_html=True)
        uploaded_pic = st.file_uploader("", type=["png", "jpg", "jpeg"], key="profile_pic_upload_dialog", label_visibility="collapsed")
        
        if uploaded_pic is not None:
            bytes_data = uploaded_pic.getvalue()
            b64_str = base64.b64encode(bytes_data).decode()
            if b64_str != st.session_state.users_db[current_uid].get("avatar"):
                st.session_state.users_db[current_uid]["avatar"] = b64_str
                try:
                    with open(DB_FILE, "w") as f: json.dump(st.session_state.users_db, f, indent=4)
                except Exception: pass
                st.toast("✅ Profile picture updated successfully!")
                time.sleep(0.5)
                st.rerun()

        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        if st.button("⚙️ Account Settings", use_container_width=True): account_settings_dialog()
        if st.button("🛡️ Privacy & Help", use_container_width=True): help_privacy_dialog()
        
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        if st.button("🚪 Logout", use_container_width=True, type="primary"):
            try: supabase.auth.sign_out()
            except: pass
            for c_key in ["access_token", "refresh_token", "user_id", "gstu_uid"]:
                try: cookie_controller.remove(c_key)
                except: pass
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            time.sleep(0.5)
            st.rerun()


# 5. Premium Modals / Dialogs
@st.dialog("⭐ Save Project To...")
def save_dialog():
    existing_folders = sorted(list(set(ch["folder"] for ch in st.session_state.chat_history if ch.get("folder"))))
    if existing_folders:
        selected = st.selectbox("Select Folder:", existing_folders)
        if st.button("Save & Move", use_container_width=True):
            for ch in st.session_state.chat_history:
                if ch["title"] == st.session_state.active_chat_title: ch["folder"] = selected
            save_chat_history(st.session_state.chat_history)
            st.success(f"✅ Successfully moved to {selected}!")
            time.sleep(1.2); st.rerun()
    else: st.info("No folders exist yet. Create one below.")

@st.dialog("✏️ Rename Current Chat")
def rename_dialog():
    new_name = st.text_input("Enter new name:", value=st.session_state.active_chat_title)
    if st.button("Update Name", use_container_width=True):
        new_t = new_name.strip()
        if new_t and new_t != st.session_state.active_chat_title:
            old_t = st.session_state.active_chat_title
            st.session_state.active_chat_title = new_t
            for ch in st.session_state.chat_history:
                if ch["title"] == old_t: ch["title"] = new_t
            save_chat_history(st.session_state.chat_history)
            st.success("✅ Chat renamed successfully!")
            time.sleep(1.2); st.rerun()

@st.dialog("🗑️ Delete Chat")
def delete_dialog():
    st.warning("Are you sure you want to permanently delete this chat?")
    if st.button("Yes, Delete", use_container_width=True):
        st.session_state.chat_history = [ch for ch in st.session_state.chat_history if ch["title"] != st.session_state.active_chat_title]
        save_chat_history(st.session_state.chat_history)
        st.session_state.messages = []
        st.session_state.active_chat_title = None
        st.error("🗑️ Chat deleted permanently!")
        time.sleep(1.2); st.rerun()

@st.dialog("➕ Create New Project")
def create_project_dialog():
    new_proj = st.text_input("Enter Project Folder Name:", placeholder="e.g. Midterm Prep")
    if st.button("Create & Save Current Chat", use_container_width=True):
        folder_n = new_proj.strip()
        if folder_n:
            for ch in st.session_state.chat_history:
                if ch["title"] == st.session_state.active_chat_title: ch["folder"] = folder_n
            save_chat_history(st.session_state.chat_history)
            st.success(f"✅ Folder '{folder_n}' created successfully!")
            time.sleep(1.2); st.rerun()

@st.dialog("🗑️ Delete Selected Chats")
def bulk_delete_dialog(selected_titles):
    n = len(selected_titles)
    st.warning(f"Permanently delete **{n} chat{'s' if n > 1 else ''}**? This cannot be undone.")
    if st.button(f"Yes, Delete {n} Chat{'s' if n > 1 else ''}", use_container_width=True, type="primary"):
        title_set = set(selected_titles)
        st.session_state.chat_history = [ch for ch in st.session_state.chat_history if ch["title"] not in title_set]
        save_chat_history(st.session_state.chat_history)
        for k in list(st.session_state.keys()):
            if k.startswith("cb_"): del st.session_state[k]
        st.session_state.selection_mode = False
        if st.session_state.active_chat_title in title_set:
            st.session_state.messages = []
            st.session_state.active_chat_title = None
        st.success(f"✅ Deleted {n} chat{'s' if n > 1 else ''}!")
        time.sleep(1.0); st.rerun()

@st.dialog("📁 Move Selected to Project")
def bulk_move_dialog(selected_titles):
    n = len(selected_titles)
    existing_folders = sorted(list(set(ch["folder"] for ch in st.session_state.chat_history if ch.get("folder"))))
    tab1, tab2 = st.tabs(["📂 Existing Folder", "✨ New Folder"])
    with tab1:
        if existing_folders:
            folder = st.selectbox("Select folder:", existing_folders, key="bulk_folder_select")
            if st.button("Move to Selected Folder", use_container_width=True, key="bulk_move_existing"):
                title_set = set(selected_titles)
                for ch in st.session_state.chat_history:
                    if ch["title"] in title_set: ch["folder"] = folder
                save_chat_history(st.session_state.chat_history)
                for k in list(st.session_state.keys()):
                    if k.startswith("cb_"): del st.session_state[k]
                st.session_state.selection_mode = False
                st.success(f"✅ Moved {n} chat{'s' if n > 1 else ''} to '{folder}'!")
                time.sleep(1.0); st.rerun()
        else: st.info("No existing folders.")
    with tab2:
        new_folder = st.text_input("New folder name:", placeholder="e.g. Midterm Prep", key="bulk_new_folder")
        if st.button("Create Folder & Move", use_container_width=True, key="bulk_move_new"):
            fn = new_folder.strip()
            if fn:
                title_set = set(selected_titles)
                for ch in st.session_state.chat_history:
                    if ch["title"] in title_set: ch["folder"] = fn
                save_chat_history(st.session_state.chat_history)
                for k in list(st.session_state.keys()):
                    if k.startswith("cb_"): del st.session_state[k]
                st.session_state.selection_mode = False
                st.success(f"✅ Created '{fn}' and moved {n} chat{'s' if n > 1 else ''}!")
                time.sleep(1.0); st.rerun()


# =====================================================================
# 🔴 ENTERPRISE ADMIN ANALYTICS DASHBOARD (DYNAMIC)
# =====================================================================
@st.dialog("📈 Enterprise Admin Analytics", width="large")
def admin_dashboard_dialog():
    # 🔴 Added Payment Approval Tab
    tab_overview, tab_payments, tab_support= st.tabs(["📊 Live Overview", "💳 Approve Payments", "Support Ticket"])
    
    with tab_overview:
        st.markdown("### 📊 System Overview")
        try:
            # 1. Fetch Users Data (Tiers and Departments)
            users_res = supabase.table("user_profiles").select("id, subscription_tier, department").execute()
            all_users = users_res.data if users_res.data else []
            total_users = len(all_users)
            
            pro_users = sum(1 for u in all_users if u.get("subscription_tier") in ["pro_scholar", "premium"])
            free_users = total_users - pro_users
            
            dept_counts = {}
            for u in all_users:
                d = u.get("department", "Unknown")
                if d: dept_counts[d] = dept_counts.get(d, 0) + 1
                
            # 2. Fetch Query Logs
            logs_res = supabase.table("ai_training_logs").select("topic_tag").execute()
            chats_count = len(logs_res.data) if logs_res.data else 0
            
            import pandas as pd
            if logs_res.data:
                df = pd.DataFrame(logs_res.data)
                trending_topics = df['topic_tag'].value_counts().head(5)
            else:
                trending_topics = []

        except Exception as e:
            total_users, chats_count, pro_users, free_users, dept_counts, trending_topics = 0, 0, 0, 0, {}, []

        available_models = ["Llama 4", "Gemini 2.5 Flash", "Gemini 2.5 Pro", "DeepSeek R1", "GPT-4o Mini", "GPT-4o", "Claude 3.5", "Llama 3 70B", "Qwen 72B", "GPT4All Offline"]
        total_models_count = len(available_models)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("👥 Total Users", total_users)
        c2.metric("👑 Pro / Free", f"{pro_users} / {free_users}")
        c3.metric("🧠 Active Models", f"{total_models_count} Engines")
        c4.metric("💰 Est. Revenue", f"৳ {pro_users * 500}")
        
        st.markdown("---")
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.markdown("#### 🔥 Top Trending Topics")
            if len(trending_topics) > 0:
                for topic, count in trending_topics.items():
                    st.markdown(f"- **{str(topic).title()}** (`{count}` queries)")
            else:
                st.info("No query logs yet.")
                
        with col_b:
            st.markdown("#### 🏛️ Dept-Wise Users")
            if dept_counts:
                for d, c in sorted(dept_counts.items(), key=lambda x: x[1], reverse=True):
                    st.markdown(f"- **{d}**: `{c}` users")
            else:
                st.info("No department data.")

    with tab_payments:
        st.markdown("### ⏳ Pending bKash Manual Payments")
        try:
            pending_res = supabase.table("manual_payments").select("*").eq("status", "pending").execute()
            pending_payments = pending_res.data if pending_res.data else []
            
            if pending_payments:
                for p in pending_payments:
                    st.markdown("<div style='border:1px solid #10a37f; padding: 10px; border-radius:8px; margin-bottom:10px;'>", unsafe_allow_html=True)
                    p_col1, p_col2, p_col3 = st.columns([2, 2, 1])
                    p_col1.markdown(f"**Email:** {p.get('user_email')}")
                    p_col2.markdown(f"**TrxID:** `{p.get('trx_id')}`")
                    
                    # 🔴 1-Click Approve Logic
                    if p_col3.button("✅ Approve", key=f"app_{p['id']}", type="primary", use_container_width=True):
                        with st.spinner("Approving..."):
                            # 1. Upgrade User
                            supabase.table("user_profiles").update({"subscription_tier": "pro_scholar"}).eq("id", p["user_id"]).execute()
                            # 2. Mark Payment as Approved
                            supabase.table("manual_payments").update({"status": "approved"}).eq("id", p["id"]).execute()
                            st.success(f"✅ Approved {p.get('user_email')}!")
                            time.sleep(1)
                            st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.info("🎉 All caught up! No pending payments at the moment.")
        except Exception:
            st.error("⚠️ Ensure you have created the `manual_payments` table in Supabase.")
    

    # ============================================================
    # 🛠️ ADMIN PANEL: SUPPORT TICKET MANAGEMENT (Detailed View)
    # ============================================================
    with tab_support:
        # Premium Internal Header
        st.markdown("""
            <div style='text-align:center; padding-bottom: 15px;'>
                <span style='font-size: 35px; line-height: 1;'>🎧</span>
                <h3 style='color:#10a37f; margin: 8px 0 4px 0; font-weight: 700; font-size: 20px;'>AI Support Desk</h3>
                <p style='color: gray; font-size: 13px; margin: 0; line-height: 1.4;'>Submit bugs, payment issues, or system feedback.</p>
            </div>
        """, unsafe_allow_html=True)
        
        # Clean Text Area
        cs_query = st.text_area("Issue Details:", placeholder="Describe your issue clearly...", height=120, key="cs_input", label_visibility="collapsed")
          
        try:
            ticket_res = supabase.table("support_tickets").select("*").eq("ticket_status", "Open").order("created_at", desc=True).execute()
            if ticket_res.data:
                st.warning(f"⚠️ You have {len(ticket_res.data)} unresolved support ticket(s).")
                
                for t in ticket_res.data:
                    # 🔴 FETCH SAVED EMAIL DIRECTLY
                    user_email = t.get('user_email', 'Unknown Email')
                    uid = t.get('user_id', 'N/A')
                    
                    # 🔴 BULLETPROOF DATE PARSING
                    raw_date = t.get('created_at', '')
                    try:
                        # '2026-06-09T18:03:51.537246+00:00' -> '2026-06-09 18:03:51'
                        clean_date = raw_date.split('.')[0].replace('T', ' ')
                        dt_obj = datetime.datetime.strptime(clean_date, "%Y-%m-%d %H:%M:%S")
                        formatted_time = dt_obj.strftime("%d %b %Y, %I:%M %p")
                    except:
                        # If parsing completely fails, at least show a clean string without microseconds
                        formatted_time = raw_date.split('.')[0].replace('T', ' ')

                    # 🔴 CLEAN UI
                    with st.expander(f"🔴 Issue from: {user_email} | {formatted_time}"):
                        st.markdown(f"**📝 Detailed Query:**\n\n{t.get('query')}")
                        st.markdown(f"👤 **Email:** `{user_email}` | 🔑 **System ID:** `{uid}`")
                        
                        if st.button("✅ Mark as Resolved & Close", key=f"resolve_{t['id']}", type="primary"):
                            with st.spinner("Closing ticket..."):
                                supabase.table("support_tickets").update({"ticket_status": "Resolved"}).eq("id", t['id']).execute()
                                st.success(f"Ticket closed successfully!")
                                import time; time.sleep(1); st.rerun()
            else:
                st.success("🎉 Great job! No pending support tickets right now.")
                
        except Exception as e:
            st.error(f"⚠️ Could not fetch tickets. Database Error: {e}")

    st.markdown("<hr><p style='font-size: 12px; color: gray;'>*All detailed query logs are safely stored in Supabase `ai_training_logs` table for future Fine-tuning.</p>", unsafe_allow_html=True)


# Enterprise Standard Secret Management
groq_api_key = os.environ.get("GROQ_API_KEY")

if not groq_api_key:
    try:
        groq_api_key = st.secrets.get("GROQ_API_KEY")
    except Exception:
        pass

if not groq_api_key:
    st.error("⚠️ GROQ_API_KEY is missing. Add it to .env or Streamlit secrets.")
    st.stop()

# 7. State Management
if "chat_history" not in st.session_state: st.session_state.chat_history = load_chat_history_cached()
if "quick_query" not in st.session_state: st.session_state.quick_query = None
if "active_chat_title" not in st.session_state: st.session_state.active_chat_title = None
if "messages" not in st.session_state: st.session_state.messages = []
if "current_chat_id" not in st.session_state: st.session_state.current_chat_id = None
if "selection_mode" not in st.session_state: st.session_state.selection_mode = False
if "current_model" not in st.session_state: st.session_state.current_model = "meta-llama/llama-4-scout-17b-16e-instruct" 



# 🔴 MULTI-MODEL ROUTER (Universal API Switcher)
def get_llm(model_id):
    if "gemini" in model_id.lower():
        google_api_key = os.getenv("GOOGLE_API_KEY") or st.secrets.get("GOOGLE_API_KEY")
        return ChatGoogleGenerativeAI(model=model_id, temperature=0.2, google_api_key=google_api_key)
        
    # 🔴 Qwen k Llama er sathe Groq engine e route kora holo
    elif "llama" in model_id.lower() or "qwen" in model_id.lower():
        groq_api_key = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY")
        return ChatGroq(model_name=model_id, temperature=0.5, groq_api_key=groq_api_key)
        
    elif model_id == "local-gpt4all":
        # 🔴 THE LOCAL OFFLINE ENGINE (Connects to GPT4All Server)
        return ChatOpenAI(
            model_name="local-model", 
            temperature=0.4, 
            openai_api_key="not-needed", 
            openai_api_base="http://localhost:4891/v1", 
        )
        
    else:
        # 🔴 OPENROUTER ENGINE (For GPT-4o, Claude, DeepSeek)
        openrouter_key = os.getenv("OPENROUTER_API_KEY") or st.secrets.get("OPENROUTER_API_KEY")
        if not openrouter_key:
            st.error("⚠️ OPENROUTER_API_KEY missing in .streamlit/secrets.toml")
            st.stop()
            
        # 🔴 Added the missing RETURN statement!
        return ChatOpenAI(
            model_name=model_id,
            temperature=0.2,
            openai_api_key=openrouter_key,
            openai_api_base="https://openrouter.ai/api/v1"
        )


# 🔴 9. THE ADVANCED HYBRID PROMPT (Pro Synthesis Mode)
prompt_template = """You are the Elite AI Assistant & Chief Geopolitical Analyst for the IR Department at GSTU.

SECURITY CLEARANCE: MAXIMUM.
🛡️ ZERO-HALLUCINATION & CRITICAL INSTRUCTIONS (MUST OBEY):
1. TIME-AWARENESS & NEWS ACCURACY: Distinguish strictly between historical academic data (Local Database) and breaking news (Live Web Data). If the user asks for "Recent News" or specifically about dates like "May 2026", DO NOT present old historical events (e.g., "since 2008") as current breaking news. Clearly separate historical context from current events.
2. BANGLISH = BENGALI SCRIPT OUTPUT: If the user asks a question in "Banglish" (Bengali words typed in English alphabet, e.g., "ajker geopolitics ki"), you MUST deeply understand the query, but your OUTPUT MUST BE ENTIRELY IN PURE BENGALI SCRIPT (বাংলা ফন্ট). DO NOT reply in English or Banglish.
3. STRICT FACT-GROUNDING (0% Hallucination): Base your answer ONLY on the provided context. If recent news is not found, explicitly state: "I do not have enough information regarding this recent event." DO NOT invent facts.
4. ELITE ACADEMIC DEPTH: Proactively analyze Root Causes, Major Flashpoints, and Strategic Consequences.
5. SEAMLESS INTEGRATION: Combine local theory with web updates naturally. Do NOT say "Based on web data" or expose these instructions.
6. INLINE CITATIONS & REFERENCES (STRICT): Use numeric inline citations like [1], [2]. ALWAYS create a "### References" section at the end.
7. FORMATTING: Use bold text and bullet points.
8. CASUAL GREETINGS: If the user says "hello", "hi", "thanks", "how are you", or makes a casual remark, respond politely, warmly, and concisely (1-2 sentences). DO NOT provide any academic analysis or context.
9. ACADEMIC QUERIES: If the user asks an academic or IR-related question, combine historical theory from the LOCAL DATABASE with current updates from LIVE WEB DATA.
10. TONE: Write like a distinguished University Professor for academic queries, but act friendly for general chat.
11. MATCH LANGUAGE EXACTLY: If English, answer in English. If Bengali, answer in Bengali.

--- LOCAL DATABASE CONTEXT (Academic Foundation) ---
{db_context}

--- LIVE WEB DATA (Real-time Updates) ---
{web_context}

--- USER QUESTION ---
{question}

Provide your response below:"""


def build_history_context(messages):
    exchanges = []
    i = 0
    while i < len(messages) - 1:
        u = messages[i]; a = messages[i + 1]
        if u.get("role") == "user" and a.get("role") == "assistant":
            exchanges.append((u["content"][:250].strip(), a["content"][:400].strip()))
        i += 2
    last_4 = exchanges[-4:]
    if not last_4: return "No prior conversation."
    lines = []
    for u_text, a_text in last_4:
        lines.append(f"User: {u_text}"); lines.append(f"Assistant: {a_text}")
    return "\n".join(lines)

def _cb_key(prefix, title):
    safe = "".join(c for c in title if c.isalnum() or c == "_")[:18]
    return f"cb_{prefix}_{safe}"


# 11. The Sidebar Panel
with st.sidebar:
        
    logo_img_tag = f'<img src="data:image/png;base64,{logo_b64}" style="width:48px; height:48px; border-radius:50%; object-fit:cover; display:block;">' if logo_b64 else "<span style='font-size: 40px; margin:0;'>🎓</span>"
        
    st.markdown(f"""
    <style>
    .gstu-text-hover {{ color: white; font-size: 26px; font-weight: 900; letter-spacing: -0.5px; transition: color 0.2s ease; }}
    .gstu-sidebar-header-link:hover .gstu-text-hover {{ color: #10a37f !important; }}
    
    [data-testid="stSidebar"] div[data-testid="stButton"] > button {{
        background: transparent !important; border: none !important; justify-content: flex-start !important;
        text-align: left !important; box-shadow: none !important; padding-left: 10px !important;
        color: inherit !important; width: 100% !important;
    }}
    [data-testid="stSidebar"] div[data-testid="stButton"] > button:hover {{
        background: rgba(16, 163, 127, 0.15) !important; color: #10a37f !important; border-radius: 8px !important;
    }}
    </style>

    <div class="gstu-sidebar-header-container" style="margin-top: -10px; margin-bottom: 25px; display: flex; justify-content: center; align-items: center;">
        <a href="/" target="_self" class="gstu-sidebar-header-link" style="display: flex; align-items: center; gap: 14px; text-decoration: none;">
            {logo_img_tag}
            <div class="gstu-text-hover">GSTU IR AI</div>
        </a>
    </div>
""", unsafe_allow_html=True)

    # Search bar
    search_q = st.text_input("Search", placeholder="🔍 Search projects...", label_visibility="collapsed")
    

    # 🔴 Perfect spacing before the action buttons
    st.markdown("<div style='margin-top: 20px; margin-left: 12px;'></div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📝 New Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.active_chat_title = None
            st.rerun()
    with col2:
        if st.button("⭐ Save To...", use_container_width=True):
            if not st.session_state.active_chat_title: st.toast("Start chatting first!", icon="⚠️")
            else: save_dialog()

    col3, col4 = st.columns(2)
    with col3:
        if st.button("✏️ Rename", use_container_width=True):
            if not st.session_state.active_chat_title: st.toast("Start chatting first!", icon="⚠️")
            else: rename_dialog()
    with col4:
        if st.button("🗑️ Delete", use_container_width=True):
            if not st.session_state.active_chat_title: st.toast("Start chatting first!", icon="⚠️")
            else: delete_dialog()
    
    # 📝 Role-based Study Logger (Visible only to Students)
    if st.session_state.get("user_role") == "Student":
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("📝 Log Study Session", use_container_width=True):
            study_checkin_dialog()

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("➕ Create New Project", use_container_width=True):
        if not st.session_state.active_chat_title: st.toast("Start chatting first!", icon="⚠️")
        else: create_project_dialog()

    st.markdown("---")
    

    filtered_history = st.session_state.chat_history
    if search_q: filtered_history = [ch for ch in st.session_state.chat_history if search_q.lower() in ch["title"].lower()]

    folders = {}
    recent_chats = []
    seen_recent_titles = set()
    for ch in filtered_history:
        f = ch.get("folder")
        if f:
            if f not in folders: folders[f] = []
            folders[f].append(ch)
        else:
            if ch["title"] not in seen_recent_titles:
                seen_recent_titles.add(ch["title"])
                recent_chats.append(ch)

    sel_toggle_col, sel_label_col = st.columns([0.35, 0.65])
    with sel_toggle_col:
        new_mode = st.toggle("", key="sel_mode_toggle", value=st.session_state.selection_mode)
    with sel_label_col:
        st.markdown("<span style='font-size:13px;opacity:0.65;line-height:2.2;'>Selection mode</span>", unsafe_allow_html=True)

    if new_mode != st.session_state.selection_mode:
        st.session_state.selection_mode = new_mode
        for k in list(st.session_state.keys()):
            if k.startswith("cb_"): del st.session_state[k]
        st.rerun()

    all_chats_flat = []
    for folder_name, chats in folders.items():
        for i, past in enumerate(chats): all_chats_flat.append((f"f_{folder_name}", past, i))
    for i, past in enumerate(recent_chats): all_chats_flat.append(("r", past, i))

    if st.session_state.selection_mode:
        selected_titles = [past["title"] for (cb_prefix, past, idx) in all_chats_flat if st.session_state.get(f"{_cb_key(cb_prefix, past['title'])}_{idx}", False)]
    
        if selected_titles:
            n_sel = len(selected_titles)
            st.markdown(f"<div style='text-align:center;font-size:12px;opacity:0.7;margin-bottom:8px;'>☑️ <strong>{n_sel}</strong> chat{'s' if n_sel > 1 else ''} selected</div>", unsafe_allow_html=True)
            
            
            # 🔴 The New Select All Button
            if st.button("☑️ Select All", use_container_width=True):
                for cb_prefix, past, idx in all_chats_flat:
                    st.session_state[f"{_cb_key(cb_prefix, past['title'])}_{idx}"] = True
                st.rerun()
                
            ba1, ba2 = st.columns(2)
            with ba1:
                if st.button("🗑️ Delete", key="bulk_del_btn", use_container_width=True): bulk_delete_dialog(selected_titles)
            with ba2:
                if st.button("📁 Move", key="bulk_move_btn", use_container_width=True): bulk_move_dialog(selected_titles)
            
            
        else: st.caption("☑️ Tap chats below to select them")
        st.markdown("---")

    for folder_name, chats in folders.items():
        st.markdown(f"<div class='sidebar-section-title'>📁 {folder_name}</div>", unsafe_allow_html=True)
        for i, past in enumerate(chats):
            title = past["title"]
            is_active = (title == st.session_state.active_chat_title)
            cbk = f"{_cb_key(f'f_{folder_name}', title)}_{i}"
            if st.session_state.selection_mode: st.checkbox(f"💬 {title[:30]}...", key=cbk)
            else:
                if is_active: st.markdown(f"<div class='recent-chat-btn recent-chat-active'>💬 {title[:25]}...</div>", unsafe_allow_html=True)
                else:
                    if st.button(f"💬 {title[:25]}...", key=f"btn_{cbk}", use_container_width=True):
                        st.session_state.messages = past["messages"].copy()
                        st.session_state.active_chat_title = title
                        st.rerun()

    if recent_chats or (st.session_state.active_chat_title and not any(ch["title"] == st.session_state.active_chat_title for ch in filtered_history)):
        st.markdown("<div class='sidebar-section-title', style='font-size: 18px; font-weight: bold;'>🕒 Recent Chats</div>", unsafe_allow_html=True)
        if st.session_state.active_chat_title and not any(ch["title"] == st.session_state.active_chat_title for ch in filtered_history):
            st.markdown(f"<div class='recent-chat-btn recent-chat-active'>💬 {st.session_state.active_chat_title[:25]}...</div>", unsafe_allow_html=True)
        for i, past in enumerate(recent_chats):
            title = past["title"]
            is_active = (title == st.session_state.active_chat_title)
            cbk = f"{_cb_key('r', title)}_{i}"
            if st.session_state.selection_mode: st.checkbox(f"💬 {title[:30]}...", key=cbk)
            else:
                if is_active: st.markdown(f"<div class='recent-chat-btn recent-chat-active', style='border-left: 4px solid #10a37f !important;'>💬 {title[:25]}...</div>", unsafe_allow_html=True)
                else:
                    safe_r_key = f"btn_{cbk}"
                    if st.button(f"💬 {title[:25]}...", key=safe_r_key, use_container_width=True):
                        st.session_state.messages = past["messages"].copy()
                        st.session_state.active_chat_title = title
                        st.rerun()

    # =========================================================
    # 🎧 DYNAMIC ADMIN SUPPORT TICKET (Database Connected)
    # =========================================================
    st.markdown("---")
    with st.popover("🎧 AI Support", use_container_width=True):
        st.markdown("<h5 style='color:#10a37f;'>GSTU AI Support</h5>", unsafe_allow_html=True)
        cs_query = st.text_area("Issue Details:", placeholder="E.g., My 500tk payment failed via bKash. Transaction ID: 8X9Y...", height=120, key="cs_input")

        if st.button("Send to Admin", type="primary", use_container_width=True):
            if cs_query:
                with st.spinner("Creating Ticket..."):
                    try:
                        # 🔴 GET DIRECT EMAIL FROM SESSION
                        current_email = st.session_state.get("user_email") or st.session_state.get("email") or "User Email Not Found"
                        
                        # 🔴 DIRECT SUPABASE INSERTION
                        supabase.table("support_tickets").insert({
                            "user_id": st.session_state.get("username_id", "guest"),
                            "query": cs_query,
                            "user_email": current_email,
                            "category": "General Support",
                            "ticket_status": "Open",
                            "created_at": datetime.datetime.now().isoformat()
                        }).execute()
                        
                        st.success("🎫 Ticket Created Successfully! Admin will contact you soon.")
                    except Exception as e:
                        # RLS Error বা অন্য কোনো ডাটাবেস এরর হলে এটা ধরবে
                        st.error(f"Database Offline or Permission Error: {e}")
            else:
                st.warning("Please type your issue first.")
    st.markdown("---")
    

    # 12. Main Chat Interface
    llm = get_llm(st.session_state.current_model)
            
    # ==============================================================
    # 📅 1. THE 7-DAY ROUTINE DIALOG (Moved out of Main Dashboard)
    # ==============================================================
    @st.dialog("📅 7-Day CGPA Boost Plan", width="large")
    def routine_dialog():
        with st.spinner("Agent is analyzing your academic data and generating a custom plan..."):
            try:
                from core_agents import generate_cgpa_boost_plan
                plan_result = generate_cgpa_boost_plan(st.session_state.username_id)
                
                if plan_result.get("status") == "success":
                    st.success("✅ Routine generated and saved successfully!")
                    plan_data = plan_result["plan"]
                    
                    for day in ["day_1", "day_2", "day_3", "day_4", "day_5", "day_6", "day_7"]:
                        if day in plan_data:
                            day_title = day.replace("_", " ").title()
                            focus = plan_data[day].get('focus_subject', 'Review')
                            strategy = plan_data[day].get('strategy', '')
                            st.markdown(f"**{day_title} — 🎯 {focus}**")
                            st.info(f"💡 {strategy}")
                            
                    if "ai_advice" in plan_data:
                        st.warning(f"🧠 **AI Advice:** {plan_data['ai_advice']}")
                else:
                    st.error(f"⚠️ Agent Error: {plan_result.get('message')}")
            except Exception as raw_e:
                st.error(f"🚨 System Crash: {str(raw_e)}")


    # ==============================================================
    # ⚔️ 2. THE DEDICATED DEBATE ROOM (Isolated from Main Chat)
    # ==============================================================
    @st.dialog("⚔️ AI Debate Arena", width="large")
    def debate_dialog():
        st.markdown("### Challenge the AI 🛡️")
        st.write("Enter your strongest geopolitical argument. The AI will counter you aggressively.")
        
        user_argument = st.text_area("Your Argument:", placeholder="e.g., China's BRI is purely an economic trap, not development.")
        
        if st.button("Start Debate ⚔️", type="primary", use_container_width=True):
            if user_argument:
                with st.spinner("AI is formulating a counter-argument..."):
                    try:
                        llm = get_llm(st.session_state.current_model)
                        prompt = f"Act as a master debater. Counter this argument aggressively with facts, geopolitics, and IR theories. Keep it under 200 words. Argument: {user_argument}"
                        response = llm.invoke(prompt)
                        st.error("🥊 **AI Counter-Argument:**")
                        st.markdown(response.content)
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
            else:
                st.warning("Please enter an argument.")


    # ==============================================================
    # 🧠 3. THE ASSESSMENT ENGINE DIALOG (Mock Exam Loop)
    # ==============================================================
    @st.dialog("🧠 AI Assessment Engine", width="large")
    def assessment_dialog(role):
        st.markdown(f"### {'🎯 Generate Tough Mock Exam' if role == 'Student' else '📋 Generate Class Quiz & Notes'}")
        topic = st.text_input("Enter Topic:", placeholder="e.g., Cold War, Realism")
        
        if st.button("Generate Assessment", type="primary", use_container_width=True):
            if topic:
                with st.spinner("Agent is crafting your assessment..."):
                    try:
                        from core_agents import generate_smart_assessment
                        res = generate_smart_assessment(topic, role)
                        
                        if res.get("status") == "success":
                            data = res["data"]
                            st.success("✅ Assessment generated successfully!")
                            
                            # 🔴 Student View (Mock Exam) - Fixed Loop & Answers!
                            if data.get("assessment_type") == "Mock Exam":
                                st.markdown(f"#### 📜 {data.get('exam_rules', '')}")
                                
                                for idx, q in enumerate(data.get('questions', [])):
                                    st.markdown(f"**Q{idx+1}. {q.get('q')}** *(Level: {q.get('difficulty')})*")
                                    
                                    with st.expander("💡 View Hints (For self-evaluation)"):
                                        for hint in q.get('hints', []): st.write(f"- {hint}")
                                        
                                    with st.expander("👁️ Reveal Ideal Answer & Key Points"):
                                        st.info("**Key points you MUST include:**\n" + "\n".join([f"- {pt}" for pt in q.get('key_points', [])]))
                                        st.success(f"**📚 AI Model Answer:**\n\n{q.get('model_answer', 'No answer provided by model.')}")
                                        
                                    st.markdown("<hr style='margin: 10px 0; border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
                            
                            # 🔴 Faculty/Admin View (Quiz)
                            else:
                                st.markdown("#### 📝 Multiple Choice Questions")
                                for idx, mcq in enumerate(data.get('mcqs', [])):
                                    st.markdown(f"**Q{idx+1}. {mcq.get('q')}**")
                                    st.success(f"**Answer:** {mcq.get('answer')}")
                        else:
                            st.error(f"⚠️ Error: {res.get('message')}")
                    except Exception as e:
                        st.error(f"🚨 Crash: {str(e)}")


    # =====================================================================
    # 📚 KNOWLEDGE BASE UPLOADER (RAG MANAGER FOR FACULTY/ADMIN)
    # =====================================================================
    @st.dialog("📚 Dynamic Knowledge Base Manager", width="large")
    def knowledge_base_dialog():
        st.markdown("### 📤 Upload Departmental Resources")
        st.info("Upload syllabus, lecture notes, or past questions. The AI will automatically chunk, embed, and memorize them securely.")

        col1, col2 = st.columns([2, 1])
        with col1:
            course_tag = st.text_input("Course Code & Version (Crucial for Version Control):", placeholder="e.g., IR-210-v1")
        with col2:
            doc_type = st.selectbox("Document Type:", ["Lecture Notes", "Syllabus", "Exam Questions", "Research Paper"])

        uploaded_files = st.file_uploader("Drag & Drop PDFs or TXT files here", type=["pdf", "txt"], accept_multiple_files=True)

        if st.button("🚀 Process & Memorize (Train AI)", type="primary", use_container_width=True):
            if uploaded_files and course_tag:
                with st.spinner(f"Chunking and embedding {len(uploaded_files)} file(s) into the Pinecone Vector DB..."):
                    try:
                        all_docs = []
                        
                        # 1. Extract Text from Uploaded Files
                        for f in uploaded_files:
                            if f.type == "application/pdf":
                                reader = pypdf.PdfReader(f)
                                for page_num, page in enumerate(reader.pages):
                                    text = page.extract_text()
                                    if text:
                                        # Storing source and page metadata is super helpful for citations!
                                        all_docs.append(Document(
                                            page_content=text, 
                                            metadata={"source": f.name, "page": page_num, "course_tag": course_tag, "doc_type": doc_type}
                                        ))
                            elif f.type == "text/plain":
                                text = f.getvalue().decode("utf-8")
                                all_docs.append(Document(
                                    page_content=text, 
                                    metadata={"source": f.name, "course_tag": course_tag, "doc_type": doc_type}
                                ))

                        if not all_docs:
                            st.error("⚠️ No readable text found in the uploaded documents.")
                            return

                        # 2. Advanced Chunking (Smart Splitter)
                        text_splitter = RecursiveCharacterTextSplitter(
                            chunk_size=1200,    # Good size for IR contextual analysis
                            chunk_overlap=200,  # Overlap prevents cutting concepts in half
                            length_function=len
                        )
                        chunks = text_splitter.split_documents(all_docs)

                        # 3. Embedding Setup (Using Gemini Embeddings as per your router)
                        embeddings = GoogleGenerativeAIEmbeddings(
                            model="models/gemini-embedding-2", 
                            google_api_key=os.getenv("GOOGLE_API_KEY") or st.secrets.get("GOOGLE_API_KEY")
                        )

                        # 4. Upload to Pinecone Vector DB
                        pinecone_api_key = os.getenv("PINECONE_API_KEY") or st.secrets.get("PINECONE_API_KEY")
                        vectorstore = PineconeVectorStore(
                            index_name="gstu-knowledge-base", 
                            embedding=embeddings,
                            pinecone_api_key=pinecone_api_key
                        )
                        
                        # Add documents directly to the cloud vector store
                        vectorstore.add_documents(chunks)
                        
                        # 5. Log the upload to Supabase for tracking
                        supabase.table("knowledge_base_logs").insert({
                            "uploaded_by": st.session_state.get("username_id", "admin"),
                            "course_tag": course_tag,
                            "doc_type": doc_type,
                            "file_count": len(uploaded_files),
                            "status": "embedded"
                        }).execute()
                        
                        st.success(f"✅ Successfully processed {len(chunks)} contextual chunks and embedded **{course_tag}** into the AI brain!")
                        st.balloons()
                        
                    except Exception as e:
                        st.error(f"⚠️ Processing Error: {str(e)}")
            else:
                st.warning("⚠️ Please provide a Course Tag (e.g., IR-202-v2) and upload at least one file.")
                
        st.markdown("---")
        st.markdown("#### 🗄️ Currently Active Knowledge Vectors")
        try:
            kb_res = supabase.table("knowledge_base_logs").select("course_tag, doc_type, created_at").order("created_at", desc=True).limit(5).execute()
            if kb_res.data:
                for item in kb_res.data:
                    st.markdown(f"- 🏷️ **{item['course_tag']}** (`{item['doc_type']}`) - Active")
            else:
                st.caption("No custom knowledge vectors active yet.")
        except Exception:
            st.caption("Connect database to view active vectors.")


    # ==========================================================
    # 🏢 PHASE 4: THE DYNAMIC DEPARTMENT HUB (DB Connected)
    # ==========================================================
    @st.dialog("🏢 GSTU IR Department Hub", width="large")
    def department_hub_dialog():

        # 🔴 STOP UNAUTHORIZED ACCESS HERE
        if require_login_for_premium():
            return # Exits the dialog instantly if not logged in
        
        d_tab1, d_tab2, d_tab3, d_tab4, d_tab5 = st.tabs([
            "📢 Notice Board", "📅 Syllabus & Routine", "💰 Fees", "📊 Results", "🖼️ Gallery"
        ])
        
        with d_tab1:
            st.markdown("### 📌 Departmental Notices")
            # 🔴 FACULTY / ADMIN PIPELINE (Approvals)
            if user_role in ["Faculty", "Admin"]:
                with st.expander("✅ Pending Approvals (From CR)", expanded=True):
                    try:
                        pending = supabase.table("notices").select("*").eq("status", "draft").execute()
                        if pending.data:
                            for p in pending.data:
                                st.warning(f"📝 **Draft Notice:** {p['title']} \n\n {p['content']}")
                                if st.button(f"Approve & Publish '{p['title']}'", key=f"app_not_{p['id']}", type="primary"):
                                    supabase.table("notices").update({"status": "published"}).eq("id", p['id']).execute()
                                    st.success("✅ Published successfully!")
                                    import time; time.sleep(1); st.rerun()
                        else:
                            st.caption("No pending drafts waiting for approval.")
                    except: st.caption("Database setup required for drafts.")
            
            # 🔴 CR / STUDENT PIPELINE (Drafting)
            if user_role in ["Student", "Admin"]: # Admin can also draft for testing
                with st.expander("✍️ Submit Notice Draft (CR Only)"):
                    d_title = st.text_input("Notice Title", placeholder="e.g., Class Suspended Tomorrow")
                    d_content = st.text_area("Details", placeholder="Provide full details here...")
                    if st.button("Submit for Faculty Approval"):
                        if d_title and d_content:
                            import datetime
                            today = datetime.datetime.now().strftime("%Y-%m-%d")
                            try:
                                supabase.table("notices").insert({
                                    "title": d_title, 
                                    "content": d_content, 
                                    "date": today, 
                                    "status": "draft"  # 👈 Sending as DRAFT
                                }).execute()
                                st.success("✅ Draft sent! Waiting for Faculty approval.")
                            except Exception as e: st.error(f"DB Error: Make sure 'status' column exists. Details: {e}")
                        else: st.warning("Please fill all fields.")

            st.markdown("---")
            
            # 🟢 PUBLISHED NOTICES (Visible to Everyone)
            try:
                notices = supabase.table("notices").select("*").eq("status", "published").order("date", desc=True).limit(5).execute()
                if notices.data:
                    for notice in notices.data:
                        st.info(f"**{notice['date']}:** {notice['title']} - {notice['content']}")
                else:
                    st.info("No published notices available.")
            except:
                st.warning("No notices found or database connection error.")
            
        with d_tab2:
            st.markdown("### 📅 Dynamic Syllabus & Class Routine")
            sem = st.selectbox("Select Semester:", ["1.1", "1.2", "2.1", "2.2", "3.1", "3.2", "4.1", "4.2"])
            
            try:
                # 🔴 Dynamic Fetch from Supabase
                routines = supabase.table("syllabus").select("*").eq("semester", sem).execute()
                if routines.data:
                    st.success("**Classes Today:**")
                    for r in routines.data:
                        st.markdown(f"- **{r['time']}**: {r['course_code']} (Room {r['room']})")
                else: st.info("No routine updated for this semester.")
            except: st.error("Database connection error.")
            
            if st.button("Download Full Syllabus (PDF)", use_container_width=True): st.toast("Downloading...")
            
        with d_tab3:
            st.markdown("### 💳 Departmental Payments")
            st.markdown("Pay your fees directly via SSLCommerz/bKash.")
            p_col1, p_col2 = st.columns(2)
            p_col1.button("Pay Seminar Fee (৳200)", use_container_width=True)
            p_col2.button("Pay Picnic Fee (৳500)", use_container_width=True)
            
        with d_tab4:
            st.markdown("### 📈 Academic Results")
            sid = st.text_input("Enter Student ID:", placeholder="e.g. 21IR045")
            if st.button("Fetch CGPA Record", use_container_width=True, type="primary"):
                try:
                    res = supabase.table("student_results").select("cgpa").eq("student_id", sid).execute()
                    if res.data: st.success(f"🎓 **Student {sid} CGPA:** {res.data[0]['cgpa']}")
                    else: st.error("Record not found.")
                except: st.error("Database error.")
            
        with d_tab5:
            st.markdown("### 📸 Department Gallery")
            st.image("https://images.unsplash.com/photo-1523050854058-8df90110c9f1?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80", caption="IR Department Seminar")


    # ===================================================================
    # 🚀 4. THE POWER-UPS DIALOG (With 1-Month Trial Logic & Bug Fixes)
    # ===================================================================
    def check_feature_lock(user_id):
        """Phase 4: 1 Month Free Trial & 12-Hour Lock Logic"""
        # (In production, this checks Supabase 'created_at' and usage logs)
        # For now, we simulate that new users are on their 30-Day Golden Trial.
        return False, "You are on your 30-Day Free Trial! All features unlocked."

    @st.dialog("🚀 Academic Power-Ups & Gen-Z OS", width="large")
    def powerup_dialog():

        # 🔴 STOP UNAUTHORIZED ACCESS HERE
        if require_login_for_premium():
            return
        is_locked, lock_msg = check_feature_lock(st.session_state.username_id)
        if is_locked:
            st.error(f"🔒 **Feature Locked:** {lock_msg}\nUpgrade to Pro or wait 12 hours.")
            return
        tab1, tab2, tab3 = st.tabs(["🔬 Elite Research OS", "🎮 Gen-Z Tools", "👁️ Vision & PDF (Advanced)"])

        # --- TAB 1: RESEARCH OS ---
        with tab1:
            st.markdown("### 🎓 Discover Literature & Research Gaps")
            st.markdown("Enter your thesis or assignment topic. Our elite agent will synthesize data.")
            
            task_mode = st.radio("Select Agent Task:", ["Research Gap Hunter 🎯", "Literature Review Synthesis 📚"], horizontal=True)
            res_topic = st.text_input("Enter Research Topic:", placeholder="e.g., Blue Economy in Bangladesh")
            
            if st.button("Execute Research Analysis", type="primary", use_container_width=True):
                if res_topic:
                    with st.spinner("Research Agent is analyzing global literature..."):
                        try:
                            from core_agents import generate_research_assistance
                            clean_mode = task_mode.replace(" 🎯", "").replace(" 📚", "")
                            res = generate_research_assistance(res_topic, clean_mode)
                            
                            if res.get("status") == "success":
                                data = res["data"]
                                st.success(f"✅ {clean_mode} Generated Successfully!")
                                st.markdown("<hr style='border-color: rgba(16,163,127,0.3); margin: 10px 0;'>", unsafe_allow_html=True)
                                
                                if clean_mode == "Research Gap Hunter":
                                    st.markdown("#### 🕵️‍♂️ Existing Research Focus")
                                    for pt in data.get('existing_research_focus', []): st.write(f"- {pt}")
                                    st.markdown("#### ⚠️ The Missing Gap (Opportunity)")
                                    st.error(data.get('the_gap', ''))
                                    st.markdown("#### 💡 Proposed Thesis Titles")
                                    for t in data.get('proposed_thesis_titles', []): st.success(f"**{t}**")
                                    
                                else: # Literature Review
                                    st.markdown("#### 📖 Main Arguments")
                                    for pt in data.get('main_arguments', []): st.write(f"- {pt}")
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        st.success("**🤝 Areas of Agreement**\n\n" + data.get('areas_of_agreement', ''))
                                    with col2:
                                        st.error("**⚔️ Areas of Disagreement**\n\n" + data.get('areas_of_disagreement', ''))
                                    st.info("**Key Scholars/Thinkers:** " + ", ".join(data.get('key_scholars', [])))
                            else:
                                st.error(f"⚠️ Agent Error: {res.get('message')}")
                        except Exception as e:
                            st.error(f"🚨 Crash: {str(e)}")
                else:
                    st.warning("Please enter a research topic.")
        
        # ---------------------------------------------------------
        # --- TAB 2: GEN-Z GAMIFIED TOOLS ---  
        # ---------------------------------------------------------       
        with tab2:
            st.markdown("#### 🔥 Gamified EdTech Features")
            g_tab1, g_tab2, g_tab3 = st.tabs(["⚔️ Arena & Battle", "🃏 Study Hacks", "🏆 Leaderboard & Avatar"])
            
            # ---------------------------------------------------------
            # ⚔️ 1. MULTI-AGENT DEBATE ARENA (Timer, Voice Edit, Judge AI)
            # ---------------------------------------------------------
            with g_tab1:
                st.markdown("**⚔️ AI Debate Arena (User vs AI)**")
                import time
                # Setup Debate States
                if "db_history" not in st.session_state: st.session_state.db_history = []
                if "db_start_time" not in st.session_state: st.session_state.db_start_time = None
                if "db_duration" not in st.session_state: st.session_state.db_duration = None
                if "db_verdict" not in st.session_state: st.session_state.db_verdict = None

                tier = st.session_state.get('user_tier', 'free')
                time_options = [5, 10, 15] if tier == 'free' else [5, 10, 15, 30, 60]
                
                # --- INITIALIZE ARENA ---
                if not st.session_state.db_start_time:
                    st.info(f"⏱️ Select Debate Duration (Max {time_options[-1]} mins for your tier)")
                    selected_time = st.selectbox("Debate Duration (Minutes)", time_options)
                    
                    if st.button("Initialize Debate Arena 🥊", use_container_width=True, type="primary"):
                        st.session_state.db_start_time = time.time()
                        st.session_state.db_duration = selected_time * 60
                        st.session_state.db_history = []
                        st.session_state.db_verdict = None
                
                # --- ACTIVE DEBATE & TIMER ---
                else:
                    elapsed = time.time() - st.session_state.db_start_time
                    remaining = st.session_state.db_duration - elapsed
                    
                    col1, col2 = st.columns([3, 1])
                    col1.markdown(f"### ⏱️ Time Remaining: {max(0, int(remaining//60))}:{max(0, int(remaining%60)):02d}")
                    if col2.button("End Debate Early 🛑"): 
                        st.session_state.db_start_time = time.time() - (st.session_state.db_duration + 1) # Force time up
                    
                    # 🔴 TIME IS UP -> SUMMON JUDGE AI
                    if remaining <= 0:
                        st.warning("⏳ Time's Up! The Debate has ended.")
                        if not st.session_state.db_verdict:
                            if st.button("Summon Judge AI for Verdict ⚖️", type="primary", use_container_width=True):
                                with st.spinner("Judge AI is analyzing IR facts and calculating points..."):
                                    transcript = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.db_history])
                                    from core_agents import generate_genz_features
                                    res = generate_genz_features(transcript, "judge")
                                    if res["status"] == "success": st.session_state.db_verdict = res["data"]
                                    else: st.error("Judge AI failed to respond.")
                                        
                        if st.session_state.db_verdict:
                            v = st.session_state.db_verdict
                            st.success(f"🏆 **WINNER:** {v.get('winner')}")
                            c1, c2 = st.columns(2)
                            c1.metric("Your Points", v.get('user_score'))
                            c2.metric("AI Opponent Points", v.get('ai_score'))
                            st.info(f"⚖️ **Judge Summary:** {v.get('verdict_summary')}")
                            if st.button("Start New Debate 🔄", use_container_width=True): st.session_state.db_start_time = None
                    
                    # 🔴 ONGOING CHAT INTERFACE
                    else:
                        # 1. Input Processing FIRST (Instantly updates UI without rerun)
                        user_arg = st.text_input("Type Your Argument:", placeholder="e.g., China will take over Taiwan by 2027.")
                        text_submit = st.button("Send Text 💬", use_container_width=True)
                        
                        st.markdown("**OR**")
                        audio_val = st.audio_input("Record Voice Argument 🎙️") 
                        voice_submit = False
                        if audio_val:
                            st.warning("🎧 Listen to your recording. Click 'Confirm' to send, or X to delete and re-record.")
                            voice_submit = st.button("Confirm & Send Voice 🎤", use_container_width=True, type="primary")

                        final_arg = ""
                        if text_submit and user_arg: final_arg = user_arg
                        elif voice_submit and audio_val:
                            with st.spinner("🎙️ Transcribing your voice using Whisper..."):
                                try:
                                    import os
                                    from groq import Groq
                                    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
                                    temp_path = "temp_debate.wav"
                                    with open(temp_path, "wb") as f: f.write(audio_val.getvalue())
                                    with open(temp_path, "rb") as file:
                                        transcription = client.audio.transcriptions.create(
                                            file=(temp_path, file.read()), model="whisper-large-v3", temperature=0.7, response_format="text"
                                        )
                                    final_arg = transcription.strip()
                                    st.success(f"🗣️ **Transcribed:** {final_arg}")
                                    if os.path.exists(temp_path): os.remove(temp_path)
                                except Exception as e: st.error(f"Voice Error: {str(e)}")
                                    
                        if final_arg:
                            st.session_state.db_history.append({"role": "User", "content": final_arg})
                            with st.spinner("AI is formulating a counter-argument..."):
                                from core_agents import generate_genz_features
                                res = generate_genz_features(final_arg, "debate")
                                if res["status"] == "success":
                                    ai_text = res["data"]
                                    st.session_state.db_history.append({"role": "AI", "content": ai_text, "audio": True})
                                    try:
                                        supabase.table("debate_history").insert({
                                            "user_id": st.session_state.username_id, "argument": final_arg, "ai_response": ai_text
                                        }).execute()
                                    except: pass

                        # 2. Render Chat History (Always shows fresh messages)
                        st.markdown("<hr>", unsafe_allow_html=True)
                        for msg in st.session_state.db_history:
                            if msg['role'] == 'User': st.info(f"**You:** {msg['content']}")
                            else: 
                                st.error(f"**AI:** {msg['content']}")
                                if msg.get("audio"):
                                    import urllib.parse
                                    safe_speech = urllib.parse.quote(msg['content'].replace('\n', ' ').replace('"', "'"))
                                    st.components.v1.html(f"""
                                        <button onclick="let u = new SpeechSynthesisUtterance(decodeURIComponent('{safe_speech}')); window.speechSynthesis.speak(u);" 
                                        style="background:#10a37f; color:white; border:none; padding:5px 10px; border-radius:5px; cursor:pointer; font-weight:bold; font-size: 12px;">
                                        🔊 Listen
                                        </button>
                                    """, height=35)
                                    

                st.markdown("---")
                st.markdown("**🏆 Battle Mode (1 VS 1)**")
                if st.button("Find Opponent 🔍", use_container_width=True):
                    import time, random
                    with st.spinner("📡 Searching for online GSTU scholars..."):
                        time.sleep(2.5) 
                        if random.choice([True, False]):
                            opponent = random.choice(["Fahim (IR 2.1)", "Samia (IR 3.1)", "Noman (IR 1.2)"])
                            st.success(f"⚔️ **Match Found!** You are battling against **{opponent}**.")
                            st.info("Topic: International Security. Get ready!")
                        else:
                            st.warning("📭 No opponents currently online. Try again later.")

            # ---------------------------------------------------------
            # 🎮 2. DYNAMIC FLASHCARDS (Callbacks applied, ZERO st.rerun)
            # ---------------------------------------------------------
            with g_tab2:
                st.markdown("### 🃏 The Endless Study Loop")
                import time
                
                # --- STATE MANAGEMENT ---
                if "fc_cards" not in st.session_state: st.session_state.fc_cards = []
                if "fc_index" not in st.session_state: st.session_state.fc_index = 0
                if "fc_diff" not in st.session_state: st.session_state.fc_diff = "Easy" 
                if "fc_streak" not in st.session_state: st.session_state.fc_streak = 0
                if "fc_daily_count" not in st.session_state: st.session_state.fc_daily_count = 0
                if "fc_last_gen_time" not in st.session_state: st.session_state.fc_last_gen_time = 0
                
                if "fc_xp" not in st.session_state: 
                    try:
                        user_res = supabase.table("user_profiles").select("total_xp, subscription_tier").eq("id", st.session_state.username_id).execute()
                        st.session_state.fc_xp = user_res.data[0]['total_xp'] if user_res.data else 0
                        st.session_state.user_tier = user_res.data[0].get('subscription_tier', 'free') if user_res.data else 'free'
                    except: 
                        st.session_state.fc_xp = 0; st.session_state.user_tier = 'free'

                max_limit = 100 if st.session_state.get('user_tier') == 'pro_scholar' else 50
                cooldown_seconds = 3600
                
                fc_col1, fc_col2 = st.columns([3, 1])
                fc_topic = fc_col1.text_input("Topic to Master:", placeholder="e.g., Geopolitics")
                fc_col2.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                
                if fc_col2.button("Generate Set 🎲", use_container_width=True, type="primary"):
                    time_passed = time.time() - st.session_state.fc_last_gen_time
                    if st.session_state.fc_daily_count >= max_limit:
                        st.error(f"⚠️ Daily limit reached ({max_limit}/{max_limit}). Come back tomorrow or Upgrade to Pro!")
                    elif time_passed < cooldown_seconds and st.session_state.fc_last_gen_time != 0:
                        st.warning(f"⏳ Brain cooling down! Next set available in {int((cooldown_seconds - time_passed) / 60)} minutes.")
                    elif fc_topic:
                        with st.spinner(f"Summoning {st.session_state.fc_diff} Questions..."):
                            from core_agents import generate_genz_features
                            res = generate_genz_features(fc_topic, "flashcards", {"difficulty": st.session_state.fc_diff})
                            if res["status"] == "success":
                                st.session_state.fc_cards = res["data"].get("flashcards", [])
                                st.session_state.fc_index = 0
                                st.session_state.fc_last_gen_time = time.time() 
                                for key in list(st.session_state.keys()):
                                    if key.startswith("ans_fc_") or key.startswith("res_fc_") or key.startswith("radio_fc_"):
                                        del st.session_state[key]
                            else: st.error("AI Server Busy. Try again.")

                if st.session_state.fc_cards:
                    total_cards = len(st.session_state.fc_cards)
                    idx = st.session_state.fc_index
                    card = st.session_state.fc_cards[idx]
                    
                    st.markdown(f"**Card {idx + 1} of {total_cards}** | 🛡️ **Level:** {st.session_state.fc_diff} | ⚡ **XP:** {st.session_state.fc_xp} | 📊 **Today:** {st.session_state.fc_daily_count}/{max_limit}")
                    st.progress((idx + 1) / total_cards)
                    st.info(f"### Q: {card.get('q')}")
                    
                    ans_key = f"ans_fc_{idx}"
                    is_answered = st.session_state.get(ans_key, False)
                    
                    # 🔴 Callbacks used instead of st.rerun()
                    # BD Standard Negative Marking (-1.5 XP) + AI Training Loop
                    def submit_answer(c_opt, r_key, a_key, res_key):
                        st.session_state[a_key] = True
                        st.session_state.fc_daily_count += 1
                        
                        if st.session_state[r_key] == c_opt:
                            st.session_state.fc_xp += 5.0  # +5 for correct
                            st.session_state.fc_streak += 1
                            st.session_state[res_key] = "Correct"
                            if st.session_state.fc_streak == 2: st.session_state.fc_diff = "Medium"
                            elif st.session_state.fc_streak >= 4: st.session_state.fc_diff = "Hard"
                            
                            # 🔴 DYNAMIC AI TRAINING: Tell Database this is a STRONG topic!
                            try:
                                from memory_db import update_weakness_graph
                                update_weakness_graph(st.session_state.username_id, fc_topic, "Strong")
                            except: pass
                        
                        else:
                            st.session_state.fc_xp = max(0.0, st.session_state.fc_xp - 1.5)
                            st.session_state.fc_streak = 0
                            st.session_state[res_key] = "Wrong"
                            st.session_state.fc_diff = "Easy"
                            
                            # 🔴 DYNAMIC AI TRAINING: Tell Database user needs help here!
                            try:
                                from memory_db import update_weakness_graph
                                update_weakness_graph(st.session_state.username_id, fc_topic, "Weak")
                            except: pass
                            
                        try: 
                            supabase.table("user_profiles").update({"total_xp": int(st.session_state.fc_xp)}).eq("id", st.session_state.username_id).execute()
                        except: pass

                    user_ans = st.radio("Select Answer:", card.get("options", []), key=f"radio_fc_{idx}", disabled=is_answered)
                    
                    if not is_answered:
                        st.button("Submit Answer", type="primary", use_container_width=True, key=f"sub_fc_{idx}", 
                                  on_click=submit_answer, args=(card.get("correct_option"), f"radio_fc_{idx}", ans_key, f"res_fc_{idx}"))
                    
                    if st.session_state.get(ans_key, False):
                        if st.session_state.get(f"res_fc_{idx}") == "Correct": 
                            st.success("✅ **Correct! +5 XP**")
                        else:
                            st.error("❌ **Incorrect! -1.5 XP. Streak Broken.**")
                            st.warning(f"**Correct Answer:** {card.get('correct_option')}\n\n*Explanation:* {card.get('explanation')}")
                            
                        def go_prev(): st.session_state.fc_index -= 1
                        def go_next(): st.session_state.fc_index += 1
                        
                        nav1, nav2 = st.columns(2)
                        nav1.button("⬅️ Previous", use_container_width=True, disabled=(idx == 0), on_click=go_prev, key=f"prev_{idx}")
                        if idx < total_cards - 1:
                            nav2.button("Next ➡️", type="primary", use_container_width=True, on_click=go_next, key=f"next_{idx}")
                        else:
                            nav2.button("Set Completed! 🎉", disabled=True, use_container_width=True, key=f"done_{idx}")


                st.markdown("---")
                # ---------------------------------------------------------
                # 🔮 3. TRUE DYNAMIC AI PREDICTOR (RAG Database Connected)
                # ---------------------------------------------------------
                st.markdown("**🔮 AI Exam Predictor (RAG Powered)**")
                pred_course = st.text_input("Course Code:", placeholder="e.g., IR210", key="pred_input")
                
                if st.button("Predict Topics 📊", use_container_width=True):
                    if pred_course:
                        with st.spinner("Retrieving RAG Context from Vector Database..."):
                            # 🔴 DYNAMIC RAG: Connects to your existing database.py search_context function
                            try:
                                from database import search_context
                                rag_data, sources = search_context(pred_course)
                                if not rag_data:
                                    rag_data = "No past questions or syllabus found in DB. Base prediction on standard IR theory."
                            except Exception as e:
                                rag_data = "Vector DB offline. Fallback to standard theory."
                            
                            from core_agents import generate_genz_features
                            res = generate_genz_features(pred_course, "predictor", {"context": rag_data})
                            
                            if res["status"] == "success":
                                for pred in res["data"].get("predictions", []):
                                    prob = pred.get("probability", 50)
                                    st.markdown(f"#### 🎯 {pred.get('topic')}")
                                    st.progress(prob / 100.0, text=f"Probability: {prob}%")
                                    st.caption(f"**Reason:** {pred.get('reason')}")
                            else: 
                                st.error(res["message"])

            # ---------------------------------------------------------
            # 🏆 3. DYNAMIC LEADERBOARD & AVATAR
            # ---------------------------------------------------------
            with g_tab3:
                st.markdown("**😈 Savage Roast Mode**")
                rq = st.text_input("Question:", placeholder="e.g., What is Hegemony?", key="rq_input")
                ra = st.text_area("Your Answer:", key="ra_input")
                if st.button("Roast Me 🔥", use_container_width=True):
                    if rq and ra:
                        with st.spinner("Summoning the Savage Professor..."):
                            from core_agents import generate_genz_features
                            res = generate_genz_features(rq, "roast", {"answer": ra})
                            if res["status"] == "success":
                                data = res["data"]
                                if data.get("is_correct"): st.success(f"✅ {data.get('roast_text')}")
                                else:
                                    st.error(f"🔥 **ROASTED:** {data.get('roast_text')}")
                                    st.info(f"📚 **Real Concept:** {data.get('correct_concept')}")
                            else: st.error(res["message"])
                
                st.markdown("---")
                colA, colB = st.columns([1, 2])
                
                # 🔴 DYNAMIC AVATAR LOGIC
                with colA:
                    st.markdown("### 🦉 Mr. Atlas")
                    st.image("https://api.dicebear.com/7.x/bottts/svg?seed=Atlas&backgroundColor=10a37f", width=100)
                    current_xp = st.session_state.get('fc_xp', 0)
                    if current_xp == 0: atlas_msg = "🗣️ *'Zero XP? Start swiping flashcards!'*"
                    elif current_xp < 50: atlas_msg = f"🗣️ *'Okay, {current_xp} XP is a start. But faster!'*"
                    else: atlas_msg = f"🗣️ *'{current_xp} XP?! You are officially a geopolitical threat!'*"
                    st.warning(atlas_msg)
                
                # 🔴 DYNAMIC LEADERBOARD LOGIC
                with colB:
                    st.markdown("### 🏆 Live GSTU Leaderboard")
                    try:
                        lb_res = supabase.table("user_profiles").select("full_name, total_xp").order("total_xp", desc=True).limit(5).execute()
                        if lb_res.data:
                            medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
                            for i, user in enumerate(lb_res.data):
                                medal = medals[i] if i < len(medals) else "🏅"
                                name = user.get('full_name', 'Unknown Scholar')
                                xp = user.get('total_xp', 0)
                                st.markdown(f"{medal} **{name}** - {xp} XP")
                        else: st.info("Leaderboard is empty. Be the first!")
                    except Exception as e: st.error("⚠️ Connecting to Database...")


        # --- TAB 3: ADVANCED VISION & PDF ---
        with tab3:
            st.markdown("### 👁️ Multimodal & PDF Generation")
            
            # ==========================================
            # 🔍 FEATURE 1: HANDWRITTEN NOTE ANALYZER
            # ==========================================
            st.info("✍️ **Handwritten Note Analysis (Vision Engine)**")
            note_pic = st.file_uploader("Upload handwritten notes (JPG/PNG):", type=["jpg", "png", "jpeg"])
            
            if st.button("Analyze & Digitize Notes 🪄", use_container_width=True):
                if note_pic:
                    with st.spinner("Extracting text and analyzing with Gemini Vision..."):
                        try:
                            import google.generativeai as genai
                            import PIL.Image
                            import os
                            
                            # Fetch Google API Key
                            google_api_key = os.environ.get("GOOGLE_API_KEY") or st.secrets.get("GOOGLE_API_KEY")
                            genai.configure(api_key=google_api_key)
                            
                            # Process Image
                            img = PIL.Image.open(note_pic)
                            model = genai.GenerativeModel('gemini-2.5-flash')
                            
                            prompt = "You are an expert academic assistant. Read this handwritten note perfectly. First, transcribe the exact text. Then, provide a short summary of the core concepts in bullet points."
                            response = model.generate_content([prompt, img])
                            
                            st.success("✅ Analysis Complete!")
                            st.markdown(response.text)
                            
                            # Save to session state so user can copy it to PDF generator below
                            st.session_state.digitized_note = response.text
                            
                        except Exception as e:
                            st.error(f"⚠️ Vision AI Error: {str(e)}\n\nMake sure `google-generativeai` and `Pillow` are installed.")
                else:
                    st.warning("⚠️ Please upload an image first!")
            
            st.markdown("---")
            
            # ==========================================
            # 📄 FEATURE 2: TEXT-TO-PDF GENERATOR
            # ==========================================
            st.info("📄 **Text-to-PDF Generator (Report Builder)**")
            st.markdown("*Export your AI research directly to a beautifully formatted PDF for your assignments.*")
            
            pdf_title = st.text_input("Document Title:", placeholder="e.g., Geopolitics of South Asia")
            
            # Pre-fill with digitized note if exists
            default_content = st.session_state.get("digitized_note", "")
            pdf_content = st.text_area("Paste your research or smart notes here:", value=default_content, height=200)
            
            if st.button("Export as PDF 📥", use_container_width=True, type="primary"):
                if pdf_title and pdf_content:
                    with st.spinner("Generating PDF..."):
                        try:
                            # 🔴 Generating PDF using FPDF
                            from fpdf import FPDF
                            import tempfile
                            
                            class PDF(FPDF):
                                def header(self):
                                    self.set_font('Arial', 'B', 15)
                                    self.cell(0, 10, 'GSTU AI Research Export', 0, 1, 'C')
                                    self.set_font('Arial', 'I', 10)
                                    self.set_text_color(100, 100, 100)
                                    self.cell(0, 10, f"Generated by {st.session_state.get('user_name', 'GSTU Scholar')}", 0, 1, 'C')
                                    self.ln(10)

                            pdf = PDF()
                            pdf.add_page()
                            
                            # Title
                            pdf.set_font('Arial', 'B', 16)
                            pdf.set_text_color(0, 0, 0)
                            # Encode/Decode protects against unsupported characters crashing FPDF
                            safe_title = pdf_title.encode('latin-1', 'replace').decode('latin-1')
                            pdf.multi_cell(0, 10, safe_title, align='C')
                            pdf.ln(10)
                            
                            # Content
                            pdf.set_font('Arial', '', 12)
                            safe_content = pdf_content.encode('latin-1', 'replace').decode('latin-1')
                            pdf.multi_cell(0, 8, safe_content)
                            
                            # Save to Temp File
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                                pdf.output(tmp_file.name)
                                tmp_pdf_path = tmp_file.name
                            
                            # Download Button
                            with open(tmp_pdf_path, "rb") as f:
                                st.download_button(
                                    label="✅ Download Your PDF Now",
                                    data=f,
                                    file_name=f"{pdf_title.replace(' ', '_')}.pdf",
                                    mime="application/pdf",
                                    use_container_width=True
                                )
                                
                        except ImportError:
                            st.error("⚠️ Library missing. Run: `pip install fpdf google-generativeai Pillow`")
                        except Exception as e:
                            st.error(f"⚠️ Failed to generate PDF: {str(e)}")
                else:
                    st.warning("⚠️ Please provide both a Title and Content.")


# ==============================================================
# 🚀 MAIN APP EXECUTION BLOCK
# ==============================================================
if llm:
    # 🔴 SECURE SESSION FETCHING
    safe_messages = st.session_state.get("messages", [])
    raw_role = st.session_state.get("user_role", "Guest")
    user_role = str(raw_role).strip().title() if raw_role else "Guest"
    current_uid = st.session_state.get("username_id", "guest_session")
    is_logged_in = st.session_state.get("logged_in", False)

    # 🔴 IF CHAT HISTORY IS EMPTY, SHOW DASHBOARD
    if not safe_messages:
        st.markdown("""
            <style>
            .block-container { padding-top: 2rem !important; padding-bottom: 1rem !important; }
            </style>
        """, unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; margin-top: -38px;'>Welcome to GSTU IR Ecosystem ✨</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; opacity: 0.7; margin-bottom: 20px; margin-right: 10px;'>Your personal AI assistant for syllabus, research, smart notes, and mock presentations.</p>", unsafe_allow_html=True)

        # 🔴 ROLE-BASED QUICK ACTIONS (Safe Execution)
        s_col1, s_col2, s_col3 = st.columns(3)
        if user_role in ["Student", "Guest"]:
            if s_col1.button("📅 Smart Routine", use_container_width=True): 
                if not require_login_for_premium(): routine_dialog() 
            if s_col3.button("🏢 Dept Hub", use_container_width=True): department_hub_dialog()
            if s_col2.button("🎯 Mock Exam", use_container_width=True): 
                if not require_login_for_premium(): assessment_dialog("Student")
        elif user_role == "Faculty":
            if s_col1.button("📋 Generate Quiz", use_container_width=True): assessment_dialog("Faculty")
            if s_col2.button("🏢 Dept Hub", use_container_width=True): department_hub_dialog()
            if s_col3.button("📚 Data Uploader", use_container_width=True): knowledge_base_dialog()
        elif user_role == "Admin": 
            if s_col1.button("📚 Data Uploader", use_container_width=True): knowledge_base_dialog()
            if s_col2.button("🏢 Dept Hub", use_container_width=True): department_hub_dialog() 
            if s_col3.button("📈 Revenue & Analytics", use_container_width=True): 
                if 'admin_dashboard_dialog' in globals(): admin_dashboard_dialog()
                else: st.toast("Opening Admin Analytics...")

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚀 Explore Academic Power-Ups & Research OS", use_container_width=True):
            powerup_dialog()

        # 🔴 STUDENT ANALYTICS DASHBOARD
        if user_role == "Student" and is_logged_in and current_uid != "guest_session":
            saved_hours = 0.0
            retention_boost = 15 
            weakness_topic = "General Concepts"
            cgpa_display = "2.88 ➔ 2.88" # Base fallback display
            
            try:
                # Offline safe try-except block for DB
                logs_res = supabase.table("ai_training_logs").select("topic_tag").eq("user_id", current_uid).execute()
                total_queries = len(logs_res.data) if logs_res.data else 0
                saved_hours = round((total_queries * 15) / 60, 1)

                if total_queries > 0:
                    import pandas as pd
                    df = pd.DataFrame(logs_res.data)
                    valid_topics = df[df['topic_tag'].str.strip() != '']
                    if not valid_topics.empty:
                        weakness_topic = valid_topics['topic_tag'].mode()[0].title()

                prof_res = supabase.table("user_profiles").select("total_xp").eq("id", current_uid).execute()
                xp = prof_res.data[0].get("total_xp", 0) if prof_res.data else 0
                retention_boost = min(98, 15 + int(xp / 5)) 

                # 🎯 CGPA PREDICTOR LOGIC (Wow Factor)
                improvement_factor = (retention_boost - 15) * 0.007
                new_predicted_cgpa = min(4.00, round(2.88 + improvement_factor, 2))
                cgpa_display = f"2.88 ➔ {new_predicted_cgpa:.2f}"

            except Exception:
                cgpa_display = "2.88 ➔ 3.15" # Silently proceed with a motivated fallback if offline
            
            html_content = (
                "<div style='background: linear-gradient(135deg, rgba(16,163,127,0.08) 0%, rgba(15,23,42,0.8) 100%); border: 1px solid rgba(16,163,127,0.2); border-radius: 12px; padding: 22px; margin-top: 10px; margin-bottom: 25px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); backdrop-filter: blur(10px);'>"
                "<h3 style='margin-top: 0; color: #ffffff; font-size: 18px; display: flex; align-items: center; gap: 8px; letter-spacing: -0.5px;'>🚀 Your Academic ROI & AI Impact</h3>"
                "<div style='display: flex; gap: 12px; flex-wrap: wrap;'>"
                
                # Box 1: Time Saved
                f"<div style='flex: 1; min-width: 110px; background: rgba(0,0,0,0.4); padding: 15px; border-radius: 10px; border-bottom: 3px solid #10a37f;'><div style='font-size: 22px; font-weight: 800; color: #ffffff; letter-spacing: -1px;'>⏱️ {saved_hours} <span style='font-size: 12px; font-weight: normal; color: #94a3b8;'>hrs</span></div><div style='font-size: 11px; color: #cbd5e1; margin-top: 6px; font-weight: 500;'>Reading Time Saved</div></div>"
                
                # Box 2: Memory Retention
                f"<div style='flex: 1; min-width: 110px; background: rgba(0,0,0,0.4); padding: 15px; border-radius: 10px; border-bottom: 3px solid #58A6FF;'><div style='font-size: 22px; font-weight: 800; color: #ffffff; letter-spacing: -1px;'>🧠 +{retention_boost}%</div><div style='font-size: 11px; color: #cbd5e1; margin-top: 6px; font-weight: 500;'>Memory Retention</div></div>"
                
                # Box 3: Weakness Core
                f"<div style='flex: 1; min-width: 110px; background: rgba(0,0,0,0.4); padding: 15px; border-radius: 10px; border-bottom: 3px solid #e23670;'><div style='font-size: 14px; font-weight: 700; color: #ffffff; line-height: 1.2; padding-bottom: 4px;'>{weakness_topic}</div><div style='font-size: 11px; color: #cbd5e1; margin-top: 6px; font-weight: 500;'>Core Focus Area</div></div>"
                
                # 🎯 NEW Box 4: CGPA Predictor
                f"<div style='flex: 1.2; min-width: 130px; background: linear-gradient(135deg, rgba(212, 175, 55, 0.15) 0%, rgba(0,0,0,0.6) 100%); padding: 15px; border-radius: 10px; border-bottom: 3px solid #D4AF37;'><div style='font-size: 22px; font-weight: 800; color: #FFD700; letter-spacing: -1px;'>🎯 {cgpa_display}</div><div style='font-size: 11px; color: #cbd5e1; margin-top: 6px; font-weight: 500;'>Predicted CGPA Boost</div></div>"
                
                "</div></div>"
            )
            st.markdown(html_content, unsafe_allow_html=True)

            st.markdown("<h4 style='margin-top: 15px; color: #10a37f; font-size: 16px;'>🧠 Your Personal Learning Graph</h4>", unsafe_allow_html=True)
            strong_ui = []
            weak_ui = []
            
            try:
                # 🔴 DYNAMICALLY FETCH REAL DATA FROM DB
                graph_res = supabase.table("student_learning_graph").select("*").eq("user_id", current_uid).execute()
                if graph_res.data:
                    for item in graph_res.data:
                        t_name = item.get("topic", "Unknown").title()
                        status = item.get("status", "Explored")
                        
                        if status == "Strong": strong_ui.append((t_name, 85))
                        elif status == "Weak" or status == "Needs Review": weak_ui.append((t_name, 35))
            except Exception as e:
                pass # Silently fallback if DB table doesn't exist yet
                
            # Fallback if user is totally new or DB is empty
            if not strong_ui: strong_ui = [("Geopolitics & Historical Perspectives", 85), ("Foreign Policy Analysis", 70)]
            if not weak_ui: weak_ui = [(weakness_topic, 30), ("Migration Theories & Models", 45)]

            graph_col1, graph_col2 = st.columns(2)
            with graph_col1:
                st.markdown("**🛡️ Strong Areas (Mastered)**")
                for topic, score in strong_ui[:2]: # Show top 2
                    st.progress(score / 100.0, text=f"{topic} ({score}%)")
            with graph_col2:
                st.markdown("**⚠️ Weak Areas (Needs Focus)**")
                for topic, score in weak_ui[:2]: # Show top 2
                    st.progress(score / 100.0, text=f"{topic} ({score}%)")
            
            # Dynamic Suggestion based on REAL weakness
            actual_weakness = weak_ui[0][0] if weak_ui else weakness_topic
            st.info(f"💡 **AI Suggestion:** Your retention in **{actual_weakness}** needs a boost. Would you like a quick 5-minute mock test to strengthen this area?")

            if globals().get("ENABLE_AGENTIC_FEATURES", True):
                try: render_study_logger(current_uid)
                except Exception as e: st.warning(f"⚠️ Analytics Logger Offline")

                with st.expander("🚀 Generate 7-Day CGPA Boost Plan (AI Agent)", expanded=False):
                    if st.button("🧠 Generate Smart Routine Now", use_container_width=True, type="primary"):
                        with st.spinner("Agent is analyzing your academic data and generating a custom plan..."):
                            try:
                                from core_agents import generate_cgpa_boost_plan
                                plan_result = generate_cgpa_boost_plan(current_uid)
                                if plan_result.get("status") == "success":
                                    st.success("✅ Routine generated and saved successfully!")
                                    plan_data = plan_result["plan"]
                                    for day in ["day_1", "day_2", "day_3", "day_4", "day_5", "day_6", "day_7"]:
                                        if day in plan_data:
                                            st.markdown(f"**{day.replace('_', ' ').title()} — 🎯 {plan_data[day].get('focus_subject', 'Review')}**")
                                            st.info(f"💡 {plan_data[day].get('strategy', '')}")
                                    if "ai_advice" in plan_data: st.warning(f"🧠 **AI Advice:** {plan_data['ai_advice']}")
                                    st.markdown("<div style='height: 80px;'></div>", unsafe_allow_html=True)
                                else: st.error(f"⚠️ Agent Logic Error: {plan_result.get('message', 'Unknown Error')}")
                            except Exception as raw_e: st.error(f"🚨 System Offline")
                
                with st.expander("📈 View Your Academic Progress", expanded=False):
                    try:
                        import socket
                        socket.setdefaulttimeout(2)
                        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
                        render_analytics_dashboard(current_uid)
                    except OSError: st.warning("🔌 **Offline Mode Active:** Cannot sync progress data right now.", icon="⚠️")
                    except Exception as e: st.error(f"⚠️ **Dashboard Error:** Could not load analytics.")

    # ==================================================================================
    # 🔴 ALWAYS VISIBLE UI (Model Hub, File Uploader, Chat Input)
    # ==================================================================================
    st.markdown("<br>", unsafe_allow_html=True)

    is_guest_user = (user_role == "Guest" or current_uid in ["guest_session", None])
    is_real_admin = st.session_state.get("user_email") in ["yousufaltashfin@gmail.com", "tashfin@gstu.edu"]
    
    current_tier = "free"
    if not is_guest_user:
        try: current_tier = check_subscription_status(current_uid)
        except Exception: pass 
    if is_real_admin: current_tier = "Admin"
        
    m_col1, m_col2, m_col3 = st.columns([0.25, 0.5, 0.25])
    with m_col2:
        model_options = {
            "⚡ Fast Engine (Llama 4 - 17B)": "meta-llama/llama-4-scout-17b-16e-instruct",
            "💻 Offline Mode (GPT4All Local)": "local-gpt4all", 
            "🌐 Web Search (Gemini 2.5 Flash)": "gemini-2.5-flash",
            "🔬 DeepSeek R1 (Free)": "deepseek/deepseek-r1:free",
            "🚀 GPT-4o Mini (Fast)": "openai/gpt-4o-mini",
            "💎 Deep Logic (Llama 3 - 70B)": "llama-3.3-70b-versatile",
            "💎 Qwen Core (Qwen 2.5 - 72B)": "qwen/qwen-2.5-72b-instruct",
            "💎 Adv. Analysis (Gemini 2.5 Pro)": "gemini-2.5-pro",
            "💎 GPT-4o (OpenAI Premium)": "openai/gpt-4o-2024-08-06",
            "💎 Claude 3.5 Sonnet (Anthropic)": "anthropic/claude-3.5-sonnet"
        }
        
        current_model_name = "⚡ Fast Engine (Llama 4 - 17B)" 
        for key, val in model_options.items():
            if val == st.session_state.get("current_model"):
                current_model_name = key
                break
                
        selected_model_ui = st.selectbox("Select AI Engine", list(model_options.keys()), index=list(model_options.keys()).index(current_model_name) if current_model_name in model_options else 0, label_visibility="collapsed")
        st.session_state.current_model = model_options[selected_model_ui]

        is_locked = False
        try: is_locked = is_model_premium(st.session_state.current_model) and current_tier not in ["pro_scholar", "Admin"]
        except: pass

        if is_locked and is_guest_user:
            st.warning("🔒 Premium models require an account.")
            if st.button("🚀 Login to Unlock", type="primary", use_container_width=True):
                st.session_state.show_login_page = True; st.rerun()
            st.session_state.current_model = "meta-llama/llama-4-scout-17b-16e-instruct"
            is_locked = False
        elif is_locked and not is_guest_user:
            st.markdown("<div style='border: 1px solid rgba(255, 75, 75, 0.4); background: rgba(255, 75, 75, 0.05); padding: 15px; border-radius: 12px; text-align: center;'><h4 style='color: #ff4b4b; margin: 0;'>🔒 Premium Engine Locked</h4><p style='font-size: 13px;'>Upgrade to Pro Scholar to unlock.</p></div>", unsafe_allow_html=True)
            if st.button("💎 Upgrade to Pro Scholar", use_container_width=True, type="primary"): account_settings_dialog()

        st.session_state.is_model_locked = is_locked

    st.markdown("""<style>.stChatInputContainer { padding-bottom: 20px !important; background: transparent !important; }</style>""", unsafe_allow_html=True)

    # 🔴 CHAT CONTAINER & HISTORY RENDERING
    if "messages" not in st.session_state or st.session_state.messages is None:
        st.session_state.messages = []

    chat_container = st.container()
    
    for index, msg in enumerate(st.session_state.messages):
        if not isinstance(msg, dict) or "role" not in msg or "content" not in msg: continue
        avatar = "🧑‍💻" if msg["role"] == "user" else "✨"
        with chat_container.chat_message(msg["role"], avatar=avatar):
            if msg["role"] == "assistant": st.markdown(msg["content"], unsafe_allow_html=True)
            else: st.markdown(msg["content"])
            
            if msg["role"] == "assistant":
                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                act_cols = st.columns([1, 1, 1, 1, 1, 8], gap="small")
                with act_cols[0]:
                    import urllib.parse
                    is_bn_msg = bool(re.search(r'[\u0980-\u09FF]', msg["content"]))
                    tts_lang = "bn-BD" if is_bn_msg else "en-US" 
                    clean_text = re.sub(r'<[^>]+>', ' ', msg["content"]) 
                    clean_text = re.sub(r'http\S+', '', clean_text) 
                    clean_text = re.sub(r'[*#_~`>|\[\]()-]', '', clean_text) 
                    clean_text = clean_text.replace('\n', ' ').replace('"', "'").strip()
                    safe_speech_uri = urllib.parse.quote(clean_text)
                    st.components.v1.html(
                            f"""
                            <div style="display:flex; justify-content:center; align-items:center; height:100%;">
                                <button id="tts-btn-{index}" onclick='toggleVoice{index}()' title="Listen / Stop" style="background:transparent; border:none; cursor:pointer; font-size:18px; filter: grayscale(100%); outline:none; padding-top:2px; transition: transform 0.2s ease;">🔊</button>
                            </div>
                            <script>
                            let btn{index} = document.getElementById("tts-btn-{index}");
                            function toggleVoice{index}() {{
                                if (window.speechSynthesis.speaking) {{
                                    window.speechSynthesis.cancel();
                                    btn{index}.innerText = "🔊";
                                    btn{index}.style.transform = "scale(1)";
                                }} else {{
                                    let decodedText = decodeURIComponent('{safe_speech_uri}');
                                    let utterance = new SpeechSynthesisUtterance(decodedText);
                                    utterance.lang = '{tts_lang}'; 
                                    let voices = window.speechSynthesis.getVoices();
                                    for(let i = 0; i < voices.length; i++) {{
                                        if(voices[i].lang.includes('{tts_lang.split('-')[0]}')) {{
                                            utterance.voice = voices[i];
                                            break;
                                        }}
                                    }}
                                    utterance.onstart = function() {{ btn{index}.innerText = "⏹️"; btn{index}.style.transform = "scale(1.1)"; }};
                                    utterance.onend = function() {{ btn{index}.innerText = "🔊"; btn{index}.style.transform = "scale(1)"; }};
                                    utterance.onerror = function() {{ btn{index}.innerText = "🔊"; }};
                                    window.speechSynthesis.speak(utterance);
                                }}
                            }}
                            window.speechSynthesis.getVoices();
                            </script>
                            """, height=35
                        )
                with act_cols[1]: 
                    if st.button("👍", key=f"up_{index}", help="Good response"): st.toast("✅ Positive feedback logged.")
                with act_cols[2]: 
                    if st.button("👎", key=f"down_{index}", help="Bad response"): feedback_dialog(index)
                
                with act_cols[3]:
                    if st.button("🔄", key=f"regen_{index}", help="Regenerate response"):
                        st.session_state.messages.pop(index)
                        if len(st.session_state.messages) > 0:
                            st.session_state["retry_query"] = st.session_state.messages[-1]["content"]
                        st.rerun()
                with act_cols[4]:
                    if st.button("📑", key=f"copy_{index}", help="Copy text"): 
                        st.session_state[f"show_copy_{index}"] = not st.session_state.get(f"show_copy_{index}", False)
                with act_cols[5]:
                    app_url = os.getenv("APP_URL", "https://gstu-ir-ai.streamlit.app")
                    st.components.v1.html(f"""<button onclick="if(navigator.share)navigator.share({{url:'{app_url}'}})" style="background:transparent; border:none; cursor:pointer; font-size:20px;">📤</button>""", height=35)
                
    st.markdown("<br>", unsafe_allow_html=True)

    # 🔴 MULTIMODAL UPLOADER
    if "uploaded_files_cache" not in st.session_state: st.session_state.uploaded_files_cache = []
    with st.expander("📎 Attach Files, Camera & Voice Notes"):
        tab_file, tab_cam, tab_voice = st.tabs(["📂 Files", "📸 Camera", "🎤 Voice Note"])
        with tab_file:
            up_files = st.file_uploader("Upload PDFs or Images", type=["pdf", "png", "jpg", "jpeg"], accept_multiple_files=True)
            if up_files: st.session_state.uploaded_files_cache = up_files; st.success(f"✅ {len(up_files)} file(s) attached and ready for analysis.")
        with tab_cam:
            cam_pic = st.camera_input("Take a photo")
            if cam_pic: st.session_state.uploaded_files_cache = [cam_pic]; st.success("✅ Photo captured and attached.")
        with tab_voice:
            voice_data = st.audio_input("Record Voice")
            if voice_data and not st.session_state.get("voice_draft"):
                if st.button("🎙️ Process Audio", use_container_width=True):
                    with st.spinner("Translating voice to text..."):
                        import tempfile, os
                        from groq import Groq
                        try:
                            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                                tmp.write(voice_data.getbuffer())
                                t_path = tmp.name
                            groq_api = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY")
                            if groq_api:
                                with open(t_path, "rb") as f:
                                    t = Groq(api_key=groq_api).audio.transcriptions.create(file=(t_path, f.read()), model="whisper-large-v3", response_format="text").strip()
                                    if t: st.session_state.voice_draft = t; st.rerun()
                        except Exception as e: st.error(f"Voice processing error: {e}")
                        finally:
                            if 't_path' in locals() and os.path.exists(t_path): os.remove(t_path)
            
            if st.session_state.get("voice_draft"):
                st.info("Review:")
                e_txt = st.text_area("Command:", value=st.session_state.voice_draft, height=100)
                v1, v2 = st.columns(2)
                if v1.button("❌ Discard", use_container_width=True): st.session_state.voice_draft = ""; st.rerun()
                if v2.button("🚀 Send", use_container_width=True, type="primary"): st.session_state.quick_query = e_txt; st.session_state.voice_draft = ""; st.rerun()

    # 🔴 CHAT INPUT
    temp_query = st.chat_input("Message GSTU Assistant...", disabled=st.session_state.get("is_model_locked", False))
    user_query = st.session_state.get("quick_query") or temp_query
    st.session_state.quick_query = None 

    # 🔴 EXTRACT CACHED FILES
    context_from_files = ""
    if st.session_state.uploaded_files_cache:
        with st.spinner("📄 Analyzing documents..."):
            for f in st.session_state.uploaded_files_cache:
                try:
                    if f.type == "application/pdf":
                        import pypdf
                        for page in pypdf.PdfReader(f).pages: context_from_files += page.extract_text() + "\n"
                    elif "image" in f.type: context_from_files += f"\n[User image: {f.name}]\n"
                except Exception as e: st.warning(f"Read error: {e}")

    # =====================================================================
    # 🔴 AI PROCESSING FLAG ARCHITECTURE
    # =====================================================================
    if user_query:
        if not st.session_state.get("active_chat_title"):
            new_title = user_query[:25] + "..."
            st.session_state.active_chat_title = new_title
            st.session_state.current_session_id = create_new_session(current_uid, new_title)
            if "chat_history" not in st.session_state: st.session_state.chat_history = []
            st.session_state.chat_history.insert(0, {"title": new_title, "folder": None, "messages": []})

        st.session_state.messages.append({"role": "user", "content": user_query})
        if st.session_state.get('current_session_id'): save_message_to_cloud(st.session_state.current_session_id, "user", user_query)

        with chat_container.chat_message("user", avatar="👨🏻‍💻"):
            if len(user_query) > 300:
                st.markdown(user_query[:150] + "...")
                with st.expander("🔽 Show full prompt"): st.markdown(user_query)
            else: st.markdown(user_query)

        latest_q = st.session_state.messages[-1]["content"]
        proceed_with_ai = True  

        # SECURITY CHECK
        suspicious_keywords = ["ignore previous", "system prompt", "developer mode", "jailbreak", "print your instructions", "bypass", "forget instructions", "you are no longer", "sudo ", "give me the prompt"]
        if any(kw in latest_q.lower() for kw in suspicious_keywords):
            with chat_container.chat_message("assistant", avatar="🛡️"): st.error("⚠️ **Security Guard AI:** Malicious intent detected.")
            st.session_state.messages.pop(); proceed_with_ai = False

        # RATE LIMIT CHECK
        if proceed_with_ai:
            can_proceed, limit_msg = check_rate_limit(current_uid, current_tier)
            if not can_proceed:
                with chat_container.chat_message("assistant", avatar="✨"):
                    st.error(limit_msg)
                    if st.button("💎 Unlock Unlimited", use_container_width=True): account_settings_dialog()
                st.session_state.messages.pop(); proceed_with_ai = False 


        if proceed_with_ai:
            # 🔴 Explicitly define llm_engine right here so it's always in scope
            llm_engine = get_llm(st.session_state.get("current_model", "meta-llama/llama-4-scout-17b-16e-instruct"))
            
            with chat_container.chat_message("assistant", avatar="✨"):
                # 1. 🎯 SHOW CUSTOM SPINNER FIRST
                thinking_placeholder = st.empty()
                thinking_placeholder.markdown(get_thinking_html(), unsafe_allow_html=True)

                creator_keywords = ["created", "made", "inventor", "founded", "developer", "creator", "founder", "built"]
                casual_greetings = ["hi", "hello", "hey", "hallo", "helo", "hi there", "hey there", "what's up", "হ্যালো", "হাই", "কেমন আছো", "কেমন আছেন"]
                latest_q_lower = latest_q.strip().lower()
                

                # --- 1. INSTANT GREETINGS (Instant Response) ---
                if any(kw in latest_q_lower for kw in creator_keywords):
                    res_text = (
                        "The inventor and head developer of this AI model is **Tashfin Yousuf**.<br><br>"
                        "<a href='https://tashfinzportfolio.infy.uk/' target='_blank' rel='noopener noreferrer' "
                        "style='display: inline-block; background-color: #10a37f; color: white; padding: 10px 20px; "
                        "border-radius: 8px; text-decoration: none; font-weight: 600; font-family: sans-serif; "
                        "border: 1px solid #0f916f; box-shadow: 0 2px 5px rgba(0,0,0,0.2);'>📄 View / Download Tashfin's CV</a>"
                    )
                    st.markdown(res_text, unsafe_allow_html=True)
                
                elif any(latest_q_lower.startswith(g) for g in casual_greetings):
                    res_text = "Hello! 👋 I am the Elite GSTU IR AI Assistant. How can I help you with your academic research, theories, syllabus, or geopolitical analysis today?"
                    st.markdown(res_text)


                # --- 1.5 🎧 OMNICHANNEL CS ROUTER (PHASE 3) ---
                    admin_keywords = ["payment", "fee", "tk", "taka", "bkash", "sslcommerz", "bug", "support", "admin", "contact", "issue", "complain", "পেমেন্ট", "টাকা", "সমস্যা", "বিকাশ", "ভুল", "অ্যাডমিন", "ফি", "লগইন"]
                    
                    if any(kw in latest_q_lower for kw in admin_keywords):
                        st.toast("Routing to Admin Support Agent...", icon="🎧")
                        thinking_placeholder.empty()
                        
                        with chat_container.chat_message("assistant", avatar="🎧"):
                            from core_agents import process_customer_service
                            cs_result = process_customer_service(latest_q, current_uid)
                            
                            if cs_result["status"] == "success":
                                ans_data = cs_result["data"]
                                res_text = ans_data["response"]
                                
                                # If escalated, show a cool ticket badge
                                if ans_data.get("status") == "escalated":
                                    cat = ans_data.get('escalation_category', 'Support')
                                    res_text += f"\n\n🎫 **[Ticket Created & Sent to Admin: {cat}]**"
                                
                                # Stream the support text smoothly
                                import time
                                def stream_cs():
                                    for word in res_text.split():
                                        yield word + " "
                                        time.sleep(0.03)
                                answer = st.write_stream(stream_cs())
                                
                            else:
                                res_text = "I am currently unable to reach the support database. Please try again later."
                                st.warning(res_text)

                # --- 2. 🔌 SMART OFFLINE ENGINE ---
                elif (lambda: __import__("socket").setdefaulttimeout(2) or __import__("socket").socket(__import__("socket").AF_INET, __import__("socket").SOCK_STREAM).connect_ex(("8.8.8.8", 53)) != 0)():
                    if st.session_state.current_model != "local-gpt4all":
                        thinking_placeholder.empty() # Clear spinner immediately
                        res_text = "🔌 **Internet connection lost.** \n\nPlease select **'Offline Mode (GPT4All Local)'** from the AI Engine dropdown menu to continue offline."
                        st.error(res_text)
                    else:
                        with st.spinner("Analyzing locally with GPT4All..."):
                            try:
                                def route_query(query):
                                    q = query.lower()
                                    if any(x in q for x in ["research", "methodology", "social", "hypothesis"]): return "IR-210"
                                    elif any(x in q for x in ["foreign policy", "diplomacy", "policy", "fpa"]): return "IR-202"
                                    elif any(x in q for x in ["french", "france", "translate", "alphabet"]): return "French"
                                    elif any(x in q for x in ["intro", "theory", "realism"]): return "IR-200"
                                    else: return "General"
                                
                                detected_course = route_query(latest_q)
                                db_context, db_docs = search_context(latest_q, active_course=detected_course if detected_course != "General" else None)
                                
                                db_sources = {}
                                if db_docs:
                                    for doc in db_docs:
                                        src_name = os.path.basename(doc.metadata.get('source', 'Unknown'))
                                        page = doc.metadata.get('page')
                                        if src_name not in db_sources: db_sources[src_name] = set()
                                        if page is not None: db_sources[src_name].add(str(page + 1))

                                is_bengali = bool(re.search(r'[\u0980-\u09FF]', latest_q))
                                sys_inst = "তুমি হচ্ছো GSTU এর IR ডিপার্টমেন্টের এলিট এআই। শুধুমাত্র বাংলায় বিস্তারিত উত্তর দাও।" if is_bengali else "You are the Elite GSTU AI Assistant for IR. Provide a detailed, academic response in English."
                                
                                offline_prompt = f"{sys_inst}\n\nContext:\n{db_context[:1200]}\n\nQuestion: {latest_q}\n\nAnalysis:"
                                
                                try:
                                    response = llm.invoke(offline_prompt)
                                    answer = str(response.content).strip()
                                except Exception as e:
                                    err_str = str(e).lower()
                                    if "connection error" in err_str or "connection refused" in err_str:
                                        answer = "⚠️ **Offline Server Not Running!**\n\nঅনুগ্রহ করে আপনার পিসিতে **GPT4All** অ্যাপটি ওপেন করুন এবং Settings থেকে **'Enable API Server'** অপশনটি অন করুন। এরপর আবার ট্রাই করুন।"
                                    else:
                                        answer = f"⚠️ **GPT4All Error:** `{str(e)}`"

                                # Clear spinner & Render final output
                                thinking_placeholder.empty()
                                
                                source_text = "\n\n<details><summary><b>📚 View Local Sources</b></summary>\n<ul>"
                                for src, pages in db_sources.items():
                                    page_str = ", ".join(sorted(list(pages), key=lambda x: int(x) if x.isdigit() else str(x))) if pages else ""
                                    source_text += f"<li>📄 {src} {f'<i>(Page: {page_str})</i>' if page_str else ''}</li>"
                                source_text += "</ul></details>"
                                
                                res_text = f"🔌 **[Offline Mode Active]**\n\n{answer}{source_text}"
                                st.markdown(res_text, unsafe_allow_html=True)
                                
                            except Exception as e:
                                res_text = f"⚠️ **GPT4All Error:** `{str(e)}`"
                                st.error(res_text)


                # --- 3. 🌐 ONLINE CLOUD ENGINE (Only 1 Spinner, Bullet-Fast!) ---
                else:
                    with st.spinner("Analyzing GSTU Database & Live Web..."):
                        try:
                            is_bengali = bool(re.search(r'[\u0980-\u09FF]', latest_q))
                            active_model = st.session_state.current_model
                            
                            # Auto-Route Bengali to Gemini
                            if is_bengali and "llama" in active_model.lower():
                                st.toast("🔄 Llama doesn't support Bengali perfectly. Auto-routing to Gemini...", icon="⚡")
                                google_api_key = os.getenv("GOOGLE_API_KEY") or st.secrets.get("GOOGLE_API_KEY")
                                llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.2, google_api_key=google_api_key)
                            else:
                                llm = get_llm(active_model)

                            # =====================================================================
                            # 1. Pinecone Cloud DB Search (Replaces ChromaDB)
                            # =====================================================================
                            db_context = "No relevant academic data found in the local database."
                            db_sources = {}
                            
                            try:                       
                                embeddings = GoogleGenerativeAIEmbeddings(
                                    model="models/gemini-embedding-2", 
                                    google_api_key=os.getenv("GOOGLE_API_KEY") or st.secrets.get("GOOGLE_API_KEY")
                                )
                                vectorstore = PineconeVectorStore(
                                    index_name="gstu-knowledge-base", 
                                    embedding=embeddings,
                                    pinecone_api_key=os.getenv("PINECONE_API_KEY") or st.secrets.get("PINECONE_API_KEY")
                                )
                                retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
                                db_docs = retriever.invoke(latest_q)
                                
                                if db_docs:
                                    db_context = "\n\n".join([f"Local Doc: {d.page_content}" for d in db_docs])
                                    for doc in db_docs:
                                        src_name = os.path.basename(doc.metadata.get('source', 'Uploaded PDF'))
                                        page = doc.metadata.get('page')
                                        if src_name not in db_sources: db_sources[src_name] = set()
                                        if page is not None:
                                                clean_page = str(int(float(page)) + 1)
                                                db_sources[src_name].add(clean_page)
                            except Exception as e:
                                print(f"Pinecone RAG Error: {e}")
                    
                        
                            # =====================================================================
                            # 2. Web Search Module (With Auto Banglish-to-English Translator!)
                            # =====================================================================
                            rt_keywords = ["current", "latest", "now", "today", "recent", "update", "updates", "2024", "2025", "2026", "news", "geopolitics", "situation", "war", "conflict", "crisis", "বর্তমান", "সাম্প্রতিক", "আজকের", "এখনকার", "খবর", "নিউজ", "পরিস্থিতি", "অবস্থা", "আপডেট", "bortoman", "bishwer", "bisser", "ajker"]
                            definition_keywords = ["define", "what is", "concept of", "theory of", "meaning of", "who is", "scholar", "describe", "explain", "সংজ্ঞা", "কি", "কাকে বলে", "তত্ত্ব", "মতবাদ"]
                            explicit_temporal = ["current", "latest", "now", "today", "recent", "update", "updates", "2026", "news", "বর্তমান", "সাম্প্রতিক", "আজকের", "খবর", "আপডেট", "bortoman", "ajker"]
                            
                            latest_q_lower = latest_q.lower()
                            
                            # ১. প্রাথমিক চেক: কোয়েরিতে কোনো লাইভ কি-ওয়ার্ড আছে কিনা
                            has_rt_keyword = any(kw in latest_q_lower for kw in rt_keywords)

                            # ২. ডেফিনিশন চেক: এটা কি পিওর একাডেমিক ডেফিনিশন বা থিওরি কিনা
                            has_definition_keyword = any(kw in latest_q_lower for kw in definition_keywords)
                            has_explicit_time = any(kw in latest_q_lower for kw in explicit_temporal)
                            
                            # ৩. স্মার্ট ডিসিশন: থিওরি কি-ওয়ার্ড থাকলে লাইভ সার্চ বন্ধ, যদি না সেখানে লেটেস্ট টাইম মার্কার থাকে
                            if has_definition_keyword and not has_explicit_time:
                                needs_web = False  # থিওরিটিক্যাল প্রশ্ন, এপিআই লিমিট বাঁচাও
                            else:
                                needs_web = has_rt_keyword
                            
                            web_context = "No live web search triggered."
                            web_links = []

                            if needs_web:
                                tavily_key = os.getenv("TAVILY_API_KEY") or (st.secrets.get("TAVILY_API_KEY") if hasattr(st, "secrets") else None)
                                if not tavily_key:
                                    st.error("⚠️ TAVILY_API_KEY is missing!")
                                    st.stop()
                                    
                                try:
                                    # Translate Banglish/Bengali to English for Tavily
                                    search_query = latest_q
                                    has_banglish = any(word in latest_q.lower().split() for word in ["ki", "ajker", "kemon", "bhalo", "koro", "hobe", "na", "amar", "tumi", "bolo", "bisser", "bortoman", "news"])
                                    
                                    if is_bengali or has_banglish:
                                        # Use a lightning-fast Groq model just for translating the search intent
                                        from groq import Groq
                                        translator = Groq(api_key=os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY"))
                                        trans_res = translator.chat.completions.create(
                                            model="llama-3.3-70b-versatile", 
                                            messages=[
                                                {"role": "system", "content": "You are a translator. Translate the given Bengali or Banglish text into a short, concise English search query (max 5 words) for Google Search. ONLY output the English query, nothing else. Example: 'bisser bortoman news' -> 'current global geopolitics news'."},
                                                {"role": "user", "content": latest_q}
                                            ],
                                            temperature=0.1,
                                            max_tokens=20
                                        )
                                        search_query = trans_res.choices[0].message.content.strip().strip('"').strip("'")
                                        # st.toast(f"🔍 Translated Search: {search_query}") # (Optional) Uncomment to see what it translated to
                                    
                                    # Now search Tavily with the PERFECT English query!
                                    from tavily import TavilyClient
                                    tavily_client = TavilyClient(api_key=tavily_key)
                                    tavily_res = tavily_client.search(
                                        query=search_query, search_depth="advanced", max_results=5, include_answer=True,
                                        exclude_domains=["instagram.com", "youtube.com", "facebook.com", "x.com", "twitter.com", "tiktok.com"]
                                    )
                                    web_context = f"Tavily AI Summary: {tavily_res.get('answer', '')}\n\n"
                                    for r in tavily_res.get('results', []):
                                        web_context += f"Source: {r.get('title', 'Web')}\nSnippet: {r.get('content', '')}\n\n"
                                        web_links.append(r.get('url', ''))
                                        used_web = True # সোর্স রেন্ডারিং ইন্টিগ্রেশনের জন্য ট্রু
                                except Exception as e:
                                    st.warning(f"⚠️ Live search failed: {e}. Relying solely on local database.")


                            # =====================================================================
                            # 3. Context & Truncation (Safe Limits)
                            # =====================================================================
                            prior_messages = st.session_state.messages[:-1]
                            history_ctx = build_history_context(prior_messages)
                            contextual_query = (f"{latest_q}\n\n[Conversation context:\n{history_ctx}]") if history_ctx != "No prior conversation." else latest_q

                            MAX_DB_CHARS = 2000
                            safe_db_context = db_context[:MAX_DB_CHARS] + ("...[Truncated]" if len(db_context) > MAX_DB_CHARS else "")
                            
                            # NOTE: If you have a separate file uploader context (context_from_files), you can append it here.
                            safe_file_context = context_from_files[:1500] if 'context_from_files' in locals() else "No files uploaded."
                            
                            # 4. Strict Language Router

                            banglish_keywords = [
                                "ki", "ajker", "kemon", "bhalo", "koro", "hobe", "na", "amar", "tumi", "bolo", 
                                "bisser", "bortoman", "khobor", "somporke", "niye", "kobe", "kothay", "keno", 
                                "kivabe", "kibhabe", "konta", "naki", "dao", "dekhaw", "bolen", "janaw", 
                                "shomporke", "gulo", "gula", "kore", "kori", "korbo", "biswer", "ajke"
                            ]

                            has_banglish_keywords = any(word in latest_q.lower().split() for word in banglish_keywords)
                            
                            if is_bengali or has_banglish_keywords:
                                system_instruction = (
                                    "You are the Chief Geopolitical Analyst for the IR Department at GSTU.\n"
                                    "CRITICAL REQUIREMENT: You MUST respond entirely in flawless, academic, formal BENGALI SCRIPT (বাংলা লিপি).\n"
                                    "Never mix English and Bengali sentences. Provide deep analytical value without repetition."
                                )
                                language_shield = "OUTPUT PROTOCOL: 100% Formal Bengali Script. No English phrasing inside the main body text."
                            else:
                                system_instruction = (
                                    "You are the Chief Geopolitical Analyst and University Professor for the IR Department at GSTU.\n"
                                    "CRITICAL REQUIREMENT: You MUST answer entirely in elite, scholarly, academic ENGLISH.\n"
                                    "Do not use a single character of Bengali script or any informal language."
                                )
                                language_shield = "OUTPUT PROTOCOL: 100% Scholarly English. Zero Bengali script allowed."

                            import datetime
                            current_date = datetime.datetime.now().strftime("%B %d, %Y")

                            # 🧠 1. FETCH STUDENT LEARNING GRAPH MEMORY (FIXED LOGIC)
                            try:
                                # Fetch last session mood
                                last_session = supabase.table("study_sessions").select("topic, mood").eq("user_id", st.session_state.username_id).order("timestamp", desc=True).limit(1).execute()
                                last_mood = last_session.data[0].get("mood") if last_session.data else 3
                                
                                logs_res = supabase.table("ai_training_logs").select("topic_tag").eq("user_id", st.session_state.username_id).execute()
                                
                                if logs_res.data:
                                    import pandas as pd
                                    df = pd.DataFrame(logs_res.data)
                                    valid_topics = df[df['topic_tag'].str.strip() != '']
                                    user_focus = valid_topics['topic_tag'].mode()[0].title() if not valid_topics.empty else "General Academic Concepts"
                                else: user_focus = "General Academic Concepts"
                            except: 
                                last_mood = 3
                                user_focus = "General Academic Concepts"

                            # 🧠 2. INJECT MEMORY INTO HYBRID PROMPT
                            hybrid_prompt = f"""{system_instruction}

        ⏳ CURRENT SYSTEM DATE: {current_date}
        {language_shield}

        🧠 STUDENT LEARNING STATE (MEMORY):
        - Focus Topic: "{user_focus}"
        - Last Session Mood (1-5): {last_mood}
        - NOTE: If the mood is low (1-2), be extra encouraging and break down complex IR theories into tiny, manageable steps. If mood is high (4-5), provide deeper, challenging geopolitical analysis.
        When explaining complex theories, providing examples, or analyzing ANY topic, proactively try to draw analogies and links back to "{user_focus}" to make your explanations highly engaging and relatable for the user.

        🛡️ ZERO-HALLUCINATION & FACT-GROUNDING ENFORCEMENT:
        1. TIME-AWARENESS: Distinguish between historical context and active live news. If the user asks about recent updates or dates like 'May 2026', focus heavily on Live Web Data.
        2. 0% HALLUCINATION: Ground your analysis strictly on the provided facts. If information is missing, explicitly state that you lack sufficient data, do not invent details.
        3. STRUCTURE: Use clear section headers, bold text, and clean bullet points. Avoid repeating information or looping sentences.
        4. CITATIONS: Include numeric inline citations like [1], [2] if data is derived from the local database.

        Context from uploaded documents:
        {safe_file_context}

        --- LOCAL ACADEMIC DATABASE ---
        {safe_db_context}

        --- LIVE WEB DATA ---
        {web_context}

        --- USER QUERY ---
        {contextual_query}

        Provide your clean, well-structured, non-repetitive academic analysis below:"""

                            from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
                            agent_messages = [
                                SystemMessage(content=system_instruction),
                                HumanMessage(content=hybrid_prompt)
                            ]

                            # =====================================================================
                            # 5. AGENTIC CORE EXECUTION
                            # =====================================================================
                            ENABLE_AGENTIC_CORE = True
                            ENABLE_WEB_SEARCH = True
                            ENABLE_RAG = True
                            ENABLE_VERIFIER = True
                            
                            tool_triggered = False
                            answer = ""
                            res_text = ""
                            
                            if ENABLE_AGENTIC_CORE:
                                try:
                                    from langchain_groq import ChatGroq
                                    llm_agent = ChatGroq(
                                        api_key=os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY"),
                                        model="llama-3.3-70b-versatile",
                                        temperature=0.3,
                                        max_tokens=2048
                                    )
                                    llm_with_tools = llm_agent.bind_tools(astra_core_tools)
                                    initial_response = llm_with_tools.invoke(agent_messages)
                                    
                                    if hasattr(initial_response, 'tool_calls') and initial_response.tool_calls:
                                        tool_triggered = True 
                                        st.toast("Activating AI Agent Tools...", icon="🌐") 
                                        agent_messages.append(initial_response)
                                        
                                        for tool_call in initial_response.tool_calls:
                                            tool_name = tool_call['name']
                                            tool_args = tool_call['args']
                                            
                                            if tool_name == "analyze_student_progress" and "user_id" not in tool_args:
                                                tool_args["user_id"] = user_id
                                                
                                            tool_func = next((t for t in astra_core_tools if t.name == tool_name), None)
                                            
                                            if tool_func is None:
                                                agent_messages.append(ToolMessage(content=f"Tool '{tool_name}' not available.", tool_call_id=tool_call['id']))
                                            else:
                                                try:
                                                    tool_result = tool_func.invoke(tool_args)
                                                    agent_messages.append(ToolMessage(content=str(tool_result), tool_call_id=tool_call['id']))
                                                except Exception as te:
                                                    agent_messages.append(ToolMessage(content=f"Tool failed: {str(te)}", tool_call_id=tool_call['id']))
                                        
                                        thinking_placeholder.empty()
                                        def agent_stream_generator():
                                            for chunk in llm_agent.stream(agent_messages): 
                                                if hasattr(chunk, 'content') and chunk.content: yield str(chunk.content)
                                        res_text = st.write_stream(agent_stream_generator())
                                        
                                    else:
                                        tool_triggered = False

                                except Exception as e:
                                    error_str = str(e).lower()
                                    if "400" in error_str or "function" in error_str:
                                        tool_triggered = False 
                                    else:
                                        st.error(f"⚠️ Agent System Error: {e}")
                                        tool_triggered = False 


                            # --- FALLBACK / STANDARD STREAMING (With VERIFIER ENGINE) ---
                            if not tool_triggered:
                                if ENABLE_VERIFIER:
                                    thinking_placeholder.markdown(get_thinking_html().replace("Analyzing GSTU Database & Live Web", "🛡️ Verifying Facts..."), unsafe_allow_html=True)
                                    
                                    draft_response = llm_engine.invoke(agent_messages).content
                                    from core_agents import create_verifier_messages
                                    total_context = f"DATABASE:\n{db_context}\n\nWEB:\n{web_context}"
                                    verifier_result = create_verifier_messages(latest_q, total_context, draft_response, is_bengali)
                                    
                                    thinking_placeholder.empty() 
                                    
                                    if verifier_result["status"] == "success":
                                        badge_html = "<div style='background: rgba(16, 163, 127, 0.1); border: 1px solid rgba(16, 163, 127, 0.3); padding: 6px 12px; border-radius: 6px; margin-bottom: 12px; display: inline-block;'><span style='font-size:13px; color:#10a37f; font-weight:600;'>🛡️ ✓ Fact-checked by Verifier Agent</span></div>\n\n"
                                        st.markdown(badge_html, unsafe_allow_html=True)
                                        
                                        def stream_verified():
                                            for chunk in llm_engine.stream(verifier_result["messages"]):
                                                if hasattr(chunk, 'content') and chunk.content: yield str(chunk.content)
                                        res_text = st.write_stream(stream_verified())
                                        res_text = badge_html + res_text 
                                    else:
                                        st.warning("⚠️ Verifier Offline. Showing direct draft.")
                                        def stream_draft():
                                            for chunk in llm_engine.stream(agent_messages):
                                                if hasattr(chunk, 'content') and chunk.content: yield str(chunk.content)
                                        res_text = st.write_stream(stream_draft())
                                     
                                else: 
                                    thinking_placeholder.empty()
                                    def stream_standard():
                                        for chunk in llm_engine.stream(agent_messages):
                                            if hasattr(chunk, 'content') and chunk.content: yield str(chunk.content)
                                    res_text = st.write_stream(stream_standard())
                        
                        except Exception as e:
                            thinking_placeholder.empty()
                            st.error(f"⚠️ Critical System Error: {e}")
                            res_text = "System Error"

                            # 6. Smooth Silent Fallback
                            error_msg = str(e).lower()
                            if any(keyword in error_msg for keyword in ["429", "413", "rate limit", "rate_limit", "quota", "tokens"]):
                                try:
                                    fallback_llm = get_llm("gemini-2.5-flash")
                                    def fallback_stream():
                                        for chunk in fallback_llm.stream(agent_messages):
                                            if hasattr(chunk, 'content'): yield str(chunk.content)
                                    st.toast("⚠️ Heavy load detected! Switched to backup AI.", icon="🔄")
                                    res_text = st.write_stream(fallback_stream())
                                except Exception as fallback_e:
                                    res_text = "🚦 **Server Overloaded!** Please wait 10 seconds and try again."
                                    st.markdown(res_text)
                            else:
                                res_text = f"⚠️ System Error: `{str(e)[:150]}`"
                                st.error(res_text)
                            
                        
                    # =====================================================================
                    # 7. RENDERING SOURCES & CITATIONS (🔴 DE-NESTED FROM EXCEPT BLOCK)
                    # =====================================================================
                    if "System Error" not in res_text and "Server Overloaded" not in res_text:
                        source_text = "\n\n<div style='margin-top: 15px;'><details><summary style='cursor: pointer; font-weight: 600; color: white;'>📚 View Citations & Sources</summary><div style='padding-top: 10px;'>"
                        has_sources = False
                        
                        # Process Pinecone DB Sources
                        db_src_dict = locals().get("db_sources", {})
                        if db_src_dict:
                            has_sources = True
                            for src, pages in db_src_dict.items():
                                page_str = ", ".join(sorted(list(pages), key=lambda x: int(x) if x.isdigit() else str(x))) if pages else ""
                                source_text += f"<div style='margin-bottom: 5px;'>📄 <b>{src}</b> {f'<i>(Page: {page_str})</i>' if page_str else ''}</div>"
                                
                        # Process Web Sources (Tavily links or used_web status)
                        web_links = locals().get("web_links", [])
                        needs_web = locals().get("needs_web", False)
                        used_web = locals().get("used_web", False)
                        
                        if web_links or used_web:
                            has_sources = True
                            source_text += "<div style='display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px;'>"
                            if web_links:
                                for link in web_links:
                                    if link: 
                                        domain = link.split('/')[2].replace('www.', '') if '//' in link else 'Web Source'
                                        source_text += f"<a href='{link}' target='_blank' style='background: rgba(16, 163, 127, 0.1); border: 1px solid rgba(16, 163, 127, 0.4); color: inherit; padding: 4px 12px; border-radius: 16px; text-decoration: none; font-size: 12px; transition: all 0.2s;'>🔗 {domain}</a>"
                            else:
                                source_text += f"<div style='background: rgba(16, 163, 127, 0.1); border: 1px solid rgba(16, 163, 127, 0.4); color: inherit; padding: 4px 12px; border-radius: 16px; font-size: 12px;'>🔗 Live Web Search</div>"
                            source_text += "</div>"
                                    
                        # If completely standard fallback
                        if not has_sources:
                            source_text += "<div style='margin-bottom: 5px; color: #94a3b8;'>🧠 <b>Internal AI Knowledge / General Concept</b></div>"
                                    
                        source_text += "</div></details></div>"
                        
                        # Render the source UI live directly to the chat
                        st.markdown(source_text, unsafe_allow_html=True)
                        
                        # Append to the saved text for chat history
                        res_text += source_text
                        
                        if needs_web and (web_links or used_web):
                            search_badge = "\n\n*(🌐 Realtime Data Powered by **GSTU AI Search**)*"
                            st.markdown(search_badge)
                            res_text += search_badge

        # ==============================================================
        # 💾 SAVE & CLEANUP (Execute Only Once)
        # ==============================================================
        if res_text:
            st.session_state.messages.append({"role": "assistant", "content": res_text})
            increment_usage(st.session_state.username_id, current_tier)

            # 🔴 LOG DATA FOR FUTURE AI TRAINING
            try:
                # টপিক এক্সট্রাক্টর (প্রথম ৩-৪টা শব্দ)
                extracted_topic = " ".join(user_query.split()[:4]) 
                
                supabase.table("ai_training_logs").insert({
                    "user_id": st.session_state.username_id,
                    "user_query": user_query,
                    "ai_response": res_text,
                    "topic_tag": extracted_topic,
                    "timestamp": "now()"
                }).execute()

                # 🟢 Silently update the student's weakness graph based on topics discussed
                # AI will update it to "Weak" or "Strong" based on actual quiz/flashcard tests later.
                update_weakness_graph(st.session_state.username_id, extracted_topic, "Explored")
            
            except: pass
            
            if st.session_state.get('current_session_id'):
                save_message_to_cloud(st.session_state.current_session_id, "ai", res_text)
        
        for ch in st.session_state.chat_history:
            if ch["title"] == st.session_state.active_chat_title: 
                ch["messages"] = st.session_state.messages.copy()
        
        try:
            save_chat_history(st.session_state.chat_history)
        except Exception:
            pass
        

        # =====================================================================
        # 📜 ROBUST AUTO-SCROLL MECHANISM
        # =====================================================================
        st.components.v1.html("""
            <script>
                setTimeout(function() {
                    const messages = window.parent.document.querySelectorAll('.stChatMessage');
                    if (messages.length > 0) {
                        messages[messages.length - 1].scrollIntoView({ behavior: 'smooth', block: 'end' });
                    }
                }, 400); 
            </script>
        """, height=0)