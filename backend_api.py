import os
import re
import pypdf
import datetime
from datetime import timedelta
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# 🔴 Core AI Imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_community.vectorstores import SupabaseVectorStore
from supabase import create_client, Client
from groq import Groq
from tavily import TavilyClient
from fastapi import Request
from supabase import create_client, Client
from fastapi.responses import RedirectResponse

# 🟢 Local AI Architect Imports (Agentic Engine)
from memory_db import get_or_create_student_profile
from analytics_engine import generate_progress_report
from core_agents import generate_cgpa_boost_plan


# Load Environment Variables (.env)
load_dotenv()

# 🚀 Initialize FastAPI App
app = FastAPI(title="GSTU AI Assistant", version="1.0.0")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "GSTU AI Assistant Backend is RUNNING! 🚀", "status": "Active"}


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
ENABLE_AGENTIC_CORE = os.getenv("ENABLE_AGENTIC_CORE", "true").lower() == "true"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Supabase Cloud DB Connected!")
except Exception as e:
    supabase = None
    print(f"⚠️ Supabase Connection Error: {e}")


# =====================================================================
# 🧠 Initialize Supabase & Vector Database (PGVECTOR MIGRATION)
# =====================================================================
print("🚀 Booting up Advanced AI Engine & Supabase Vector DB...")

try:
    embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")
    
    if supabase:
        vector_db = SupabaseVectorStore(
            embedding=embeddings,
            client=supabase,
            table_name="gstu_documents",
            query_name="match_documents"
        )
        print("✅ Supabase pgvector DB ready!")
    else:
        raise Exception("Supabase client not initialized")
        
except Exception as e:
    print(f"⚠️ Vector DB Error: {e}")
    vector_db = None

# =====================================================================
# 📦 Data Models
# =====================================================================
class ChatRequest(BaseModel):
    user_id: str = "guest"
    query: str
    model: str = "llama-3.1-8b-instant"
    context_from_files: str = ""

# 🟢 Agentic System Models
class StudentRequest(BaseModel):
    user_id: str
    email: str = None
    name: str = None

# =====================================================================
# 🛠️ HELPER FUNCTIONS
# =====================================================================
def get_llm(model_id: str):
    if "gemini" in model_id.lower(): return ChatGoogleGenerativeAI(model=model_id, temperature=0.1, google_api_key=os.getenv("GOOGLE_API_KEY"))
    elif "llama" in model_id.lower() or "qwen" in model_id.lower(): return ChatGroq(model_name=model_id, temperature=0.1, groq_api_key=os.getenv("GROQ_API_KEY"))
    else: return ChatOpenAI(model_name=model_id, temperature=0.1, openai_api_key=os.getenv("OPENROUTER_API_KEY"), openai_api_base="https://openrouter.ai/api/v1")

def route_query(query: str):
    q = query.lower()
    if any(x in q for x in ["research", "methodology", "social"]): return "IR-210"
    elif any(x in q for x in ["foreign policy", "diplomacy"]): return "IR-202"
    elif any(x in q for x in ["french", "france"]): return "French"
    return "General"


