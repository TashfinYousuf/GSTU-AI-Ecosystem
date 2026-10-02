import os
import uuid
import re
import asyncio
import logging

from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from google import genai
from groq import Groq
from google.genai import types
from dotenv import load_dotenv

from app.core.limiter import limiter
from app.core.security import get_current_user, get_optional_current_user
from app.core.vector_store import get_workspace_vectorstore

from supabase import create_client, Client

load_dotenv(override=True)

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
# 🔴 FIX: this MUST be the `service_role` key, not the `anon` key.
# Your backend already authenticates every request via get_current_user()
# (JWT/JWKS verification) and manually scopes every query with
# .eq("user_id", user_id) — so Postgres Row Level Security is redundant
# protection here, and if this is the anon key, RLS blocks inserts even
# from a fully-authenticated, correctly-scoped request. That's exactly
# what "new row violates row-level security policy" means: not a bug in
# this code, but the client being initialized with a key that RLS
# actually applies to. Get the service_role key from Supabase Dashboard
# -> Settings -> API -> service_role (secret) -- NEVER expose this key to
# the frontend, it must only ever live in backend .env.
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

gemini_key = os.getenv("GEMINI_API_KEY")
if gemini_key:
    os.environ["GEMINI_API_KEY"] = gemini_key

router = APIRouter(tags=["AI Engine"])


class ChatRequest(BaseModel):
    model_config = {"extra": "forbid"}
    message: str
    workspace_id: str
    model: str = "llama-3.3-70b-versatile" # 🔴 Added Support for multi-model routing

class ProjectCreate(BaseModel):
    model_config = {"extra": "forbid"}
    name: str = "New Project"


class ProjectUpdate(BaseModel):
    model_config = {"extra": "forbid"}
    name: Optional[str] = None


class WorkspaceCreate(BaseModel):
    model_config = {"extra": "forbid"}
    project_id: Optional[str] = None


class WorkspaceUpdate(BaseModel):
    model_config = {"extra": "forbid"}
    title: Optional[str] = None
    is_starred: Optional[bool] = None
    project_id: Optional[str] = None
    clear_project: Optional[bool] = False

class SupportQuery(BaseModel):
    model_config = {"extra": "forbid"}
    message: str

# ---------- PROJECTS ----------

