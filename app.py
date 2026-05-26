import re  # For detecting Bengali/French text automatically
import uuid
import html
import os
import email
import hashlib
import time
import json
import socket
import secrets
import base64
import tempfile
import hmac
import logging
logger = logging.getLogger(__name__)
import streamlit as st

from langchain_community.chat_models import ChatOpenAI
from langchain_core import embeddings
from socket import AF_INET, SOCK_STREAM
from dotenv import load_dotenv

# Core Imports
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain_groq import ChatGroq

# Database and authentication module import
from auth_logic import render_auth_interface, logout_user, init_auth_session, supabase
from database_manager import save_chat_message, fetch_chat_history
from analytics_engine import render_study_logger, render_analytics_dashboard
from database import save_to_vector_db, search_context
import os, json, time, logging, socket, html
from streamlit_cookies_controller import CookieController


# 🔴 1. PAGE CONFIG MUST BE THE FIRST COMMAND!
st.set_page_config(page_title="GSTU AI Assistant", layout="wide", page_icon="🎓", initial_sidebar_state="expanded")

# 🔴 2. INITIALIZE COOKIE CONTROLLER IMMEDIATELY
cookie_controller = CookieController()

# 🔴 3. SESSION STATE VARIABLES (CONSOLIDATED)

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
    
if "user_info" not in st.session_state:
    st.session_state["user_info"] = None

# 🔴 4. AUTO-RECOVERY LOGIC (THE MAGIC FIX)

try:
    saved_session = cookie_controller.get("gstu_session") 
    if saved_session and not st.session_state["authenticated"]:
        st.session_state["authenticated"] = True
        st.session_state["user_info"] = saved_session
except Exception as e:
    pass

# =====================================================================
# 🎨 PREMIUM MODERN UI CSS
# =====================================================================
st.markdown("""
    <style>
    .block-container { max-width: 95% !important; transition: max-width 0.4s cubic-bezier(0.2, 0.8, 0.2, 1), padding 0.4s ease !important; }
    div.stButton > button { border-radius: 8px !important; border: 1px solid rgba(255, 255, 255, 0.2) !important; background-color: transparent !important; transition: all 0.3s cubic-bezier(0.2, 0.8, 0.2, 1) !important; }
    div.stButton > button:hover { border-color: #10a37f !important; color: #10a37f !important; transform: translateY(-2px) !important; box-shadow: 0 4px 12px rgba(16, 163, 127, 0.2) !important; }
    div.stSelectbox > div[data-baseweb="select"] > div { background-color: transparent !important; border: 1px solid rgba(255, 255, 255, 0.2) !important; border-radius: 8px !important; transition: all 0.3s ease !important; }
    div.stSelectbox > div[data-baseweb="select"] > div:hover { border-color: #10a37f !important; box-shadow: 0 0 10px rgba(16, 163, 127, 0.3) !important; }
    [data-testid="stFileUploadDropzone"] { border: 2px dashed rgba(255, 255, 255, 0.3) !important; border-radius: 12px !important; background: transparent !important; transition: all 0.3s ease-in-out !important; }
    [data-testid="stFileUploadDropzone"]:hover { border-color: #10a37f !important; background-color: rgba(16, 163, 127, 0.05) !important; transform: scale(1.02) !important; }
    </style>
""", unsafe_allow_html=True)



# 🔴 THE MASTER FEATURE FLAG
ENABLE_AGENTIC_FEATURES = True # (এটা True যেহেতু আমরা backend_api.py-তে Agentic Core বসিয়েছি)


# Important Dependencies
SESSION_MAX_AGE_SEC = 86400
OTP_EXPIRY_SEC = 300
ts = int(time.time())
sig = ""
exc = Exception("System Error")
up_files = [] 
logger = logging.getLogger(__name__) 

# 🔴 GLOBAL DB PATH
DB_FILE = "users_db.json"
SESSION_FILE = "current_session.json"

# --- MISSING FUNCTIONS ---
def clear_local_session():
    if os.path.exists(SESSION_FILE): 
        try: os.remove(SESSION_FILE)
        except: pass

def load_users():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f: return json.load(f)
    return {}

