import os
import uuid
import asyncio
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from google import genai
from google.genai import types
from dotenv import load_dotenv

from app.core.security import get_current_user
from supabase import create_client, Client

load_dotenv(override=True)
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
    message: str
    workspace_id: str


class ProjectCreate(BaseModel):
    name: str = "New Project"


class ProjectUpdate(BaseModel):
    name: Optional[str] = None


class WorkspaceCreate(BaseModel):
    project_id: Optional[str] = None


class WorkspaceUpdate(BaseModel):
    title: Optional[str] = None
    is_starred: Optional[bool] = None
    project_id: Optional[str] = None
    clear_project: Optional[bool] = False

class SupportQuery(BaseModel):
    message: str

# ---------- PROJECTS ----------

@router.post("/projects")
async def create_project(payload: ProjectCreate, current_user: dict = Depends(get_current_user)):
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

    proj_res = supabase.table("projects").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
    chat_res = supabase.table("workspaces").select("project_id").eq("user_id", user_id).execute()

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
async def create_workspace(payload: WorkspaceCreate = WorkspaceCreate(), current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    new_id = str(uuid.uuid4())
    supabase.table("workspaces").insert({
        "id": new_id,
        "user_id": user_id,
        "name": "New Chat",
        "project_id": payload.project_id,
        "is_starred": False
    }).execute()

    return {"id": new_id, "title": "New Chat", "project_id": payload.project_id, "is_starred": False}


# 2. LIST WORKSPACES
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
    workspaces = [
        {
            "id": w["id"],
            "title": w.get("name", "New Chat"),
            "project_id": w.get("project_id"),
            "is_starred": w.get("is_starred", False),
            "updated_at": w.get("updated_at", w.get("created_at")),
        }
        for w in (res.data or [])
    ]
    return {"status": "success", "data": workspaces}


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


# 4. STREAM CHAT + PERSIST BOTH SIDES
# 🔴 workspace lookup now scoped to user_id (same IDOR issue as get_history).
# 🔴 bare `except Exception` now logs the real error instead of swallowing it silently.
@router.post("/stream")
# 🔴 Maximum 50 AI requests per minute per IP to prevent bot attacks
# @limiter.limit("50/minute") <- You can add this decorator if limiter is configured globally
async def chat_stream(request: ChatRequest, chat_req: ChatRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    role = current_user.get("user_metadata", {}).get("role", "guest").lower()

    # 🔴 GUEST RESTRICTION LOGIC
    if role == "guest":
        # Check local DB/Cache for message count here
        pass

    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    ws_check = (
        supabase.table("workspaces")
        .select("*")
        .eq("id", request.workspace_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not ws_check.data:
        raise HTTPException(status_code=404, detail="Workspace not found.")

    # Auto-title the workspace from the first message
    if ws_check.data[0].get("name") == "New Chat":
        new_name = request.message[:35] + "..." if len(request.message) > 35 else request.message
        supabase.table("workspaces").update({"name": new_name}).eq("id", request.workspace_id).execute()

    supabase.table("messages").insert({
        "workspace_id": request.workspace_id,
        "role": "user",
        "content": request.message
    }).execute()

    # Keep "updated_at" fresh so Recents sorts by real activity, not creation date
    supabase.table("workspaces").update({
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", request.workspace_id).execute()

    async def streaming_generator():
        full_ai_response = ""

        system_instruction = (
            "You are GSTU Assistant, an academic AI for International Relations students.\n"
            "Formatting rules for EVERY response:\n"
            "- Use short paragraphs (2-4 sentences max).\n"
            "- Use bullet points (-) or numbered lists for multiple items.\n"
            "- Use **bold** for key terms and important conclusions.\n"
            "- Use markdown headers (###) to break up longer answers.\n"
            "- Avoid single dense walls of text.\n"
        )

        try:
            client = genai.Client(api_key=gemini_key)
            response = client.models.generate_content_stream(
                model='gemini-2.5-flash',
                contents=f"{system_instruction}\n\nUSER QUESTION: {request.message}",
                config=types.GenerateContentConfig(tools=[{"google_search": {}}])
            )
            for chunk in response:
                if chunk.text:
                    full_ai_response += chunk.text
                    yield chunk.text
                    await asyncio.sleep(0.015)
        except Exception as e:
            # 🔴 was a bare `except Exception: yield "..."` with no logging —
            # this made every AI failure invisible in the server logs.
            print(f"AI Generation Error: {e}")
            yield "⚠️ System Overloaded. AI is unavailable right now."

        if full_ai_response:
            try:
                supabase.table("messages").insert({
                    "workspace_id": request.workspace_id,
                    "role": "assistant",
                    "content": full_ai_response
                }).execute()
            except Exception as db_err:
                print(f"Failed to save AI msg: {db_err}")

    return StreamingResponse(streaming_generator(), media_type="text/plain")


@router.post("/ecosystem-support")
async def ecosystem_support_bot(req: SupportQuery):
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
async def global_search(q: str, current_user: dict = Depends(get_current_user)):
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