# =====================================================================
# 🌟 THE AGENTIC ACADEMIC OS ENDPOINTS
# =====================================================================
@app.get("/api/v1/academic/analytics/{user_id}")
async def get_student_analytics(user_id: str):
    """ফ্রন্টএন্ড থেকে কল করলে ইউজারের উইকনেস এবং প্রোগ্রেস রিপোর্ট পাঠাবে।"""
    try:
        report = generate_progress_report(user_id)
        return {"status": "success", "data": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch analytics: {e}")


@app.post("/api/v1/academic/generate-plan")
async def create_study_plan(req: StudentRequest):
    """এজেন্টিক ব্রেইনকে ট্রিগার করবে ইউজারের জন্য ৭-দিনের রুটিন বানানোর জন্য।"""
    try:
        if req.email and req.name:
            get_or_create_student_profile(req.user_id, req.email, req.name)
            
        result = generate_cgpa_boost_plan(req.user_id)
        
        if result.get("status") == "success":
            return {
                "message": "AI successfully generated and saved your CGPA Boost Plan!", 
                "data": result["plan"]
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("message", "Unknown error"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================================
# 🌐 THE MAIN CHAT API (UPDATED WITH AGENTIC CORE)
# =====================================================================
@app.post("/chat")
async def chat_with_ai(request: ChatRequest):
    user_query = request.query
    selected_model = request.model
    user_id = request.user_id
    

    # 0. MODEL LOCKING & CREDIT DEDUCTION LOGIC
    premium_models = ["gpt-4o", "claude-3-5-sonnet", "gemini-1.5-pro"]
    cost_per_premium_prompt = 5
    
    if selected_model in premium_models and user_id != "guest" and supabase:
        user_db = supabase.table("user_profiles").select("subscription_tier, reward_credits").eq("id", user_id).execute()
        
        if user_db.data:
            user_info = user_db.data[0]
            if user_info.get("subscription_tier") != "pro_scholar":
                current_credits = user_info.get("reward_credits", 0)
                
                if current_credits < cost_per_premium_prompt:
                    return {
                        "reply": "⚠️ **Premium Model Locked!**\nআপনার পর্যাপ্ত ক্রেডিট নেই। এই অ্যাডভান্সড মডেলটি ব্যবহার করতে একটি অ্যাড দেখুন অথবা Pro Scholar প্যাকেজ আনলক করুন।",
                        "sources": []
                    }
                else:
                    new_balance = current_credits - cost_per_premium_prompt
                    supabase.table("user_profiles").update({"reward_credits": new_balance}).eq("id", user_id).execute()
    

    # 1. CASUAL GREETING BYPASS
    casual_greetings = ["hi", "hello", "hey", "hallo", "helo", "হ্যালো", "হাই"]
    if any(user_query.strip().lower().startswith(g) for g in casual_greetings) and len(user_query.split()) < 5:
        reply = "হ্যালো! 👋 আমি GSTU IR ডিপার্টমেন্টের এলিট এআই অ্যাসিস্ট্যান্ট। আজ আপনার গবেষণা বা জিওপলিটিক্যাল অ্যানালাইসিসে কীভাবে সাহায্য করতে পারি?" if bool(re.search(r'[\u0980-\u09FF]', user_query)) else "Hello! 👋 I am the Elite GSTU IR AI Assistant. How can I help you with your academic research or geopolitical analysis today?"
        return {"reply": reply, "sources": []}


    # 2. INITIALIZE CONTEXT VARIABLES
    db_context = ""
    web_context = ""
    source_counter = 1
    formatted_sources_list = []
    

    # 3. AGENTIC DECISION ENGINE
    need_db = False
    need_web = False

    if ENABLE_AGENTIC_CORE and selected_model in premium_models:
        agentic_prompt = f"""Analyze the user query: "{user_query}"
        Does this query require looking up academic course materials/PDFs (IR-200, geopolitics notes)? Reply 'DB'
        Does this query require the latest current events, news, or live web data? Reply 'WEB'
        If both, reply 'BOTH'. If neither, reply 'NONE'."""
        
        try:
            router_llm = ChatGroq(model_name="llama-3.1-8b-instant", temperature=0, groq_api_key=os.getenv("GROQ_API_KEY"))
            decision = router_llm.invoke(agentic_prompt).content.strip().upper()
            
            if "DB" in decision or "BOTH" in decision: need_db = True
            if "WEB" in decision or "BOTH" in decision: need_web = True
        except:
            need_db, need_web = True, True
    else:
        need_db = True
        if any(kw in user_query.lower() for kw in ["current", "latest", "now", "today", "news", "geopolitics", "2026"]):
            need_web = True

    # 4. BACKGROUND TOOL EXECUTION
    if need_db and vector_db:
        detected_course = route_query(user_query)
        search_kwargs = {"k": 6} if detected_course == "General" else {"k": 6, "filter": {"course": detected_course}}
        docs = vector_db.as_retriever(search_kwargs=search_kwargs).invoke(user_query)
        
        if docs:
            db_context = "\n\n".join(doc.page_content for doc in docs)
            unique_db = {}
            for doc in docs:
                src_name = os.path.basename(doc.metadata.get('source', 'Unknown'))
                page = doc.metadata.get('page')
                if src_name not in unique_db: unique_db[src_name] = set()
                if page is not None: unique_db[src_name].add(str(page + 1))
                
            for src, pages in unique_db.items():
                pg_str = ", ".join(sorted(list(pages), key=lambda x: int(x) if x.isdigit() else str(x)))
                formatted_sources_list.append({"id": source_counter, "type": "pdf", "title": src, "details": f"Pages: {pg_str}" if pg_str else ""})
                source_counter += 1

    if need_web and os.getenv("TAVILY_API_KEY"):
        try:
            tav_res = TavilyClient(api_key=os.getenv("TAVILY_API_KEY")).search(query=user_query, max_results=3, include_answer=True)
            web_context = f"Live Web Data: {tav_res.get('answer', '')}\n\n"
            for r in tav_res.get('results', []):
                web_context += f"Content: {r.get('content')}\n\n"
                domain = r.get('url', '').split('/')[2].replace('www.', '') if '//' in r.get('url', '') else 'Web'
                formatted_sources_list.append({"id": source_counter, "type": "web", "title": r.get('title', domain), "details": r.get('url', '')})
                source_counter += 1
        except Exception as e:
            print(f"Web Search Tool Failed: {e}")


    # 5. FINAL RESPONSE GENERATION
    is_bengali = bool(re.search(r'[\u0980-\u09FF]', user_query))
    
    if is_bengali:
                            system_persona = """তুমি হচ্ছো GSTU-এর ইন্টারন্যাশনাল রিলেশনস (IR) ডিপার্টমেন্টের চিফ জিওপলিটিক্যাল অ্যানালিস্ট।
তোমার উত্তর হবে অ্যাকাডেমিক, থিওরি-নির্ভর এবং অত্যন্ত প্রফেশনাল।"""
                            lang_guard = "CRITICAL: Output MUST be entirely in standard BENGALI (বাংলা ফন্ট)।"
    else:
        system_persona = """You are the Chief Geopolitical Analyst & Professor for the IR Department at GSTU.
Your response MUST be highly academic, theoretically sound, and analytically deep. DO NOT provide shallow answers."""
        lang_guard = "CRITICAL: You MUST answer strictly in scholarly ENGLISH. DO NOT USE BENGALI under any circumstances."

    hybrid_prompt = f"""{system_persona}
{lang_guard}

1. TIME-AWARENESS: Distinguish between historical context and current updates.
2. STRICT FACT-GROUNDING: Use ONLY the provided Database and Web Data. Do not invent facts.
3. ACADEMIC STANDARD: Analyze root causes and strategic impacts.
4. INLINE CITATIONS: Use [1], [2] referencing the sources below.

--- DATABASE KNOWLEDGE ---
{db_context[:1500]}

--- LIVE WEB DATA ---
{web_context[:3000]}

--- USER QUESTION ---
{user_query}

Provide detailed academic analysis:"""

    try:
        if is_bengali and "llama" in selected_model.lower(): 
            selected_model = "gemini-2.5-flash"
            
        response = get_llm(selected_model).invoke(hybrid_prompt)
        final_reply = response.content.strip()
        
        # 🔴 Save Chat to Supabase Cloud Asynchronously
        if user_id != "guest" and supabase:
            try:
                supabase.table("chat_history").insert({
                    "user_id": user_id,
                    "user_query": user_query,
                    "ai_response": final_reply
                }).execute()
            except Exception as db_err:
                print(f"Failed to save chat history: {db_err}")
        
        return {"reply": final_reply, "sources": formatted_sources_list}
        
    except Exception as e:
        return {"reply": f"⚠️ **AI Engine Error:** `{str(e)}`", "sources": []}
    

# =====================================================================
# 🎤 VOICE & FILE API
# =====================================================================
@app.post("/voice")
async def process_voice(audio_file: UploadFile = File(...)):
    try:
        temp_path = f"temp_{audio_file.filename}"
        with open(temp_path, "wb") as f: f.write(await audio_file.read())
        groq_key = os.getenv("GROQ_API_KEY")
        client = Groq(api_key=groq_key)
        with open(temp_path, "rb") as file:
            transcription = client.audio.transcriptions.create(file=(temp_path, file.read()), model="whisper-large-v3", response_format="text").strip()
        os.remove(temp_path)
        return {"transcription": transcription}
    except Exception as e:
        if os.path.exists(temp_path): os.remove(temp_path)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload")
async def process_document(file: UploadFile = File(...)):
    try:
        if file.filename.endswith(".pdf"):
            pdf_reader = pypdf.PdfReader(file.file)
            text = "".join(page.extract_text() + "\n" for page in pdf_reader.pages)
            return {"extracted_text": text}
        return {"extracted_text": f"[Uploaded file: {file.filename}]"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

# =====================================================================
# 🔴 FEEDBACK API
# =====================================================================
@app.post("/feedback")
async def log_feedback(feedback: dict):
    print(f"Feedback Logged - Chat: {feedback.get('chat_id')}, Rating: {feedback.get('rating')}")
    return {"status": "success"}


# =====================================================================
# 👤 USER TIER & REWARD LOGIC
# =====================================================================
@app.get("/api/user/status/{user_id}")
async def get_user_status(user_id: str):
    if not supabase: raise HTTPException(status_code=500, detail="DB Offline")
    response = supabase.table("user_profiles").select("*").eq("id", user_id).execute()
    
    if not response.data: raise HTTPException(status_code=404, detail="User not found")
    user_data = response.data[0]
    
    if user_data.get('subscription_tier') == 'pro_scholar' and user_data.get('pro_expiry_date'):
        expiry_date = datetime.datetime.fromisoformat(user_data['pro_expiry_date'])
        if datetime.datetime.now() > expiry_date:
            supabase.table("user_profiles").update({"subscription_tier": "free", "pro_expiry_date": None}).eq("id", user_id).execute()
            user_data['subscription_tier'] = 'free'
            
    return {"status": "success", "data": user_data}


@app.get("/api/chat/history/{user_id}")
async def get_chat_history(user_id: str, limit: int = 20):
    if not supabase: raise HTTPException(status_code=500, detail="DB Offline")
    response = supabase.table("chat_history").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute()
    if not response.data: return {"status": "success", "data": []}
    return {"status": "success", "data": response.data[::-1]}


@app.post("/api/user/add_credits/{user_id}")
async def add_reward_credits(user_id: str, credits_earned: int):
    if not supabase: raise HTTPException(status_code=500, detail="DB Offline")
    current_data = supabase.table("user_profiles").select("reward_credits").eq("id", user_id).execute()
    if not current_data.data: raise HTTPException(status_code=404, detail="User not found")
    new_balance = current_data.data[0].get('reward_credits', 0) + credits_earned
    supabase.table("user_profiles").update({"reward_credits": new_balance}).eq("id", user_id).execute()
    return {"status": "success", "new_balance": new_balance}


@app.post("/api/user/earn_credits/{user_id}")
async def earn_credits(user_id: str, action_type: str):
    if not supabase: raise HTTPException(status_code=500, detail="DB Offline")
    reward_map = {"watch_ad": 10, "download_app": 50, "daily_login": 5}
    credits_earned = reward_map.get(action_type, 0)
    if credits_earned == 0: raise HTTPException(status_code=400, detail="Invalid action type")
    
    current_data = supabase.table("user_profiles").select("reward_credits").eq("id", user_id).execute()
    if not current_data.data: raise HTTPException(status_code=404, detail="User not found")
    new_balance = current_data.data[0].get('reward_credits', 0) + credits_earned
    
    supabase.table("user_profiles").update({"reward_credits": new_balance}).eq("id", user_id).execute()
    return {"status": "success", "new_balance": new_balance, "message": f"Successfully earned {credits_earned} credits!"}

# =====================================================================
# 💳 PAYMENT GATEWAY INTEGRATION
# =====================================================================
# 🔴 Streamlit ফ্রন্টএন্ডের লিংক (লোকাল টেস্টিংয়ের জন্য localhost:8501)
# প্রজেক্ট লাইভ করার সময় এখানে Render বা আপনার আসল ডোমেইন লিংক বসাতে হবে
FRONTEND_URL = "https://gstu-ai-backend.onrender.com"

# Initialize Admin Client (Bypasses RLS)
admin_supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))

class PaymentRequest(BaseModel):
    user_id: str
    amount: float
    plan_name: str

@app.post("/api/payment/initiate")
async def initiate_payment(req: PaymentRequest):
    """Note: Initiation is now directly handled in Streamlit via payment_manager.py"""
    return {"message": "Please use payment_manager.py for initiation."}


@app.post("/api/payment/success")
async def payment_success(request: Request):
    """SSLCommerz will send POST data here after successful payment"""
    form_data = await request.form()
    
    status = form_data.get("status")
    tran_id = form_data.get("tran_id")
    val_id = form_data.get("val_id")
    
    if status == "VALID":
        # 1. Fetch User ID from our pending transactions
        txn_res = admin_supabase.table("transactions").select("user_id").eq("id", tran_id).execute()
        
        if txn_res.data:
            user_id = txn_res.data[0]["user_id"]
            
            # 2. Update Transaction Status
            admin_supabase.table("transactions").update({
                "status": "success",
                "gateway_ref": val_id
            }).eq("id", tran_id).execute()
            
            # 3. 🔴 UPGRADE USER TIER (Bypassing RLS with Admin Key)
            admin_supabase.table("subscriptions").upsert({
                "user_id": user_id,
                "plan": "pro_scholar",
                "status": "active",
                "expires_at": (datetime.datetime.now() + timedelta(days=30)).isoformat()
            }).execute()
            
            # 4. Redirect browser back to Streamlit app (Success UI)
            return RedirectResponse(url=f"{FRONTEND_URL}?payment=success", status_code=303)
            
    # If validation fails, redirect to fail page
    return RedirectResponse(url=f"{FRONTEND_URL}?payment=failed", status_code=303)

@app.post("/api/payment/fail")
@app.post("/api/payment/cancel")
async def payment_fail_cancel(request: Request):
    """Redirects user back to Streamlit if they cancel or payment fails"""
    return RedirectResponse(url=f"{FRONTEND_URL}?payment=cancelled", status_code=303)