# Helper Functions
def esc(value: str) -> str: return html.escape(str(value), quote=True)
def is_online(host="8.8.8.8", port=53, timeout=3) -> bool:
    sock = None
    try:
        sock = socket.socket(AF_INET, SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        return True
    except OSError: return False
    finally:
        if sock: sock.close()

# 🔴 LOAD USERS DB EARLY
if "users_db" not in st.session_state: 
    st.session_state.users_db = load_users()


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


# 👑 ADMIN SYSTEM
ADMIN_EMAILS = ["yousufaltashfin@gmail.com"]

# 🍪 ROBUST COOKIE AUTO-LOGIN (Auto-Logout Fix)
saved_uid = cookie_controller.get("gstu_uid")
if saved_uid and not st.session_state.get("logged_in", False):
    if saved_uid in st.session_state.users_db:
        user_info = st.session_state.users_db[saved_uid]
        st.session_state["authenticated"] = True
        st.session_state.username_id = saved_uid
        st.session_state.user_name = user_info.get("name", "User")
        st.session_state.user_email = user_info.get("email", "admin@gstu.edu")
        
        # Admin Role Security Check
        if st.session_state.user_email in ADMIN_EMAILS:
            st.session_state.users_db[saved_uid]["role"] = "Admin"
            
        st.session_state.user_role = st.session_state.users_db[saved_uid]["role"]
        st.rerun() # 🔴 কুকি পেলেই সাথে সাথে ড্যাশবোর্ডে নিয়ে যাবে


# 🧠 SUPABASE OAUTH LOGIC (Smooth Transition & Anti-Flash)
if "code" in st.query_params:
    st.markdown("<h3 style='text-align:center; margin-top: 20vh; color: #10a37f;'>🔄 Securing Connection... Please wait.</h3>", unsafe_allow_html=True)
    try:
        auth_code = st.query_params["code"]
        if isinstance(auth_code, list): auth_code = auth_code[0]
        
        session = supabase.auth.exchange_code_for_session({"auth_code": auth_code})
        if session and session.user:
            uid = session.user.id
            email = session.user.email
            name = session.user.user_metadata.get("full_name", email.split("@")[0])
            
            assigned_role = "Admin" if email in ADMIN_EMAILS else session.user.user_metadata.get("role", "Student")
            
            st.session_state["authenticated"] = True
            st.session_state.username_id = uid
            st.session_state.user_email = email
            st.session_state.user_name = name
            st.session_state.user_role = assigned_role
            
            if uid not in st.session_state.users_db:
                st.session_state.users_db[uid] = {"name": name, "role": assigned_role, "email": email, "avatar": None}
            else:
                st.session_state.users_db[uid]["role"] = assigned_role 
            
            with open(DB_FILE, "w") as f: json.dump(st.session_state.users_db, f, indent=4)
            cookie_controller.set("gstu_uid", uid, max_age=2592000)
            
            st.toast(f"✅ Login Successful! Welcome back, {name}", icon="🎉")
            time.sleep(1) # Smooth buffer
            st.query_params.clear() 
            st.rerun()
            
    except Exception as e:
        st.error(f"Auth Error: {e}")
        st.query_params.clear()
        time.sleep(1)
        st.rerun()
    st.stop() # 🔴 CRITICAL: Stops the giant FB logo from rendering below!


# 👑 ADMIN SYSTEM (Strict RBAC)
ADMIN_EMAILS = ["yousufaltashfin@gmail.com", "tashfin@gstu.edu"]

# 🛑 THE GATEKEEPER: Stop everything if not logged in
if not st.session_state.get("logged_in", False):
    render_auth_interface()
    st.stop()
else:
    # 🔴 SAVE USER TO DB & FORCE ADMIN ROLE
    current_uid = st.session_state.username_id
    user_id = current_uid
    
    # 🔴 Strict Admin Override (Works for both Manual & Google Auth)
    if st.session_state.user_email in ADMIN_EMAILS:
        st.session_state.user_role = "Admin"
        
    if current_uid not in st.session_state.users_db:
        st.session_state.users_db[current_uid] = {
            "name": st.session_state.user_name,
            "role": st.session_state.user_role,
            "email": st.session_state.user_email,
            "avatar": None
        }
        with open(DB_FILE, "w") as f: json.dump(st.session_state.users_db, f, indent=4)
    else:
        # Update existing user role just in case
        st.session_state.users_db[current_uid]["role"] = st.session_state.user_role
        with open(DB_FILE, "w") as f: json.dump(st.session_state.users_db, f, indent=4)


# 🛑 THE GATEKEEPER
if not st.session_state.get("logged_in", False):
    render_auth_interface()
    st.stop()
else:
    # 🔴 SAVE USER TO DB IF NEW
    current_uid = st.session_state.username_id
    user_id = current_uid
    if current_uid not in st.session_state.users_db:
        st.session_state.users_db[current_uid] = {
            "name": st.session_state.user_name,
            "role": "Student",
            "email": st.session_state.user_email,
            "avatar": None
        }
        with open(DB_FILE, "w") as f: json.dump(st.session_state.users_db, f, indent=4)

    st.session_state.user_role = st.session_state.users_db[current_uid].get("role", "Student")

# --- চ্যাট হিস্ট্রি এবং মেমোরি ---
if "chat_history_loaded" not in st.session_state: st.session_state.chat_history_loaded = False
if "messages" not in st.session_state: st.session_state.messages = []

def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file: return base64.b64encode(img_file.read()).decode()
    return None

logo_b64 = get_base64_image("logo.png")


# 👑 ADMIN SYSTEM (Strict RBAC)
ADMIN_EMAILS = ["yousufaltashfin@gmail.com", "tashfin@gstu.edu"]

# 🛑 THE GATEKEEPER: Stop everything if not logged in
if not st.session_state.get("logged_in", False):
    render_auth_interface()
    st.stop()
else:
    # 🔴 SAVE USER TO DB & FORCE ADMIN ROLE
    current_uid = st.session_state.username_id
    user_id = current_uid
    
    # 🔴 Strict Admin Override (Works for both Manual & Google Auth)
    if st.session_state.user_email in ADMIN_EMAILS:
        st.session_state.user_role = "Admin"
        
    if current_uid not in st.session_state.users_db:
        st.session_state.users_db[current_uid] = {
            "name": st.session_state.user_name,
            "role": st.session_state.user_role,
            "email": st.session_state.user_email,
            "avatar": None
        }
        with open(DB_FILE, "w") as f: json.dump(st.session_state.users_db, f, indent=4)
    else:
        # Update existing user role just in case
        st.session_state.users_db[current_uid]["role"] = st.session_state.user_role
        with open(DB_FILE, "w") as f: json.dump(st.session_state.users_db, f, indent=4)


# =====================================================================
# ⚙️ PREMIUM ACCOUNT, BILLING, ADS & PRIVACY DIALOGS
# =====================================================================

@st.dialog("⚙️ Account Settings & Subscription", width="large")
def account_settings_dialog():
    # 🔴 3 Tabs: Profile, Pro Subscription, Alternative Earn
    tab_profile, tab_billing, tab_earn = st.tabs(["👤 Profile", "💎 Upgrade to Pro", "🎁 Earn Free Pro (Tasks)"])
    
    with tab_profile:
        st.markdown(f"**Name:** {st.session_state.user_name}")
        st.markdown(f"**Email:** {st.session_state.user_email}")
        st.markdown(f"**Account Role:** `{st.session_state.user_role}`")
        st.info("Avatar and role changes are securely synced with Supabase.")
        
    with tab_billing:
        st.markdown("### 💎 Unlock Limitless AI Power")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            <div style='border: 1px solid #10a37f; padding: 15px; border-radius: 10px;'>
                <h4 style='margin:0; color:#10a37f;'>Basic Tier</h4>
                <h2>$0 <span style='font-size: 14px;'>/mo</span></h2>
                <ul style='font-size: 13px;'><li>Llama 3 (Fast Engine)</li><li>Standard Rate Limits</li></ul>
                <button disabled style='width: 100%; border-radius: 5px; padding: 5px;'>Current Plan</button>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown("""
            <div style='border: 1px solid #58A6FF; padding: 15px; border-radius: 10px; background: rgba(88, 166, 255, 0.05);'>
                <h4 style='margin:0; color:#58A6FF;'>Pro Scholar</h4>
                <h2>$5.99 <span style='font-size: 14px;'>/mo</span></h2>
                <ul style='font-size: 13px;'><li>GPT-4o & Claude 3.5 Sonnet</li><li>Unlimited Offline Models</li></ul>
            </div>
            """, unsafe_allow_html=True)
            if st.button("💳 Pay via bKash/SSLCommerz", type="primary", use_container_width=True):
                st.success("Redirecting to secure local payment gateway...")
                
    with tab_earn:
        st.markdown("### 🎁 Can't Pay? Earn Pro Access for Free!")
        st.write("Support the platform by completing quick tasks to unlock 24 Hours of Pro Access.")
        
        t_col1, t_col2 = st.columns(2)
        with t_col1:
            st.markdown("📺 **Watch Sponsored Video** (30 sec)")
            if st.button("▶️ Watch Now", key="ad_btn", use_container_width=True): st.info("Loading Video Ad API...")
        with t_col2:
            st.markdown("📱 **Download & Try App** (+3 Days Pro)")
            if st.button("📥 View Offers", key="task_btn", use_container_width=True): st.info("Loading Offerwall...")



# 🔴 FIXED PROFILE PILL LAYOUT (All duplicates removed)
col_space, col_profile = st.columns([0.88, 0.12])
with col_profile:
    with st.container():
        user_data = st.session_state.users_db.get(current_uid, {})
        avatar_b64 = user_data.get("avatar")
        btn_label = f"👤 {st.session_state.user_name.split()[0][:7]}"
        
        with st.popover(btn_label, use_container_width=True):
            if avatar_b64:
                st.markdown(f"<div style='text-align: center;'><img src='data:image/jpeg;base64,{avatar_b64}' style='width: 70px; height: 70px; border-radius: 50%; object-fit: cover; border: 2px solid #10a37f; margin-bottom: 5px;'></div>", unsafe_allow_html=True)
            else:
                st.markdown("<div style='text-align: center; font-size: 50px; margin-bottom: 5px;'>👤</div>", unsafe_allow_html=True)
                
            st.markdown(f"<h4 style='text-align: center; margin: 0;'>{st.session_state.user_name}</h4>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: center; opacity: 0.7; margin: 0 0 15px 0; font-size: 13px;'>{st.session_state.user_role} Account</p>", unsafe_allow_html=True)
            
            uploaded_pic = st.file_uploader("Update Picture", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
            if uploaded_pic is not None:
                bytes_data = uploaded_pic.getvalue()
                b64_str = base64.b64encode(bytes_data).decode()
                if b64_str != st.session_state.users_db[current_uid].get("avatar"):
                    st.session_state.users_db[current_uid]["avatar"] = b64_str
                    saved_uid(st.session_state.users_db)
                    st.toast("✅ Profile picture updated successfully!")
                    time.sleep(0.5)
                    st.rerun()

            st.divider()
            if st.button("⚙️ Account Settings", use_container_width=True):
                account_settings_dialog() # 🔴 Calls the new dialog

            if st.button("🚪 Logout", key="master_logout_btn_123", use_container_width=True, type="primary"):
                try:
                    cookie_controller.remove("gstu_uid") # 🔴 Safe Cookie Removal
                except KeyError:
                    pass # কুকি না থাকলে ক্র্যাশ করবে না
                logout_user()
                

# =====================================================================
# SECURE JSON HISTORY MANAGER (ISOLATED BY USER)
# =====================================================================
HISTORY_FILE = "chat_history.json"

def load_chat_history():
    """
    Loads chat history strictly isolated to the authenticated user.
    Prevents data leakage between different accounts.
    """
    current_user_id = st.session_state.get("username_id") # Fetch active user ID
    
    if os.path.exists(HISTORY_FILE) and current_user_id:
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                # STRICT FILTER: Only load chats where owner matches current user
                user_specific_data = [d for d in data if d.get("owner_id") == current_user_id]
                
                for d in user_specific_data:
                    if "folder" not in d: 
                        d["folder"] = None
                return user_specific_data
        except (json.JSONDecodeError, IOError, ValueError): 
            return []
    return []

def save_chat_history(history_list):
    """
    Saves chat history while preserving other users' data in the JSON file.
    Appends the owner_id to every new chat project.
    """
    current_user_id = st.session_state.get("username_id")
    if not current_user_id: return
    
    # Inject owner_id into current user's history
    for ch in history_list:
        ch["owner_id"] = current_user_id

    # Load existing global data to merge safely
    global_data = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                global_data = json.load(f)
        except: pass
        
    # Remove old records for THIS user, keep others' records
    filtered_global = [d for d in global_data if d.get("owner_id") != current_user_id]
    
    # Append the updated records for the current user
    final_data = filtered_global + history_list
    
    with open(HISTORY_FILE, "w", encoding="utf-8") as f: 
        json.dump(final_data, f, ensure_ascii=False, indent=4)


# 4. Base64 Image Loader
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file: return base64.b64encode(img_file.read()).decode()
    return None

logo_b64 = get_base64_image("logo.png")
logo_html = f"<img src='data:image/png;base64,{logo_b64}' style='width: 42px; height: 42px; border-radius: 50%; margin-right: 12px; object-fit: cover;'>" if logo_b64 else "<span style='font-size: 42px; margin-right: 10px;'>🎓</span>"

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


# 🔴 ENTERPRISE ADMIN ANALYTICS DASHBOARD
@st.dialog("📈 Enterprise Admin Analytics", width="large")
def admin_dashboard_dialog():
    st.markdown("### 📊 System Overview")
    users_data = st.session_state.users_db
    history_data = st.session_state.chat_history
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("👥 Total Users", len(users_data))
    col2.metric("💬 Total Chats", len(history_data))
    col3.metric("🧠 Active Models", "10 Engines") # 🔴 Fixed to 10
    col4.metric("🟢 System Health", "100% Online")
    
    st.markdown("---")
    
    # 🔴 DYNAMIC GRAPHICAL CHART (Phase 3 functionality)
    st.markdown("#### 📈 Weekly Token Usage & Engagement")
    import pandas as pd
    import numpy as np
    # Generating dynamic dummy data for the graph
    chart_data = pd.DataFrame(np.random.randint(1000, 5000, size=(7, 2)), columns=["Free Tier Usage", "Pro Tier Usage"])
    st.line_chart(chart_data, color=["#10a37f", "#58A6FF"])
    
    st.markdown("---")
    st.markdown("#### 👤 Registered Users Directory")
    for uid, info in users_data.items():
        # 🔴 FIXED: UUID hider. It now strictly shows email
        user_email = info.get('email', uid) 
        st.markdown(f"- **{info.get('name', 'User')}** ({info.get('role', 'Student')}) ✉️ `{user_email}`")
        
    st.markdown("#### 📂 Recent Knowledge Queries")
    for chat in history_data[:5]: 
        st.markdown(f"- 📝 `{chat['title']}` *(Folder: {chat.get('folder', 'Uncategorized')})*")


# 6. THE FLUID CSS BOSS
def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
            st.markdown('<a href="/" target="_self" class="mobile-floating-btn">📝</a>', unsafe_allow_html=True)

local_css("assets/style.css")

# Enterprise Standard Secret Management
try: groq_api_key = st.secrets["GROQ_API_KEY"]
except (KeyError, FileNotFoundError):
    load_dotenv()
    groq_api_key = os.getenv("GROQ_API_KEY")

if not groq_api_key:
    st.error("⚠️ GROQ_API_KEY is missing. Add it to .env or Streamlit secrets.")
    st.stop()

# 7. State Management
if "chat_history" not in st.session_state: st.session_state.chat_history = load_chat_history()
if "quick_query" not in st.session_state: st.session_state.quick_query = None
if "active_chat_title" not in st.session_state: st.session_state.active_chat_title = None
if "messages" not in st.session_state: st.session_state.messages = []
if "current_chat_id" not in st.session_state: st.session_state.current_chat_id = None
if "selection_mode" not in st.session_state: st.session_state.selection_mode = False
if "current_model" not in st.session_state: st.session_state.current_model = "llama-3.1-8b-instant" 

# 8. Initialize Models & Database
@st.cache_resource(show_spinner=False)
def load_central_database():
    db_path = "./chroma_db"
    
    # Check if database exists
    if not os.path.exists(db_path):
        st.warning("⚠️ Local Database not found! Please run 'build_central_db.py' first.")
        return None
        
    # Must use the exact same embedding model used during building!
    embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")
    return Chroma(persist_directory=db_path, embedding_function=embeddings)

vectorstore = load_central_database()


# 🔴 MULTI-MODEL ROUTER (Universal API Switcher)
def get_llm(model_id):
    if "gemini" in model_id.lower():
        google_api_key = os.getenv("GOOGLE_API_KEY") or st.secrets.get("GOOGLE_API_KEY")
        return ChatGoogleGenerativeAI(model=model_id, temperature=0.1, google_api_key=google_api_key)
        
    elif "llama" in model_id.lower():
        groq_api_key = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY")
        return ChatGroq(model_name=model_id, temperature=0.1, groq_api_key=groq_api_key)
        
    elif model_id == "local-gpt4all":
        # 🔴 THE LOCAL OFFLINE ENGINE (Connects to GPT4All Server)
        return ChatOpenAI(
            model_name="local-model", # Name doesn't matter for GPT4All
            temperature=0.4, # 0.4 ensures it elaborates more creatively
            openai_api_key="not-needed", # No real key needed for local
            openai_api_base="http://localhost:4891/v1", # GPT4All's default port
        )
        
    else:
        # 🔴 OPENROUTER ENGINE
        openrouter_key = os.getenv("OPENROUTER_API_KEY") or st.secrets.get("OPENROUTER_API_KEY")
        if not openrouter_key:
            st.error("⚠️ OPENROUTER_API_KEY missing.")
            st.stop()


# 🔴 9. THE ADVANCED HYBRID PROMPT (Pro Synthesis Mode)
prompt_template = """You are the Elite AI Assistant & Chief Geopolitical Analyst for the IR Department at GSTU.

SECURITY CLEARANCE: MAXIMUM.
CRITICAL INSTRUCTIONS:
1. CASUAL GREETINGS: If the user says "hello", "hi", "thanks", "how are you", or makes a casual remark, respond politely, warmly, and concisely (1-2 sentences). DO NOT provide any academic analysis or context.
2. ACADEMIC QUERIES: If the user asks an academic or IR-related question, combine historical theory from the LOCAL DATABASE with current updates from LIVE WEB DATA.
3. ELITE ACADEMIC DEPTH (For IR Queries Only): Dig deeply into the core issues. Analyze Root Causes, Major Flashpoints, and Future Predictions.
4. TONE: Write like a distinguished University Professor for academic queries, but act friendly for general chat.
5. MATCH LANGUAGE EXACTLY: If English, answer in English. If Bengali, answer in Bengali.

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
    st.markdown("""
        <style>
        /* 1. Safe Typography Reset (Protects Streamlit Material Icons) */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        
        /* 🔴 ONLY target text tags so we don't break Streamlit's arrow icons! */
        p, h1, h2, h3, h4, li, .stChatMessage {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
            -webkit-font-smoothing: antialiased !important;
        }
        
        p, .stChatMessage {
            font-size: 15px !important;
            line-height: 1.6 !important;
        }
        
        /* Fix headers */
        h1 { font-size: 32px !important; font-weight: 700 !important; letter-spacing: -0.5px !important; }
        h2 { font-size: 24px !important; font-weight: 600 !important; }
        h3 { font-size: 18px !important; font-weight: 600 !important; }

        /* 2. PERFECT CENTERED Sidebar Header */
        .gstu-sidebar-header {
            margin-top: -15px !important; 
            margin-bottom: 25px !important; 
            display: flex;
            align-items: center;
            justify-content: center !important; /* 🔴 Perfectly Centered */
            width: 100%;
        }
        
        .gstu-home-link {
            text-decoration: none !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important; /* 🔴 Perfectly Centered */
            gap: 12px !important; /* Nice gap between logo and text */
            cursor: pointer !important;
            background: transparent !important;
        }
        
        .gstu-home-text {
            margin: 0 !important;
            font-size: 24px !important;
            font-weight: 900 !important;
            color: white !important;
            letter-spacing: -0.5px !important;
            line-height: 1.2 !important;
            transition: color 0.3s ease !important;
        }
        
        .gstu-home-link:hover .gstu-home-text {
            color: #10a37f !important; /* Premium Green Hover */
        }
        
        .gstu-logo-img {
            width: 46px !important; 
            height: 46px !important; 
            min-width: 46px !important; 
            min-height: 46px !important; 
            border-radius: 50% !important; 
            object-fit: cover !important;
        }
        
        /* 3. Search Bar Spacing Fix */
        div[data-testid="stSidebar"] div[data-testid="stTextInput"] {
            margin-bottom: 20px !important; 
        }
        
        /* 4. Chat Input Box Smoothness */
        div[data-testid="stChatInput"] {
            border-radius: 20px !important;
            border: 1px solid rgba(255,255,255,0.1) !important;
        }

                
        /* 🔴 APPLE / OPENAI GRADE PREMIUM UI ANIMATIONS 🔴 */

                
        /* 1. Sleek Action Buttons (Like ChatGPT) */
        div[data-testid="stButton"] > button {
            border-radius: 12px !important;
            border: 1px solid rgba(16, 163, 127, 0.2) !important;
            background: linear-gradient(145deg, #1e1e1e, #2a2a2a) !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
        }

        div[data-testid="stButton"] > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 8px 15px rgba(16, 163, 127, 0.3) !important;
            border: 1px solid rgba(16, 163, 127, 0.8) !important;
            background: white !important;
            color: white !important;
        }

        /* 2. Glassmorphism Chat Input (Floating effect) */
        div[data-testid="stChatInput"] {
            border-radius: 24px !important;
            border: 1px solid rgba(255,255,255,0.1) !important;
            background: rgba(30, 30, 30, 0.6) !important;
            backdrop-filter: blur(12px) !important;
            box-shadow: 0 -4px 20px rgba(0,0,0,0.05) !important;
            transition: border 0.3s ease, box-shadow 0.3s ease !important;
        }

        div[data-testid="stChatInput"]:focus-within {
            border: 1px solid #10a37f !important;
            box-shadow: 0 0 15px rgba(16, 163, 127, 0.4) !important;
        }

        /* 3. Welcome Message Glow Animation */
        @keyframes textGlow {
            0% { text-shadow: 0 0 10px rgba(16,163,127,0.2); }
            50% { text-shadow: 0 0 20px rgba(16,163,127,0.6); }
            100% { text-shadow: 0 0 10px rgba(16,163,127,0.2); }
        }

        h1 {
            animation: textGlow 3s infinite alternate !important;
        }

        /* 4. General Buttons (The Neon Glow Effect) */
            [data-testid="stButton"] button {
                border-radius: 8px !important;
                border: 1px solid rgba(16, 163, 127, 0.4) !important;
                background: rgba(20, 20, 20, 0.8) !important;
                color: #e0e0e0 !important;
                box-shadow: 0 0 10px rgba(16, 163, 127, 0.1) !important;
                transition: all 0.3s ease-in-out !important;
            }
            
            [data-testid="stButton"] button:hover {
                border-color: #10a37f !important;
                color: #ffffff !important;
                background: rgba(16, 163, 127, 0.1) !important;
                /* 🔴 The Magic Glow */
                box-shadow: 0 0 20px rgba(16, 163, 127, 0.6), 0 0 40px rgba(16, 163, 127, 0.2) !important; 
                transform: translateY(-2px);
            }
            
            [data-testid="stButton"] button:active {
                transform: translateY(1px);
                box-shadow: 0 0 10px rgba(16, 163, 127, 0.4) !important;
            }

        /* 5. FIX: Restore File Uploader Remove (X) Button */
            button[title="Remove file"], button[aria-label="Remove"] {
                display: inline-flex !important;
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
                color: #ff4b4b !important;
                z-index: 9999 !important;
            }
            
            button[title="Remove file"]:hover, button[aria-label="Remove"]:hover {
                background: rgba(255, 75, 75, 0.2) !important;
                color: #ff0000 !important;
                transform: scale(1.1) !important;
                box-shadow: none !important;
                border-color: transparent !important;
            }
            
            /* Ensure uploaded file row stays visible */
            [data-testid="stUploadedFile"] {
                background: rgba(20, 20, 20, 0.6) !important;
                border-radius: 8px !important;
                border: 1px solid rgba(255, 255, 255, 0.1) !important;
            }
        </style>
    """, unsafe_allow_html=True)
    
    # 🔴 The Centered Header Block
    logo_img = f'<img src="data:image/png;base64,{logo_b64}" class="gstu-logo-img">' if logo_b64 else "<span style='font-size: 35px; margin:0;'>🎓</span>"
        
    st.markdown(f"""
        <div class="gstu-sidebar-header">
            <a href="http://localhost:8501" target="_self" class="gstu-home-link">
                {logo_img}
                <div class="gstu-home-text">GSTU IR AI</div>
            </a>
        </div>
    """, unsafe_allow_html=True)

    # Search bar
    search_q = st.text_input("Search", placeholder="🔍 Search projects...", label_visibility="collapsed")
    
    # 🔴 Perfect spacing before the action buttons
    st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)
    
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
        #st.markdown("<br>", unsafe_allow_html=True)
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
        st.markdown("<div class='sidebar-section-title'>🕒 RECENT CHATS</div>", unsafe_allow_html=True)
        if st.session_state.active_chat_title and not any(ch["title"] == st.session_state.active_chat_title for ch in filtered_history):
            st.markdown(f"<div class='recent-chat-btn recent-chat-active'>💬 {st.session_state.active_chat_title[:25]}...</div>", unsafe_allow_html=True)
        for i, past in enumerate(recent_chats):
            title = past["title"]
            is_active = (title == st.session_state.active_chat_title)
            cbk = f"{_cb_key('r', title)}_{i}"
            if st.session_state.selection_mode: st.checkbox(f"💬 {title[:30]}...", key=cbk)
            else:
                if is_active: st.markdown(f"<div class='recent-chat-btn recent-chat-active'>💬 {title[:25]}...</div>", unsafe_allow_html=True)
                else:
                    safe_r_key = f"btn_{cbk}"
                    if st.button(f"💬 {title[:25]}...", key=safe_r_key, use_container_width=True):
                        st.session_state.messages = past["messages"].copy()
                        st.session_state.active_chat_title = title
                        st.rerun()

    # ==============================================================
    # 🛡️ PRIVACY & SECURITY POLICY (Silicon Valley Standard)
    # 🔴 PRIVACY & HELP CENTER BUTTON
    # ==============================================================
    
    st.sidebar.markdown("<br><br>", unsafe_allow_html=True)
    st.sidebar.markdown("---")
    if st.sidebar.button("🛡️ Privacy Policy & Help", use_container_width=True):
        help_privacy_dialog()


# 12. Main Chat Interface
if not vectorstore:
    st.error("⚠️ No Database Found! Please run `python build_db.py` first.")
    st.stop()

llm = get_llm(st.session_state.current_model)

if vectorstore and llm:
    if not st.session_state.messages:
        if not st.session_state.messages:
            # 🔴 CSS to reduce global top padding so everything fits on one screen without scrolling
            st.markdown("""
                <style>
                .block-container { padding-top: 2rem !important; padding-bottom: 1rem !important; }
                </style>
            """, unsafe_allow_html=True)
            
            # Removed extra <br> tags and reduced margins
            st.markdown("<h1 style='text-align: center; margin-top: -15px;'>Welcome to GSTU IR Ecosystem ✨</h1>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; opacity: 0.7; margin-bottom: 20px;'>Your personal AI assistant for syllabus, research, smart notes, and mock presentations.</p>", unsafe_allow_html=True)
            
    
    # 🔴 ROLE-BASED QUICK ACTIONS (Exactly 3 Aesthetic Buttons)
        s_col1, s_col2, s_col3 = st.columns(3)
        
        if st.session_state.user_role == "Student":
            if s_col1.button("📝 Smart Notes", use_container_width=True): st.session_state.quick_query = "Generate clear smart notes based on the syllabus."
            if s_col2.button("🎯 Mock Exam", use_container_width=True): st.session_state.quick_query = "Ask me a tough analytical question for my upcoming exam."
            if s_col3.button("⏰ Class Info", use_container_width=True): st.session_state.quick_query = "Show me the recommended books and routine."
            
        elif st.session_state.user_role == "Faculty":
            if s_col1.button("📋 Generate Quiz", use_container_width=True): st.session_state.quick_query = "Generate a 5-question MCQ quiz based on the latest geopolitical events."
            if s_col2.button("📊 Analyze Papers", use_container_width=True): st.session_state.quick_query = "Act as a grading assistant. What are the key points to look for in a thesis about US-China trade war?"
            if s_col3.button("⏰ Class Info", use_container_width=True): st.session_state.quick_query = "Show me the recommended books and routine."
            
        else: # For Admin
            if s_col1.button("📝 Smart Notes", use_container_width=True): st.session_state.quick_query = "Generate clear smart notes based on the syllabus."
            if s_col2.button("📋 Generate Quiz", use_container_width=True): st.session_state.quick_query = "Generate a 5-question MCQ quiz based on the latest geopolitical events."
            if s_col3.button("📈 Revenue & Analytics", use_container_width=True):
                admin_dashboard_dialog()

        
    # --- STUDENT ANALYTICS DASHBOARD ---
    if st.session_state.user_role == "Student":
        # 🔴 Feature Flag Check: Completely invisible if False
        if ENABLE_AGENTIC_FEATURES:
            render_study_logger(user_id)
            
            with st.expander("📈 View Your Academic Progress", expanded=False):
                try:
                    socket.setdefaulttimeout(2)
                    socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
                    
                    render_analytics_dashboard(user_id)
                    
                except OSError:
                    st.warning(
                        "🔌 **Offline Mode Active:** Cannot sync progress data with the cloud database right now. "
                        "Please connect to the internet to view your live analytics.", 
                        icon="⚠️"
                    )
                except Exception as e:
                    st.error(f"⚠️ **Dashboard Error:** Could not load analytics. Details: {e}")
                # (No 'else' block here. If flag is False, the UI shows absolutely nothing.)


    # মডেল সিলেক্টর এখন ৩টা বাটনের ঠিক নিচে, একদম সেন্টারে!
    st.markdown("<br>", unsafe_allow_html=True)
    
    
    # 🔴 THE MODEL HUB (User Selects Task-Specific Engine)
    m_col1, m_col2, m_col3 = st.columns([0.25, 0.5, 0.25])
    with m_col2:
        model_options = {
            "⚡ Fast Engine (Llama 3 - 8B)": "llama-3.1-8b-instant",
            "💻 Offline Mode (GPT4All Local)": "local-gpt4all", # 🔴 NEW LOCAL ENGINE
            "🌐 Web & Research (Gemini 2.5 Flash)": "gemini-2.5-flash",
            "🐉 Qwen Core (Qwen 2.5 - 72B)": "qwen/qwen-2.5-72b-instruct",
            "🎓 Deep Logic (Llama 3 - 70B)": "llama-3.3-70b-versatile",
            "🧠 Adv. Analysis (Gemini 2.5 Pro)": "gemini-2.5-pro",
            "🚀 GPT-4o (OpenAI Premium)": "openai/gpt-4o-2024-08-06",
            "🔬 DeepSeek R1 (OpenRouter - Free)": "deepseek/deepseek-r1:free",
            "🚀 GPT-4o Mini (OpenRouter)": "openai/gpt-4o-mini",
            "🎨 Claude 3.5 Sonnet (Anthropic)": "anthropic/claude-3.5-sonnet"
        }
        
        # Get current model name for default index
        current_model_name = "⚡ Fast Engine (Llama 3 - 8B)" # fallback
        for key, val in model_options.items():
            if val == st.session_state.get("current_model"):
                current_model_name = key
                break
                
        selected_model_ui = st.selectbox(
            "Select AI Engine",
            list(model_options.keys()),
            index=list(model_options.keys()).index(current_model_name) if current_model_name in model_options else 0,
            label_visibility="collapsed"
        )
        
        new_model_val = model_options[selected_model_ui]

        if new_model_val != st.session_state.current_model:
            st.session_state.current_model = new_model_val
            st.rerun()


    for index, msg in enumerate(st.session_state.messages):
        if not isinstance(msg, dict) or "role" not in msg or "content" not in msg: continue

        avatar = "🧑‍💻" if msg["role"] == "user" else "✨"
        with st.chat_message(msg["role"], avatar=avatar):
            if msg["role"] == "assistant": st.markdown(msg["content"], unsafe_allow_html=True)
            else: st.markdown(msg["content"])
            
            if msg["role"] == "assistant":
                # Spacing for standard UI
                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                act_cols = st.columns([0.08, 0.08, 0.08, 0.08, 0.08, 0.8], gap="small")
                
                # 🔊 Listen/Stop Toggle Button (Pure HTML/JS integration)
                with act_cols[0]:
                    import re
                    is_bn_msg = bool(re.search(r'[\u0980-\u09FF]', msg["content"]))
                    tts_lang = "bn-BD" if is_bn_msg else "en-US"
                    safe_speech = json.dumps(msg["content"])
                    st.components.v1.html(
                        f"""
                        <script>
                        function toggleVoice() {{
                            if (window.speechSynthesis.speaking) {{
                                window.speechSynthesis.cancel();
                            }} else {{
                                let msg = new SpeechSynthesisUtterance('{safe_speech}');
                                msg.lang = '{tts_lang}'; // 🔴 Dynamically switches between Bengali and English
                                window.speechSynthesis.speak(msg);
                            }}
                        }}
                        </script>
                        <button onclick="toggleVoice()" title="Listen / Stop" style="background:transparent; border:none; cursor:pointer; font-size:16px; padding:0; margin:0; filter: grayscale(100%);">🔊</button>
                        """, height=25
                    )
                    
                with act_cols[1]: 
                    if st.button("👍", key=f"up_{index}", help="Good response"): st.toast("✅ Positive feedback logged.")
                with act_cols[2]: 
                    if st.button("👎", key=f"down_{index}", help="Bad response"): feedback_dialog(index)
                with act_cols[3]:
                    if st.button("🔄", key=f"regen_{index}", help="Regenerate"):
                        st.session_state.messages.pop()
                        st.rerun()
                with act_cols[4]:
                    if st.button("📑", key=f"copy_{index}", help="Copy text"): st.toast("📋 Copied to clipboard!")
                with act_cols[5]:
                    app_url = os.getenv("APP_URL", "https://gstu-ir-ai.streamlit.app")
                    share_html = f"""
                        <div style="display: flex; align-items: center; justify-content: center; height: 35px; width: 35px;">
                            <script>function shareApp() {{ if (navigator.share) navigator.share({{title: 'GSTU IR AI', url: '{app_url}'}}).catch(console.error); }}</script>
                            <button onclick="shareApp()" title="Share AI" style="background:transparent; border:none; cursor:pointer; font-size:20px;">📤</button>
                        </div>
                    """
                    st.components.v1.html(share_html, height=35, width=35)

    st.markdown("<br>", unsafe_allow_html=True)


    # 🔴 FUNCTIONAL MULTIMODAL BOX (Camera, Files, Voice)
    with st.expander("📎 Attach Files, Camera & Voice Notes"):
        tab_file, tab_cam, tab_voice = st.tabs(["📂 Files & Gallery", "📸 Camera", "🎤 Voice Note"])
        
        # 🔴 RESTORED: File Uploader Box
        with tab_file:
            st.markdown("### 📄 Upload Documents for Analysis")
            up_files = st.file_uploader("Upload PDFs or Images (Max 10MB)", type=["pdf", "png", "jpg", "jpeg"], accept_multiple_files=True)
            if up_files:
                st.success(f"✅ {len(up_files)} file(s) attached and ready for analysis.")

        MAX_UPLOAD_MB = 10
        MAX_AVATAR_MB = 2

        def validate_file_size(file_obj, max_mb: float) -> bool: ...

        def validate_image_content(data: bytes) -> bool:
            """Check magic bytes — not just the extension."""
            return (data[:3] == b"\xff\xd8\xff" or    # JPEG
                    data[:4] == b"\x89PNG"      or    # PNG
                    data[:4] in (b"GIF8",))           # GIF
                
        with tab_cam:
            cam_pic = st.camera_input("Take a photo using webcam/phone")
            if cam_pic: 
                st.success("✅ Photo captured and attached.")
                
        with tab_voice:
            voice_data = st.audio_input("Record your Voice Command")
        
        # Initialize persistent voice draft state
        if "voice_draft" not in st.session_state:
            st.session_state.voice_draft = ""
            
        if voice_data and not st.session_state.voice_draft:
            if st.button("🎙️ Process Audio", use_container_width=True):
                with st.spinner("Translating voice to text..."):
                    try:
                        # সাময়িকভাবে অডিও ফাইলটি লোকাল ড্রাইভে সেভ করা
                        # FIXED
                        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                            tmp.write(voice_data.getbuffer())
                            temp_audio_path = tmp.name  # Unique per invocation
                        
                        # ফাইল সাইজ মেপে মেগাবাইটে কনভার্ট করা
                        file_size_mb = os.path.getsize(temp_audio_path) / (1024 * 1024)
                        MAX_LOCAL_SIZE_MB = 5.0 # ৫ মেগাবাইটের নিচে হলে লোকাল প্রসেস হবে
                        
                        transcription = ""
                        
                        # === ১. লোকাল ইঞ্জিন রান (ছোট ফাইলের জন্য) ===
                        if file_size_mb <= MAX_LOCAL_SIZE_MB:
                            st.toast(f"🔒 Local Engine Active ({file_size_mb:.2f} MB). Processing offline...", icon="🔌")
                            try:
                                from faster_whisper import WhisperModel
                                # CPU এর জন্য int8 অপ্টিমাইজড করে লোড করা হলো যাতে ক্র্যাশ না করে
                                model = WhisperModel("base", device="cpu", compute_type="int8")
                                segments, info = model.transcribe(temp_audio_path, beam_size=5)
                                transcription = " ".join([segment.text for segment in segments])
                                st.toast("💡 Processed via: Local (faster-whisper)", icon="✅")
                            except ImportError:
                                st.error("⚠️ Local faster-whisper not configured properly. Falling back to Cloud API...")
                                file_size_mb = 999 # ফোর্সড ক্লাউড ফলব্যাক
                                
                        # === ২. ক্লাউড ইঞ্জিন রান (বড় ফাইলের জন্য বা ফলব্যাক) ===
                        if file_size_mb > MAX_LOCAL_SIZE_MB:
                            st.toast(f"⚡ Cloud Engine Active. Routing to Groq Cloud API...", icon="🌐")
                            from groq import Groq
                            
                            groq_api_key = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY")
                            if not groq_api_key:
                                st.error("⚠️ GROQ_API_KEY missing! Cannot process via cloud.")
                            else:
                                client = Groq(api_key=groq_api_key)
                                with open(temp_audio_path, "rb") as audio_file:
                                    transcription = client.audio.transcriptions.create(
                                        file=(temp_audio_path, audio_file.read()),
                                        model="whisper-large-v3",
                                        response_format="text"
                                    ).strip()
                                st.toast("💡 Processed via: Cloud (Groq Whisper API)", icon="🚀")
                                
                        # সাময়িকভাবে তৈরি করা অডিও ফাইলটি ডিলিট করে ক্লিন করা
                        if os.path.exists(temp_audio_path):
                            os.remove(temp_audio_path)
                            
                        # টেক্সট ড্রাফট হিসেবে সেভ করে স্ক্রিন রিফ্রেশ দেওয়া (রিভিউ এর জন্য)
                        if transcription:
                            st.session_state.voice_draft = transcription.strip()
                            st.rerun() 
                        else:
                            st.error("⚠️ Failed to transcribe audio. No text recovered.")
                            
                    except Exception as e:
                        if os.path.exists(temp_audio_path):
                            os.remove(temp_audio_path)
                        st.error(f"⚠️ Audio processing pipeline error: {str(e)}")
                        
        # Render the Review & Edit Box if a draft exists
        if st.session_state.get("voice_draft"):
            st.info("📝 Review and edit your transcribed text before sending:")
            edited_text = st.text_area("Transcribed Command:", value=st.session_state.voice_draft, height=100)
            
            col_v1, col_v2 = st.columns(2)
            with col_v1:
                if st.button("❌ Discard", use_container_width=True):
                    st.session_state.voice_draft = ""
                    st.rerun()
            with col_v2:
                if st.button("🚀 Send to Agent", use_container_width=True, type="primary"):
                    st.session_state.quick_query = edited_text
                    st.session_state.voice_draft = "" # Clear draft state
                    st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    
    # 🔴 1. Smart Input Interceptor (ভয়েস কমান্ড রিসিভ করবে)
    temp_query = st.chat_input("Message GSTU Assistant...")
    if st.session_state.get("quick_query"):
        user_query = st.session_state.quick_query
        st.session_state.quick_query = None # Clear after catching
    else:
        user_query = temp_query


    # 🔴 2. File Extractor (পিডিএফ বা ছবি থেকে টেক্সট বের করে রাখবে)
    context_from_files = ""
    up_files = [] # Initialize safety variable
    
    if 'up_files' in locals() and up_files:
        with st.spinner("📄 Analyzing documents..."):
            for f in up_files:
                if f.type == "application/pdf":
                    try:
                        import pypdf
                        for page in pypdf.PdfReader(f).pages: context_from_files += page.extract_text() + "\n"
                    except: pass
                elif "image" in f.type:
                    context_from_files += f"\n[User attached image: {f.name}]\n"

    
    # =====================================================================
    # 📝 AI LEARNING FEEDBACK FORM
    # =====================================================================
    @st.dialog("🧠 Help Astra Core Learn")
    def feedback_dialog(msg_index):
        st.markdown("### Why did you dislike this response?")
        feedback_reason = st.text_area("Provide specific details to train the model:", placeholder="e.g., The geopolitical facts were outdated...")
        if st.button("Submit Feedback to Core", type="primary", use_container_width=True):
            # Phase 2: Save to 'ai_training_logs' in Supabase
            st.success("✅ Feedback securely logged! The Zenith routing engine will adjust future responses.")
            time.sleep(1.5)
            st.rerun()


    # =====================================================================
    # 💬 CHAT INPUT & HISTORY BUG FIX
    # =====================================================================
    if user_query:
        # 🔴 CREATE NEW HISTORY INSTANCE IF NONE EXISTS
        if not st.session_state.active_chat_title:
            new_title = user_query[:25] + "..."
            st.session_state.active_chat_title = new_title
            st.session_state.chat_history.insert(0, {
                "title": new_title,
                "folder": None,
                "messages": []
            })

        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user", avatar="👨🏻‍💻"):
            # ChatGPT Style Expander for long prompts (> 300 chars)
            if len(user_query) > 300:
                st.markdown(user_query[:150] + "...")
                with st.expander("🔽 Show full prompt"):
                    st.markdown(user_query)
            else:
                st.markdown(user_query)

        
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        latest_q = st.session_state.messages[-1]["content"]
        res_text = None  

        with st.chat_message("assistant", avatar="✨"):
            creator_keywords = ["created", "made", "inventor", "founded", "developer", "creator", "founder", "built"]
        
        # 🧠 SMART ROUTER ENGINE (Auto-detects course from user query)
            def route_query(query):
                q = query.lower()
                if any(x in q for x in ["research", "methodology", "social", "hypothesis", "weak points"]): return "IR-210"
                elif any(x in q for x in ["foreign policy", "diplomacy", "policy"]): return "IR-202"
                elif any(x in q for x in ["french", "france", "translate", "alphabet"]): return "French"
                elif any(x in q for x in ["intro", "theory", "realism"]): return "IR-200"
                else: return "General"
            
            detected_course = route_query(latest_q)
            # 🔴 UPDATE 1: Expanded greetings to catch "hey there", "what's up" etc.
            casual_greetings = ["hi", "hello", "hey", "hallo", "helo", "hi there", "hey there", "what's up", "হ্যালো", "হাই", "কেমন আছো", "কেমন আছেন"]
            
            latest_q_lower = latest_q.strip().lower()

            if any(kw in latest_q_lower for kw in creator_keywords):
                res_text = (
                    "The inventor and head developer of this AI model is **Tashfin Yousuf**.<br><br>"
                    "<a href='https://tashfinzportfolio.infy.uk/' target='_blank' rel='noopener noreferrer' "
                    "style='display: inline-block; background-color: #10a37f; color: white; padding: 10px 20px; "
                    "border-radius: 8px; text-decoration: none; font-weight: 600; font-family: sans-serif; "
                    "border: 1px solid #0f916f; box-shadow: 0 2px 5px rgba(0,0,0,0.2);'>📄 View / Download Tashfin's CV</a>"
                )
                st.markdown(res_text, unsafe_allow_html=True)
            
            # 🔴 UPDATE 2: Smart Greeting Bypass (Checks if it STARTS with a greeting)
            elif any(latest_q_lower.startswith(g) for g in casual_greetings):
                res_text = "Hello! 👋 I am the Elite GSTU IR AI Assistant. How can I help you with your academic research, theories, syllabus, or geopolitical analysis today?"
                st.markdown(res_text)

            # 🔴 === 🔌 SMART OFFLINE ENGINE (Powered by GPT4All) === 🔴
            elif (lambda: __import__("socket").setdefaulttimeout(2) or __import__("socket").socket(__import__("socket").AF_INET, __import__("socket").SOCK_STREAM).connect_ex(("8.8.8.8", 53)) != 0)():
                st.toast("⚠️ Offline Mode Active. Local AI Engine intercepting...", icon="🔌")
                
                # Ensure the user has actually selected the Local LLM, otherwise clouds will crash
                if st.session_state.current_model != "local-gpt4all":
                    res_text = "🔌 **Internet connection lost.** \n\nTo generate intelligent answers offline, please select **'Offline Mode (GPT4All Local)'** from the AI Engine dropdown menu above."
                    st.error(res_text)
                else:
                    with st.spinner("Analyzing locally with GPT4All..."):
                        try:

                            # 1. Fetch Local Data (STRICT ROUTING)
                            def route_query(query):
                                q = query.lower()
                                if any(x in q for x in ["research", "methodology", "social", "hypothesis"]): return "IR-210"
                                elif any(x in q for x in ["foreign policy", "diplomacy", "policy"]): return "IR-202"
                                elif any(x in q for x in ["french", "france", "translate", "alphabet"]): return "French"
                                elif any(x in q for x in ["intro", "theory", "realism"]): return "IR-200"
                                else: return "General"
                            
                            detected_course = route_query(latest_q)
                            
                            # STRICT FILTER: NO FALLBACK ALLOWED
                            if detected_course != "General":
                                st.toast(f"🔌 Offline: Routed strictly to {detected_course}", icon="🧠")
                                db_context, db_docs = search_context(latest_q, active_course=detected_course)
                            else:
                                db_context, db_docs = search_context(latest_q, active_course=None)
                            
                            db_sources = {}
                            if db_docs:
                                for doc in db_docs:
                                    src_name = os.path.basename(doc.metadata.get('source', 'Unknown'))
                                    page = doc.metadata.get('page')
                                    if src_name not in db_sources: db_sources[src_name] = set()
                                    if page is not None: db_sources[src_name].add(str(page + 1))
                                    
                            else:
                                db_context, db_docs = search_context(latest_q, active_course=None)
                            
                            db_sources = {}
                            for doc in db_docs:
                                src_name = os.path.basename(doc.metadata.get('source', 'Unknown'))
                                page = doc.metadata.get('page')
                                if src_name not in db_sources: db_sources[src_name] = set()
                                if page is not None: db_sources[src_name].add(str(page + 1))

                            # =====================================================================
                            # 🧠 SMART LANGUAGE & CULTURAL ROUTER 
                            # =====================================================================
                            import re
                            is_bengali = bool(re.search(r'[\u0980-\u09FF]', latest_q))
                            
                            if is_bengali:
                                # 🇧🇩 Bengali Academic Persona
                                system_instruction = """তুমি হচ্ছো GSTU (গোপালগঞ্জ বিজ্ঞান ও প্রযুক্তি বিশ্ববিদ্যালয়) এর ইন্টারন্যাশনাল রিলেশনস (IR) ডিপার্টমেন্টের একজন এলিট এআই অ্যাসিস্ট্যান্ট। 
তোমার প্রধান কাজ হলো শুধুমাত্র নিচের কনটেক্সটের ওপর ভিত্তি করে একটি অত্যন্ত বিস্তারিত এবং অ্যাকাডেমিক উত্তর প্রদান করা।

CRITICAL INSTRUCTIONS (BANGLA):
১. উত্তরটি অবশ্যই ১০০% বিশুদ্ধ, প্রমিত এবং ফর্মাল বাংলায় হতে হবে। কোনোভাবেই ইংরেজি থেকে আক্ষরিক বা যান্ত্রিক অনুবাদ (Robotic translation) করা যাবে না।
২. বাংলাদেশের লোকাল টোন এবং অ্যাকাডেমিক স্টাইল বজায় রাখবে।
৩. পয়েন্ট এবং বোল্ড টেক্সট ব্যবহার করে উত্তরটি সুন্দরভাবে সাজাবে।
৪. এক লাইনের ছোট উত্তর দেওয়া সম্পূর্ণ নিষেধ। বিস্তারিত ব্যাখ্যা করবে।"""

                            else:
                                # 🇬🇧 English Academic Persona
                                system_instruction = """You are the Elite GSTU AI Assistant for the International Relations (IR) Department. 
Your task is to provide a comprehensive, highly detailed, and academic response based ONLY on the provided context.

CRITICAL INSTRUCTIONS (ENGLISH):
1. EXPAND & ELABORATE: Provide a detailed, multi-paragraph explanation. Do NOT give short one-liner answers.
2. STRUCTURE: Use bullet points and bold text to structure your answer professionally.
3. TONE: Maintain a highly academic and analytical tone suitable for university-level research."""

                            # 🔴 Injecting the dynamic instruction into the final prompt
                            offline_prompt = f"""{system_instruction}

Context:
{db_context[:800]} 

User Question: {latest_q}

Detailed Analysis:
"""
                            
                            response = llm.invoke(offline_prompt)
                            answer = str(response.content).strip()
                            
                            # 3. Maintain Beautiful Source UI
                            source_text = "\n\n<details><summary><b>📚 View Local Sources</b></summary>\n<ul>"
                            for src, pages in db_sources.items():
                                if pages:
                                    sorted_pages = sorted(list(pages), key=lambda x: int(x) if x.isdigit() else str(x))
                                    page_str = ", ".join(sorted_pages)
                                    source_text += f"<li>📄 {src} <i>(Page: {page_str})</i></li>"
                                else: source_text += f"<li>📄 {src}</li>"
                            source_text += "</ul></details>"
                            
                            res_text = f"🔌 **[Offline Mode Active]**\n\n{answer}{source_text}"
                            st.markdown(res_text, unsafe_allow_html=True)
                            
                        except Exception as e:
                            res_text = f"⚠️ **GPT4All Connection Error:** Please ensure GPT4All app is running in the background and 'Enable Web Server' is ON in its settings. \n\nError details: `{str(e)}`"
                            st.error(res_text)


            # 🌐 === ONLINE CLOUD ENGINE === 🌐
            else:
                with st.spinner(f"Analyzing with {'Deep Think (70B)' if '70b' in st.session_state.current_model else 'Fast (8B)'}..."):
                
                        import re
                        is_bengali = bool(re.search(r'[\u0980-\u09FF]', latest_q))
                        active_model = st.session_state.current_model
                        
                        # 🔴 SMART AUTO-ROUTING
                        if is_bengali and "llama" in active_model.lower():
                            st.toast("🔄 Llama doesn't support Bengali perfectly. Auto-routing to Gemini...", icon="⚡")
                            google_api_key = os.getenv("GOOGLE_API_KEY") or st.secrets.get("GOOGLE_API_KEY")
                            from langchain_google_genai import ChatGoogleGenerativeAI
                            llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.2, google_api_key=google_api_key)
                        else:
                            llm = get_llm(active_model)
                
                        # 🔴 THE HYBRID RAG MAGIC STARTS HERE
                        # 1. Get Data from Local DB (Books/PDFs) using STRICT ROUTER
                        def route_query(query):
                            q = query.lower()
                            if any(x in q for x in ["research", "methodology", "social", "hypothesis"]): return "IR-210"
                            elif any(x in q for x in ["foreign policy", "diplomacy", "policy"]): return "IR-202"
                            elif any(x in q for x in ["french", "france", "translate", "alphabet"]): return "French"
                            elif any(x in q for x in ["intro", "theory", "realism"]): return "IR-200"
                            else: return "General"
                        
                        detected_course = route_query(latest_q)
                        
                        # STRICT FILTER: NO FALLBACK TO RANDOM COURSES
                        if detected_course != "General":
                            st.toast(f"🔍 Auto-Routed to strict {detected_course} context...", icon="🧠")
                            db_context, db_docs = search_context(latest_q, active_course=detected_course)
                        else:
                            db_context, db_docs = search_context(latest_q, active_course=None)
                        
                        db_sources = {}
                        if db_docs:
                            for doc in db_docs:
                                src_name = os.path.basename(doc.metadata.get('source', 'Unknown'))
                                page = doc.metadata.get('page')
                                if src_name not in db_sources: db_sources[src_name] = set()
                                if page is not None: db_sources[src_name].add(str(page + 1))

                        # 2. Smart Trigger for Live Web Search
                        rt_keywords = [
                            "current", "latest", "now", "today", "recent", "update", "updates", "2024", "2025", "2026", 
                            "news", "geopolitics", "situation", "war", "conflict", "crisis",
                            "বর্তমান", "সাম্প্রতিক", "আজকের", "এখনকার", "খবর", "নিউজ", "পরিস্থিতি", "অবস্থা", "আপডেট"
                        ]
                        needs_web = any(kw in latest_q.lower() for kw in rt_keywords)

                        web_context = "No live web search triggered."
                        web_links = []

                        if needs_web:
                            # 🌐 TAVILY ENGINE TRIGGERED (The Free AI Search)
                            tavily_key = os.getenv("TAVILY_API_KEY") or st.secrets.get("TAVILY_API_KEY")
                            
                            if not tavily_key:
                                st.error("⚠️ TAVILY_API_KEY is missing in .env! Get it for free at tavily.com")
                                st.stop()
                                
                            with st.spinner("🌐 Fetching live global data..."):
                                try:
                                    from tavily import TavilyClient
                                    tavily_client = TavilyClient(api_key=tavily_key)
                
                                # Advanced search targets high-quality sources and digs deeper
                                    tavily_res = tavily_client.search(
                                        query=latest_q, 
                                        search_depth="advanced", 
                                        max_results=8,
                                        include_answer=True,

                                        # 🔴 The Garbage Collector Filter: Blocks social media and bad blogs
                                        exclude_domains=["instagram.com", "facebook.com", "x.com", "twitter.com", "reddit.com", "quora.com", "tiktok.com", "blog.greeden.me"]
                                    )
                                    
                                    web_context = f"Tavily AI Summary: {tavily_res.get('answer', '')}\n\n"
                                    for r in tavily_res.get('results', []):
                                        # Filtering to ensure highly legitimate data processing
                                        web_context += f"Source: {r.get('title', 'Web')}\nSnippet: {r.get('content', '')}\n\n"
                                        web_links.append(r.get('url', ''))
                                    
                                        
                                except Exception as e:
                                    st.warning(f"⚠️ Live search failed: {e}. Relying solely on local database.")

                        # 🧠 GROQ SYNTHESIS (Llama 3 acting as the Master Brain)
                        prior_messages = st.session_state.messages[:-1]
                        history_ctx = build_history_context(prior_messages)
                        contextual_query = (f"{latest_q}\n\n[Conversation context:\n{history_ctx}]") if history_ctx != "No prior conversation." else latest_q
                    
                        # =====================================================================
                        # 🧠 THE ULTIMATE TIME-AWARE & LANGUAGE-LOCKED ROUTER
                        # =====================================================================
                        import re
                        has_bengali_script = bool(re.search(r'[\u0980-\u09FF]', latest_q))
                        
                        # 1. CORE PERSONA (Dynamically assigned)
                        if has_bengali_script:
                            system_persona = """তুমি হচ্ছো GSTU (গোপালগঞ্জ বঙ্গবন্ধু শেখ মুজিবুর রহমান বিজ্ঞান ও প্রযুক্তি বিশ্ববিদ্যালয়) এর ইন্টারন্যাশনাল রিলেশনস (IR) ডিপার্টমেন্টের চিফ জিওপলিটিক্যাল অ্যানালিস্ট এবং এলিট এআই অ্যাসিস্ট্যান্ট।
তোমার টোন হবে একজন সম্মানীয় বিশ্ববিদ্যালয়ের প্রফেসরের মতো—অত্যন্ত যুক্তিনির্ভর, অ্যাকাডেমিক এবং গোছানো।"""
                        else:
                            system_persona = """You are the Elite AI Assistant & Chief Geopolitical Analyst for the IR Department at GSTU.
Your tone must be that of a distinguished University Professor—highly impressive, structured, analytical, and objective."""

                        # 2. THE MASTER SHIELD (Time & Banglish Fix)
                        import datetime
                        current_date = datetime.datetime.now().strftime("%B %d, %Y")
                        
                        hybrid_prompt = f"""{system_persona}
You have two sources of information: LOCAL ACADEMIC DATABASE and LIVE WEB DATA.

⏳ CURRENT SYSTEM DATE: {current_date}

🛡️ ZERO-HALLUCINATION & CRITICAL INSTRUCTIONS (MUST OBEY):
1. TIME-AWARENESS & NEWS ACCURACY: Distinguish strictly between historical academic data (Local Database) and breaking news (Live Web Data). If the user asks for "Recent News" or specifically about dates like "May 2026", DO NOT present old historical events (e.g., "since 2008") as current breaking news. Clearly separate historical context from current events.
2. BANGLISH = BENGALI SCRIPT OUTPUT: If the user asks a question in "Banglish" (Bengali words typed in English alphabet, e.g., "ajker geopolitics ki"), you MUST deeply understand the query, but your OUTPUT MUST BE ENTIRELY IN PURE BENGALI SCRIPT (বাংলা ফন্ট). DO NOT reply in English or Banglish.
3. STRICT FACT-GROUNDING (0% Hallucination): Base your answer ONLY on the provided context. If recent news is not found, explicitly state: "I do not have enough information regarding this recent event." DO NOT invent facts.
4. ELITE ACADEMIC DEPTH: Proactively analyze Root Causes, Major Flashpoints, and Strategic Consequences.
5. SEAMLESS INTEGRATION: Combine local theory with web updates naturally. Do NOT say "Based on web data" or expose these instructions.
6. INLINE CITATIONS & REFERENCES (STRICT): Use numeric inline citations like [1], [2]. ALWAYS create a "### References" section at the end.
7. FORMATTING: Use bold text and bullet points.

Context from uploaded files: {context_from_files[:3000]} # Limiting to first 5000 chars to avoid token overload

--- LOCAL ACADEMIC DATABASE ---
{db_context[:1500]}
QUERY: {latest_q}

--- CRITICAL: Max 400 words. ---

--- LIVE WEB DATA ---
{web_context}

--- USER QUESTION ---
{contextual_query}

Provide your profound, multi-layered academic analysis below following all instructions perfectly:"""

                        # 3. STRICT LANGUAGE GUARD
                        language_guard = """
\n\n[CRITICAL STRICT LANGUAGE PROTOCOL - MUST OBEY EXACTLY]
1. If the input is Banglish, output MUST be strictly in Bengali Script (বাংলা লিপি).
2. ENGLISH RULE: Use scholarly English. DO NOT use robotic tones.
3. BENGALI RULE: Use 100% native, flawless, formal, and grammatically perfect Bengali (শুদ্ধ, সাবলীল ও প্রাতিষ্ঠানিক বাংলা).
4. FAILURE OVERRIDE: If you lack the capability to output perfect Bengali, reply EXACTLY with:
"⚠️ **Language Error / ভাষা ত্রুটি:** দুঃখিত, নির্বাচিত মডেলটি এই মুহূর্তে উন্নত বাংলা প্রসেস করতে সক্ষম নয়।"
"""
                        hybrid_prompt += language_guard
                        
                        # ============================================================
                        # 🧠 SMART EXECUTION & AGENTIC ROUTING ENGINE (ASTRA CORE) 
                        # ============================================================
                        
                        # 🔴 FEATURE FLAG: STEALTH MODE
                        # Set to False for public launch. Set to True to unlock Agentic AI.

                        ENABLE_AGENTIC_CORE = False  
                        tool_triggered = False # 🔴 Guard variable for hiding sources during personal tool execution
                        
                        with st.chat_message("assistant", avatar="✨"):
                            think_status = st.status("💭 Astra Core is analyzing...", expanded=True)
                            think_status.write("🔍 Evaluating query complexity...")
                            
                            try:
                                if ENABLE_AGENTIC_CORE:
                                    from agent_tools import astra_core_tools
                                    from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
                                    
                                    llm_with_tools = llm.bind_tools(astra_core_tools)
                                    initial_messages = [HumanMessage(content=hybrid_prompt)]
                                    initial_response = llm_with_tools.invoke(initial_messages)
                                    
                                    if hasattr(initial_response, 'tool_calls') and initial_response.tool_calls:
                                        tool_triggered = True # 🔴 Tool detected! We will disable citations below.
                                        think_status.write("⚙️ Autonomous Agent triggered. Routing to internal tools...")
                                        initial_messages.append(initial_response)
                                        
                                        for tool_call in initial_response.tool_calls:
                                            tool_name = tool_call['name']
                                            tool_args = tool_call['args']
                                            
                                            if tool_name == "analyze_student_progress" and "user_id" not in tool_args:
                                                tool_args["user_id"] = user_id
                                                
                                            think_status.write(f"🛠️ Executing `{tool_name}` from GSTU Database...")
                                            tool_func = next((t for t in astra_core_tools if t.name == tool_name), None)
                                            if tool_func:
                                                tool_result = tool_func.invoke(tool_args)
                                                initial_messages.append(ToolMessage(content=str(tool_result), tool_call_id=tool_call['id']))
                                            else:
                                                initial_messages.append(ToolMessage(content="Tool execution failed.", tool_call_id=tool_call['id']))
                                                
                                        think_status.write("🧠 Tool data collected. Formulating final response...")
                                        think_status.update(label="💡 Agentic Analysis Complete", state="complete", expanded=False)
                                        
                                        def agent_stream_generator():
                                            if st.session_state.current_model == "local-gpt4all":
                                                response = llm.invoke(initial_messages)
                                                words = str(response.content).split(" ")
                                                for word in words:
                                                    yield word + " "
                                                    time.sleep(0.03)
                                            else:
                                                for chunk in llm.stream(initial_messages): 
                                                    yield chunk.content
                                                    
                                        answer = st.write_stream(agent_stream_generator())
                                        
                                    else:
                                        if needs_web: think_status.write("🌐 Aggregating live global datasets...")
                                        think_status.write("⚙️ Formulating strategic response...")
                                        think_status.update(label="💡 Analysis Complete", state="complete", expanded=False)
                                        

                                # 🌊 SMART STREAMING ENGINE (Handles both Cloud & Local GPT4All)
                                answer = "" # 🔴 FIX: Initializing variable first to prevent NameError
                
                                try:
                                    def stream_generator():
                                        # 1. Fake Streaming for Local GPT4All
                                        if st.session_state.current_model == "local-gpt4all":
                                            response = llm.invoke(hybrid_prompt)
                                            words = str(response.content).split(" ")
                                            for word in words:
                                                yield word + " "
                                                time.sleep(0.03)
                                                
                                        # 2. Native Streaming for Cloud Models (Gemini, Llama etc.)
                                        else:
                                            for chunk in llm.stream(hybrid_prompt):
                                                yield chunk.content
                                                
                                    # Executing the stream
                                    answer = st.write_stream(stream_generator())
                                    
                                except Exception as api_error:
                                    # 🔴 FALLBACK: If primary model fails, auto-route to backup Llama 3
                                    st.toast("⚠️ Primary engine error. Auto-routing to backup engine...", icon="🔄")
                                    
                                    try:
                                        fallback_key = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY")
                                        from langchain_groq import ChatGroq
                                        fallback_llm = ChatGroq(model_name="llama-3.1-8b-instant", temperature=0.1, groq_api_key=fallback_key)
                                        
                                        def fallback_stream():
                                            for chunk in fallback_llm.stream(hybrid_prompt):
                                                yield chunk.content
                                                
                                        answer = st.write_stream(fallback_stream())
                                    except Exception as fallback_err:
                                        # If both engines fail, set a safe answer
                                        answer = f"⚠️ Both Primary and Fallback engines failed. Error: {fallback_err}"
                                        st.error(answer)
                                        
                                    
                                # =====================================================================
                                # 📚 Beautiful Source Formatting (OpenAI Style) - USER PROVIDED CODE
                                # =====================================================================
                                if not tool_triggered: # 🔴 Guard condition
                                    source_text = "\n\n<div style='margin-top: 15px;'><details><summary style='cursor: pointer; font-weight: 600; color: white;'>📚 View Citations & Sources</summary><div style='padding-top: 10px;'>"
                                    
                                    # Add DB Sources
                                    for src, pages in db_sources.items():
                                        if pages:
                                            sorted_pages = sorted(list(pages), key=lambda x: int(x) if x.isdigit() else str(x))
                                            page_str = ", ".join(sorted_pages)
                                            source_text += f"<div style='margin-bottom: 5px;'>📄 <b>{src}</b> <i>(Page: {page_str})</i></div>"
                                        else: 
                                            source_text += f"<div style='margin-bottom: 5px;'>📄 <b>{src}</b></div>"
                                        
                                    # Add Web Sources (Premium Button CSS)
                                    if web_links:
                                        source_text += "<div style='display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px;'>"
                                        for link in web_links:
                                            if link: 
                                                domain = link.split('/')[2].replace('www.', '') if '//' in link else 'Web Source'
                                                source_text += f"<a href='{link}' target='_blank' style='background: rgba(16, 163, 127, 0.1); border: 1px solid rgba(16, 163, 127, 0.4); color: white; padding: 4px 12px; border-radius: 16px; text-decoration: none; font-size: 12px; transition: all 0.2s;'>🔗 {domain}</a>"
                                        source_text += "</div>"
                                            
                                    source_text += "</div></details></br></div>"
        
                                    res_text = answer + source_text
                                    if needs_web and web_links:
                                        res_text += "\n\n*(🌐 Realtime Data Powered by **GSTU AI Search**)*"
                                        
                                    st.markdown(res_text, unsafe_allow_html=True)
                                else:
                                    # 🔴 If tool triggered, just output the answer cleanly without PDF sources
                                    res_text = answer
                                
                            except Exception as e:
                                # 🔴 ACTUAL ERROR TRACKER (No more hiding behind "Sorry")
                                logger.exception("Unexpected error: %s", e)
                                res_text = "⚠️ **System Error.** Please try again or switch AI engines."
                                st.error(res_text)

        if res_text:
            st.session_state.messages.append({"role": "assistant", "content": res_text})
        
        for ch in st.session_state.chat_history:
            if ch["title"] == st.session_state.active_chat_title: ch["messages"] = st.session_state.messages.copy()
        save_chat_history(st.session_state.chat_history)
        # Force Auto-Scroll to Bottom
        st.components.v1.html("""
        """, height=0)
        st.rerun()

    # =====================================================================
    # 📜 ROBUST AUTO-SCROLL MECHANISM (Targets Last Message)
    # =====================================================================
    st.components.v1.html("""
        <script>
            setTimeout(function() {
                const messages = window.parent.document.querySelectorAll('.stChatMessage');
                if (messages.length > 0) {
                    // Scroll exactly to the last chat bubble
                    messages[messages.length - 1].scrollIntoView({
                        behavior: 'smooth', 
                        block: 'end'
                    });
                }
            }, 400); // 400ms delay to ensure Streamlit has finished rendering the chunk
        </script>
    """, height=0)