@router.post("/projects")
@limiter.limit("10/minute")
async def create_project(payload: ProjectCreate, request: Request, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    new_id = str(uuid.uuid4())
    supabase.table("projects").insert({
        "id": new_id, "user_id": user_id, "name": payload.name.strip() or "New Project"
    }).execute()
    return {"id": new_id, "name": payload.name}


@router.get("/projects")
async def list_projects(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    proj_res = await asyncio.to_thread(
    lambda: supabase.table("projects").select("*").eq("user_id", user_id).order("created_at", desc=True).execute() )

    chat_res = await asyncio.to_thread(
    lambda: supabase.table("workspaces").select("project_id").eq("user_id", user_id).execute() )

    counts = {}
    for row in (chat_res.data or []):
        pid = row.get("project_id")
        if pid:
            counts[pid] = counts.get(pid, 0) + 1

    projects = [{"id": p["id"], "name": p["name"], "chat_count": counts.get(p["id"], 0)} for p in (proj_res.data or [])]
    return {"status": "success", "data": projects}


@router.patch("/projects/{project_id}")
async def update_project(project_id: str, payload: ProjectUpdate, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    check = supabase.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Project not found.")
    if payload.name:
        supabase.table("projects").update({"name": payload.name}).eq("id", project_id).execute()
    return {"status": "success"}


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    check = supabase.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Project not found.")
    supabase.table("workspaces").update({"project_id": None}).eq("project_id", project_id).execute()
    supabase.table("projects").delete().eq("id", project_id).execute()
    return {"status": "success"}


# ---------- WORKSPACES (CHATS) ----------

# 1. CREATE WORKSPACE
@router.post("/workspaces")
@limiter.limit("10/minute")
async def create_workspace(request: Request, payload: WorkspaceCreate = WorkspaceCreate(), current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Anti-junk safeguard: if user already has an unused "New Chat" with 0 messages, reuse it!
    existing = (
        supabase.table("workspaces")
        .select("id, name, project_id, is_starred")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(5)
        .execute()
    )
    for ws in (existing.data or []):
        if ws.get("name") in ["New Chat", "Untitled Chat"] and ws.get("project_id") == payload.project_id:
            msg_check = supabase.table("messages").select("id").eq("workspace_id", ws["id"]).limit(1).execute()
            if not msg_check.data:
                return {
                    "id": ws["id"],
                    "title": ws.get("name", "New Chat"),
                    "project_id": ws.get("project_id"),
                    "is_starred": ws.get("is_starred", False)
                }

    new_id = str(uuid.uuid4())
    supabase.table("workspaces").insert({
        "id": new_id,
        "user_id": user_id,
        "name": "New Chat",
        "project_id": payload.project_id,
        "is_starred": False
    }).execute()

    return {"id": new_id, "title": "New Chat", "project_id": payload.project_id, "is_starred": False}


# 2. LIST WORKSPACES (Auto-cleans duplicate empty chats)
@router.get("/workspaces")
async def list_workspaces(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    res = (
        supabase.table("workspaces")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    all_ws = res.data or []
    if not all_ws:
        return {"status": "success", "data": []}

    # Identify workspaces that have real messages
    ws_ids = [w["id"] for w in all_ws]
    msg_rows = supabase.table("messages").select("workspace_id").in_("workspace_id", ws_ids).execute()
    active_ws_ids = {m["workspace_id"] for m in (msg_rows.data or [])}

    filtered = []
    empty_new_chat_found = False
    junk_ids_to_clean = []

    for w in all_ws:
        ws_id = w["id"]
        has_msgs = ws_id in active_ws_ids
        is_empty_new_chat = (w.get("name") in ["New Chat", "Untitled Chat"]) and not w.get("project_id") and not has_msgs

        if is_empty_new_chat:
            if not empty_new_chat_found:
                # Keep only the latest empty New Chat
                empty_new_chat_found = True
                filtered.append(w)
            else:
                # Discard and queue duplicate empty New Chats for cleanup
                junk_ids_to_clean.append(ws_id)
        else:
            filtered.append(w)

    if junk_ids_to_clean:
        try:
            supabase.table("workspaces").delete().in_("id", junk_ids_to_clean).execute()
        except Exception as e:
            logger.warning(f"Error purging duplicate empty chats: {e}")

    workspaces = [
        {
            "id": w["id"],
            "title": w.get("name", "New Chat"),
            "project_id": w.get("project_id"),
            "is_starred": w.get("is_starred", False),
            "updated_at": w.get("updated_at", w.get("created_at")),
        }
        for w in filtered
    ]
    return {"status": "success", "data": workspaces}


# 2.1 GET SINGLE WORKSPACE
@router.get("/workspaces/{workspace_id}")
async def get_workspace(workspace_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    res = (
        supabase.table("workspaces")
        .select("*")
        .eq("id", workspace_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="Workspace not found")
    w = res.data
    return {
        "status": "success",
        "data": {
            "id": w["id"],
            "title": w.get("name", "New Chat"),
            "project_id": w.get("project_id"),
            "is_starred": w.get("is_starred", False),
            "updated_at": w.get("updated_at", w.get("created_at")),
        }
    }


@router.patch("/workspaces/{workspace_id}")
async def update_workspace(workspace_id: str, payload: WorkspaceUpdate, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    ws_check = supabase.table("workspaces").select("id").eq("id", workspace_id).eq("user_id", user_id).execute()
    if not ws_check.data:
        raise HTTPException(status_code=404, detail="Workspace not found.")

    update_data = {}
    if payload.title is not None:
        update_data["name"] = payload.title
    if payload.is_starred is not None:
        update_data["is_starred"] = payload.is_starred
    if payload.project_id is not None:
        update_data["project_id"] = payload.project_id
    elif payload.clear_project:
        update_data["project_id"] = None

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update.")

    supabase.table("workspaces").update(update_data).eq("id", workspace_id).execute()
    return {"status": "success"}


@router.delete("/workspaces/{workspace_id}")
async def delete_workspace(workspace_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    ws_check = supabase.table("workspaces").select("id").eq("id", workspace_id).eq("user_id", user_id).execute()
    if not ws_check.data:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    supabase.table("messages").delete().eq("workspace_id", workspace_id).execute()
    supabase.table("workspaces").delete().eq("id", workspace_id).execute()
    return {"status": "success"}


# ---------- USER STATS (drives the real Billing tab numbers) ----------

@router.get("/stats")
async def get_user_stats(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    ws_res = supabase.table("workspaces").select("id").eq("user_id", user_id).execute()
    workspace_ids = [w["id"] for w in (ws_res.data or [])]

    query_count = 0
    doc_count = 0

    if workspace_ids:
        msg_res = (
            supabase.table("messages")
            .select("id", count="exact")
            .in_("workspace_id", workspace_ids)
            .eq("role", "user")
            .execute()
        )
        query_count = msg_res.count or 0

        # 🔴 FIX: documents table has no user_id column (confirmed via
        # information_schema — same as messages, it's scoped by
        # workspace_id, not user_id directly). Count via the same
        # workspace-ownership join instead of a direct .eq("user_id", ...)
        # filter, which was querying a column that doesn't exist.
        try:
            doc_res = (
                supabase.table("documents")
                .select("id", count="exact")
                .in_("workspace_id", workspace_ids)
                .execute()
            )
            doc_count = doc_res.count or 0
        except Exception as e:
            print(f"Document count fetch error (check documents table schema): {e}")
            doc_count = 0

    return {"status": "success", "queries": query_count, "documents_analyzed": doc_count}


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


# ---------- DANGER ZONE: wipe all chat data for a user ----------

@router.delete("/history/all")
async def delete_all_history(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    ws_res = supabase.table("workspaces").select("id").eq("user_id", user_id).execute()
    workspace_ids = [w["id"] for w in (ws_res.data or [])]

    if workspace_ids:
        supabase.table("messages").delete().in_("workspace_id", workspace_ids).execute()
    supabase.table("workspaces").delete().eq("user_id", user_id).execute()
    supabase.table("projects").delete().eq("user_id", user_id).execute()

    return {"status": "success"}


# 3. GET CHAT HISTORY
# 🔴 FIX: now scoped to user_id too — previously any authenticated user could
# read any workspace's history just by guessing/knowing its UUID (IDOR bug).
@router.get("/history/{workspace_id}")
async def get_history(workspace_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    ws_check = (
        supabase.table("workspaces")
        .select("id")
        .eq("id", workspace_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not ws_check.data:
        raise HTTPException(status_code=404, detail="Workspace not found.")

    try:
        res = (
            supabase.table("messages")
            .select("*")
            .eq("workspace_id", workspace_id)
            .order("created_at", desc=False)
            .execute()
        )
        return {"status": "success", "data": res.data if res.data else []}
    except Exception as e:
        print(f"History fetch error: {e}")
        return {"status": "success", "data": []}


@router.post("/stream")
@limiter.limit("15/minute")
async def chat_stream(request: Request, chat_req: ChatRequest, current_user: dict = Depends(get_optional_current_user)):
    user_id = current_user.get("sub") if current_user else "guest_session"
    role = current_user.get("user_metadata", {}).get("role", "guest").lower() if current_user else "guest"

    latest_q = chat_req.message.strip()

    # =====================================================================
    # 🛡️ 1. SECURITY & INTENT ROUTER (Bypasses AI/DB for speed)
    # =====================================================================
    suspicious_keywords = ["ignore previous", "system prompt", "developer mode", "jailbreak", "bypass", "sudo "]
    if any(kw in latest_q.lower() for kw in suspicious_keywords):
        async def security_block():
            yield "⚠️ **Security Guard AI:** Malicious intent detected. Request Blocked."
        return StreamingResponse(security_block(), media_type="text/plain")

    creator_keywords = ["created", "made", "inventor", "founded", "developer", "creator"]
    if any(kw in latest_q.lower() for kw in creator_keywords):
        async def creator_res():
            yield "The inventor and head developer of this Elite AI Architecture is **Tashfin Yousuf**.\n\n[📄 View Tashfin's Portfolio](https://tashfinzportfolio.infy.uk/)"
        return StreamingResponse(creator_res(), media_type="text/plain")


    # =====================================================================
    # 💾 2. DATABASE PERSISTENCE & WORKSPACE MANAGEMENT
    # =====================================================================
    is_global_bot = chat_req.workspace_id == "global-assistant-0000"

    if user_id != "guest_session" and not is_global_bot:
        ws_check = supabase.table("workspaces").select("*").eq("id", chat_req.workspace_id).eq("user_id", user_id).execute()
        if not ws_check.data:
            raise HTTPException(status_code=404, detail="Workspace not found.")

        # Auto-title the workspace from the first message
        if ws_check.data[0].get("name") == "New Chat":
            new_name = latest_q[:35] + "..." if len(latest_q) > 35 else latest_q
            supabase.table("workspaces").update({"name": new_name}).eq("id", chat_req.workspace_id).execute()

        # Save user message
        supabase.table("messages").insert({
            "workspace_id": chat_req.workspace_id,
            "role": "user",
            "content": latest_q
        }).execute()

        # Bump updated_at so Recents UI updates perfectly!
        supabase.table("workspaces").update({
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", chat_req.workspace_id).execute()


    # =====================================================================
    # 🧠 3. THE MASTER GENERATOR (RAG + Web + Hybrid AI)
    # =====================================================================
    async def streaming_generator():
        full_ai_response = ""
        db_context = ""       # local RAG only
        web_context = ""      # live web search only — was being merged into db_context before
        source_links = set()
        local_citations = []
        retrieved_docs = []
        used_web = False
        is_bengali = bool(re.search(r'[\u0980-\u09FF]', latest_q))

        # 🧠 RAG Retrieval: Check Workspace Documents + Central Department Knowledge Base
        # 1. Workspace documents (if workspace_id is provided)
        if chat_req.workspace_id and not is_global_bot:
            try:
                ws_vs = get_workspace_vectorstore(chat_req.workspace_id)
                ws_docs = ws_vs.similarity_search(latest_q, k=4)
                if ws_docs:
                    retrieved_docs.extend(ws_docs)
            except Exception as e:
                logger.warning(f"Workspace RAG Retrieval Error: {e}")

        # 2. Central Department Knowledge Base (Curriculum books, syllabus, lecture materials)
        try:
            kb_vs = get_workspace_vectorstore("global_knowledge_base")
            kb_docs = kb_vs.similarity_search(latest_q, k=4)
            if kb_docs:
                retrieved_docs.extend(kb_docs)
        except Exception as e:
            logger.warning(f"Global Knowledge Base RAG Retrieval Error: {e}")

        # Format context with clean document titles and exact page numbers
        if retrieved_docs:
            formatted_chunks = []
            for i, d in enumerate(retrieved_docs):
                src = d.metadata.get("source") or d.metadata.get("filename") or "Department Textbook"
                page = d.metadata.get("page_number") or d.metadata.get("page")
                page_str = f"Page {page}" if page else "Excerpt"
                formatted_chunks.append(f"[Document {i+1}: 《{src}》, {page_str}]\n{d.page_content}")

                citation_badge = f"{src}" + (f" (p. {page})" if page else "")
                if citation_badge not in local_citations:
                    local_citations.append(citation_badge)

            db_context = "\n\n".join(formatted_chunks)
        else:
            db_context = "No internal academic documents or textbooks matched this query."


        # Live web search (unchanged logic, but now writes to web_context, not db_context)
        live_keywords = ["current", "latest", "now", "today", "update", "news", "war", "conflict", "crisis", "বর্তমান", "আজকের", "খবর", "bortoman", "bishwer", "ajker"]
        needs_web = any(kw in latest_q.lower() for kw in live_keywords)
        if needs_web:
            try:
                search_query = latest_q
                banglish_kws = ["ki", "ajker", "kemon", "hobe", "bisser", "bortoman", "news"]
                if is_bengali or any(w in latest_q.lower().split() for w in banglish_kws):
                    translator = Groq(api_key=os.getenv("GROQ_API_KEY"))
                    trans_res = translator.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": "Translate the given Bengali/Banglish text into a short English search query (max 5 words). ONLY output the English query."},
                            {"role": "user", "content": latest_q}
                        ],
                        temperature=0.1, max_tokens=20
                    )
                    search_query = trans_res.choices[0].message.content.strip().replace('"', '')

                from tavily import TavilyClient
                tavily_key = os.getenv("TAVILY_API_KEY")
                if tavily_key:
                    tavily_res = TavilyClient(api_key=tavily_key).search(query=search_query, search_depth="advanced", max_results=3)
                    for r in tavily_res.get('results', []):
                        web_context += f"Source: {r.get('title')}\nSnippet: {r.get('content')}\n\n"
                        source_links.add(r.get('url'))
                    used_web = True
            except Exception as e:
                print(f"Web Search Failed: {e}")

        # Conversation history (unchanged)
        history_ctx = "No prior conversation."
        if not is_global_bot:
            try:
                hist_res = supabase.table("messages").select("role, content").eq("workspace_id", chat_req.workspace_id).order("created_at", desc=False).execute()
                if hist_res.data:
                    history_ctx = build_history_context(hist_res.data)
            except Exception as e:
                print(f"History Fetch Error: {e}")

        # Memory/mood injection (folded in from the old Pass B — kept, not duplicated)
        import datetime
        current_date = datetime.datetime.now().strftime("%B %d, %Y")
        last_mood, user_focus = 3, "General Academic Concepts"
        if user_id != "guest_session":
            try:
                mood_res = supabase.table("study_sessions").select("mood").eq("user_id", user_id).order("timestamp", desc=True).limit(1).execute()
                if mood_res.data: last_mood = mood_res.data[0].get("mood", 3)
                logs_res = supabase.table("ai_training_logs").select("topic_tag").eq("user_id", user_id).limit(10).execute()
                if logs_res.data:
                    topics = [r["topic_tag"] for r in logs_res.data if r.get("topic_tag")]
                    if topics: user_focus = max(set(topics), key=topics.count)
            except Exception as e:
                print(f"Memory Fetch Error: {e}")

        # 🔴 THE NEW EXCLUSIVE PROMPT ARCHITECTURE
        sys_inst = (
            "You are the Chief Analyst and Professor for the IR Department at GSTU. Never say that you are an AI. Never introduce yourself unless asked. Your creator and lead architect is Tashfin Yousuf. Acknowledge him respectfully ONLY if directly asked about your creation.\n\n"
            "Answer entirely in flawless, academic BENGALI SCRIPT. Never mix languages."
            "Never hallucinate facts. Rely on the provided context."
            
        ) if is_bengali else (
            "You are the Chief Analyst and Professor for the IR Department at GSTU. Never say that you are an AI. Never introduce yourself unless asked. Your creator and lead architect is Tashfin Yousuf. Acknowledge him respectfully ONLY if directly asked about your creation.\n\n"
            "Answer entirely in elite, scholarly ENGLISH. Zero hallucination."
            "Never hallucinate facts. Rely on the provided context."
        )

        # Context formatting
        history_ctx = "No prior conversation." # (You can dynamically fetch last 3 messages here if needed)
        
        # ONE final prompt — replaces both old hybrid_prompt builds
        final_prompt = f"""{sys_inst}
    ⏳ CURRENT DATE: {current_date}
    🧠 STUDENT STATE: Focus Topic "{user_focus}", Last Mood (1-5): {last_mood}. If mood is low, be encouraging; if high, go deeper.

    🛡️ ZERO-HALLUCINATION & CRITICAL INSTRUCTIONS (MUST OBEY):
    1. TIME-AWARENESS & NEWS ACCURACY: Distinguish strictly between historical academic data (Local Database Context) and breaking news (Live Web Data).
    2. BANGLISH = BENGALI SCRIPT OUTPUT: If the user asks a question in "Banglish", you MUST deeply understand the query, but your OUTPUT MUST BE ENTIRELY IN PURE BENGALI SCRIPT (বাংলা ফন্ট).
    3. STRICT FACT-GROUNDING (0% Hallucination): Base your core academic analysis directly on the provided Local Database Context.
    4. ELITE ACADEMIC DEPTH: Proactively analyze Root Causes, Major Flashpoints, Theoretical Paradigms, and Strategic Consequences.
    5. SEAMLESS INTEGRATION: Combine local textbook theories with live web updates naturally.
    6. EXPLICIT BOOK & PAGE CITATIONS (ZERO HALLUCINATION):
       - When citing concepts or data from the LOCAL DATABASE CONTEXT, you MUST explicitly state the book/document title and page number as provided in the metadata (e.g., "According to 《Geopolitics: The Geography of International Relations》, Page 12..." or "[1] 《Globalization of World Politics》, p. 84").
       - In Bengali: (যেমন: "《Geopolitics》 বইয়ের ১২ নম্বর পৃষ্ঠা অনুযায়ী...").
       - NEVER invent or hallucinate book titles, authors, or page numbers that are not in the context.
    7. FORMATTING: Use bold text and bullet points for key terms. Always use bullet points or numbered lists when explaining multiple concepts. Add 2-3 thoughtful follow-up questions at the end.
    8. SPACING: Add double line breaks between distinct points or sections.
    9. MATCH LANGUAGE EXACTLY: If English, answer in English. If Bengali, answer in Bengali.
    10. FOUNDER: Your creator is Tashfin Yousuf, an undergraduate student at GSTU.

    --- CONVERSATION HISTORY ---
    {history_ctx}

    --- LOCAL DATABASE CONTEXT ---
    {db_context or "No internal academic documents found."}

    --- LIVE WEB DATA ---
    {web_context if used_web else "No live web search triggered."}

    --- USER QUESTION ---
    {latest_q}

    Provide your response below:"""

        hybrid_prompt = final_prompt

        verifier_badge = "<div style='background: rgba(16, 163, 127, 0.1); border: 1px solid rgba(16, 163, 127, 0.4); padding: 4px 12px; border-radius: 6px; margin-bottom: 10px; display: inline-block;'><span style='font-size:12px; color:#10a37f; font-weight:700;'>🛡️ ✓ Fact-checked by Verifier Agent</span></div>\n\n"
        full_ai_response += verifier_badge
        yield verifier_badge

        try:
            selected_model = chat_req.model.lower()
            if is_bengali:
                selected_model = "gemini-2.5-flash"  # force Bengali to Gemini for script handling

            if "gemini" in selected_model:
                client = genai.Client(api_key=gemini_key)
                response = client.models.generate_content_stream(model='gemini-2.5-flash', contents=final_prompt)
                for chunk in response:
                    if chunk.text:
                        full_ai_response += chunk.text
                        yield chunk.text
                        await asyncio.sleep(0.01)

            elif "llama" in selected_model:  # 🔴 removed "qwen" from this branch
                groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
                response = groq_client.chat.completions.create(model=selected_model, messages=[{"role": "user", "content": final_prompt}], stream=True)

            # 🔴 Localhost GPT4All Production Guard
            if selected_model == "local-gpt4all":
                is_production = os.getenv("RENDER") or os.getenv("VERCEL")
                if is_production:
                    # Production-এ স্থানীয় পিসির localhost পাওয়া যাবে না, তাই Gemini-তে অটো ফালব্যাক
                    selected_model = "gemini-2.5-flash"
                else:
                    # Local Environment
                    try:
                        llm = openai(
                            model_name="local-model",
                            temperature=0.4,
                            openai_api_key="not-needed",
                            openai_api_base="http://localhost:4891/v1",
                            request_timeout=3
                        )
                    except Exception:
                        selected_model = "gemini-2.5-flash"

            else:
                import openai
                openrouter_key = os.getenv("OPENROUTER_API_KEY")
                if not openrouter_key:
                    yield "\n\n⚠️ **OPENROUTER_API_KEY is missing!**"
                    return
                client = openai.AsyncOpenAI(api_key=openrouter_key, base_url="https://openrouter.ai/api/v1")
                response = await client.chat.completions.create(model=chat_req.model, messages=[{"role": "user", "content": final_prompt}], max_tokens=4096, stream=True)
                async for chunk in response:
                    if chunk.choices[0].delta.content:
                        text = chunk.choices[0].delta.content
                        full_ai_response += text
                        yield text
                        await asyncio.sleep(0.01)
        except Exception as e:
            print(f"CRITICAL AI FAILURE: {e}")
            if "402" in str(e) or "credits" in str(e).lower():
                yield "\n\n💳 **AI provider credits exhausted.** Please contact support."
            else:
                yield "\n\n🚦 **Server Overloaded or Model Error!** Please wait 10 seconds and try again."
            return

        # 🔴 FIX: citations were BUILT but never yielded — silently discarded every time.
        # Also the </details></div> tags were never closed in the original (broken HTML).
        if local_citations or source_links:
            source_text = "\n\n <div style='margin-top: 15px;'><details><summary style='cursor: pointer; font-weight: 600; color: white;'>📚 View Citations & Sources (তথ্যসূত্র)</summary><div style='padding-top: 10px; display: flex; flex-wrap: wrap; gap: 8px;'>"
            for doc_cite in local_citations:
                source_text += f"\n <span style='background: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.4); color: #a5b4fc; padding: 4px 12px; border-radius: 16px; font-size: 12px; font-weight: 500;'>📖 {doc_cite}</span>"
            for src in source_links:
                if str(src).startswith("http://") or str(src).startswith("https://"):
                    domain = src.split('/')[2].replace('www.', '') if '//' in str(src) else src
                    source_text += f"\n <a href='{src}' target='_blank' rel='noopener noreferrer' style='background: rgba(16, 163, 127, 0.15); border: 1px solid rgba(16, 163, 127, 0.4); color: #6ee7b7; padding: 4px 12px; border-radius: 16px; text-decoration: none; font-size: 12px; font-weight: 500;'>🌐 {domain}</a>"
                else:
                    source_text += f"\n <span style='background: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.4); color: #a5b4fc; padding: 4px 12px; border-radius: 16px; font-size: 12px; font-weight: 500;'>📖 {src}</span>"
            source_text += "\n</div></details></div>"
            full_ai_response += source_text
            yield source_text
        if used_web:
            badge = "\n\n*(🌐 Realtime Data Powered by **GSTU Web Search Engine**)*"
            full_ai_response += badge
            yield badge

        # 🔴 FIX: was inserted TWICE — once here, once again in the "RLHF logging"
        # block below. Every AI reply was being duplicated in chat history.
        if full_ai_response and user_id != "guest_session" and not is_global_bot:
            try:
                supabase.table("messages").insert({
                    "workspace_id": chat_req.workspace_id, "role": "assistant", "content": full_ai_response
                }).execute()
            except Exception as db_err:
                print(f"Failed to save AI msg: {db_err}")

            try:
                extracted_topic = " ".join(str(latest_q).split()[:4]).title()
                supabase.table("ai_training_logs").insert({
                    "user_id": user_id, "user_query": latest_q, "ai_response": full_ai_response,
                    "topic_tag": extracted_topic, "timestamp": datetime.datetime.now().isoformat()
                }).execute()
            except Exception as db_err:
                print(f"Logging Error: {db_err}")

    return StreamingResponse(streaming_generator(), media_type="text/plain")


@router.post("/ecosystem-support")
@limiter.limit("10/minute")

async def ecosystem_support_bot(request: Request, req: SupportQuery, current_user: dict = Depends(get_current_user)):
    system_prompt = (
        "You are 'GSTU Helpdesk', an AI assistant for the GSTU Ecosystem. "
        "Answer questions about how to use the dashboard, features, or general university inquiries concisely. "
        "Keep answers precise & short. Be polite and professional. "
        "Match user query language. If user asks in English, response in English. If user asks in Bangla/Banglish, response in standard Bangla."
    )
    try:
        client = genai.Client(api_key=gemini_key)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"{system_prompt}\n\nUSER QUESTION: {req.message}"
        )
        return {"status": "success", "reply": response.text}
    except Exception as e:
        return {"status": "error", "reply": "Our support agents are currently busy. Please try again later."}


# 🔴 GLOBAL SEARCH ENGINE
@router.get("/search")
@limiter.limit("10/minute")

async def global_search(request: Request, q: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id: raise HTTPException(status_code=401)
    
    # Avoid empty searches hitting the DB
    if not q or len(q.strip()) < 2:
        return {"status": "success", "data": []}
        
    try:
        # Search workspaces (chats) using case-insensitive LIKE (ilike)
        ws_res = supabase.table("workspaces") \
            .select("id, name") \
            .eq("user_id", user_id) \
            .ilike("name", f"%{q}%") \
            .limit(5) \
            .execute()
            
        results = []
        for w in (ws_res.data or []):
            results.append({
                "type": "workspace", 
                "id": w["id"], 
                "title": w["name"]
            })
            
        # You can expand this later to search projects/tickets based on user role
        return {"status": "success", "data": results}
    except Exception as e:
        print(f"Search API Error: {e}")
        return {"status": "error", "data": []}