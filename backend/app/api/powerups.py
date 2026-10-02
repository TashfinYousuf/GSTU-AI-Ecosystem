import os
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from google import genai
from dotenv import load_dotenv

from app.core.security import get_current_user
from app.core.vector_store import get_workspace_vectorstore

load_dotenv(override=True)

gemini_key = os.getenv("GEMINI_API_KEY")

router = APIRouter()

logger = logging.getLogger(__name__)


def call_gemini_json(prompt: str) -> dict:
    """Shared helper — every endpoint in this file was duplicating this exact
    client-init + JSON-cleanup pattern five times. One place to fix it now."""
    client = genai.Client(api_key=gemini_key)
    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
    raw_text = response.text.replace("```json", "").replace("```", "").strip()
    return json.loads(raw_text)


# --- Request Models ---
class ResearchRequest(BaseModel):
    model_config = {"extra": "forbid"}
    topic: str
    task_mode: str  # "gap_hunter" or "literature_review"


class RoastRequest(BaseModel):
    model_config = {"extra": "forbid"}
    question: str
    answer: str


class PredictorRequest(BaseModel):
    model_config = {"extra": "forbid"}
    workspace_id: Optional[str] = None
    course_code: str


class GamifyRequest(BaseModel):
    model_config = {"extra": "forbid"}
    
    """Matches the shape the frontend already sends to /powerups/gamify for
    debate & judge — {topic, feature_type, extra_data}."""
    topic: str
    feature_type: str
    extra_data: dict = {}


# ==========================================
# 🔬 1. ELITE RESEARCH OS (Gap Hunter & Lit Review)
# ==========================================
@router.post("/research")
async def generate_research_os(req: ResearchRequest, current_user: dict = Depends(get_current_user)):
    if not current_user.get("sub"):
        raise HTTPException(status_code=401, detail="Unauthorized")

    if req.task_mode == "gap_hunter":
        prompt = f"""Act as an Elite Research Analyst. Analyze the topic: '{req.topic}'.
        Identify what has been heavily researched and find the 'Missing Gap' that a university student can use for a thesis.
        Return EXACTLY a valid JSON object:
        {{
            "existing_research_focus": ["point 1", "point 2", "point 3"],
            "the_gap": "Detailed explanation of what is missing in current literature.",
            "proposed_thesis_titles": ["Title 1", "Title 2", "Title 3"]
        }}"""
    else:
        prompt = f"""Act as an Elite Academic Reviewer. Synthesize literature on: '{req.topic}'.
        Return EXACTLY a valid JSON object:
        {{
            "main_arguments": ["arg 1", "arg 2", "arg 3"],
            "areas_of_agreement": "What most scholars agree on...",
            "areas_of_disagreement": "Where the debate lies...",
            "key_scholars": ["Scholar A", "Scholar B"]
        }}"""

    try:
        return {"status": "success", "data": call_gemini_json(prompt)}
    except Exception as e:
        print(f"Research OS Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate research data.")


# ==========================================
# 😈 2. GEN-Z SAVAGE ROAST MODE
# ==========================================
@router.post("/roast")
async def savage_roast_mode(req: RoastRequest, current_user: dict = Depends(get_current_user)):
    if not current_user.get("sub"):
        raise HTTPException(status_code=401, detail="Unauthorized")

    prompt = f"""Act as a brilliant but highly sarcastic University Professor.
    Question asked: "{req.question}"
    Student's Answer: "{req.answer}"

    If the answer is completely wrong or foolish, roast them brutally but in a funny, Gen-Z friendly way.
    Then explain the real concept.
    Return EXACTLY a valid JSON object:
    {{
        "is_correct": false,
        "roast_text": "The savage roast or a compliment if they actually got it right.",
        "correct_concept": "The actual academic explanation."
    }}"""

    try:
        return {"status": "success", "data": call_gemini_json(prompt)}
    except Exception as e:
        print(f"Roast mode error: {e}")  # 🔴 was swallowing the real error entirely — now logged
        raise HTTPException(status_code=500, detail="Roast engine failed.")


# ==========================================
# 🔮 3. AI EXAM PREDICTOR (RAG POWERED)
# ==========================================
@router.post("/predict")
async def exam_predictor(req: PredictorRequest, current_user: dict = Depends(get_current_user)):
    if not current_user.get("sub"):
        raise HTTPException(status_code=401, detail="Unauthorized")

    # 🔴 RAG Integration: Fetching syllabus/past papers from Global Knowledge Base + Workspace
    similar_docs = []
    
    # 1. Fetch from Global Knowledge Base (Where official syllabus, course notes, past exams are stored)
    try:
        kb_vs = get_workspace_vectorstore("global_knowledge_base")
        kb_matches = kb_vs.similarity_search(f"{req.course_code} syllabus past questions exam curriculum topics", k=4)
        if kb_matches:
            similar_docs.extend(kb_matches)
    except Exception as kb_err:
        logger.warning(f"Global KB search warning for exam predictor: {kb_err}")

    # 2. Fetch from Workspace if specified
    if req.workspace_id:
        try:
            ws_vs = get_workspace_vectorstore(req.workspace_id)
            ws_matches = ws_vs.similarity_search(f"{req.course_code} exam question syllabus lecture", k=3)
            if ws_matches:
                similar_docs.extend(ws_matches)
        except Exception as ws_err:
            logger.warning(f"Workspace search warning for exam predictor: {ws_err}")

    if similar_docs:
        context_parts = []
        for d in similar_docs:
            source = d.metadata.get("source") or d.metadata.get("filename") or "Course Material"
            page = d.metadata.get("page_number") or d.metadata.get("page")
            page_info = f", Page {page}" if page else ""
            context_parts.append(f"[Source: {source}{page_info}]\n{d.page_content}")
        context_text = "\n\n".join(context_parts)
    else:
        context_text = "No past questions or syllabus found in DB. Base prediction on standard university curriculum."

    prompt = f"""Act as a Chief University Exam Controller and Senior Professor for Course '{req.course_code}'.
Analyze the following curriculum, syllabus, and past exam context retrieved from the Department's Knowledge Base:

--- DEPARTMENT KNOWLEDGE BASE & SYLLABUS CONTEXT ---
{context_text}
---------------------------------------------------

Based on the syllabus coverage, repeated themes, and fundamental theoretical importance, mathematically predict 3 to 5 highly probable exam topics.
For each topic:
1. "topic": Clear, academic title of the topic/question area.
2. "probability": Calculated likelihood percentage (between 65 and 95).
3. "reason": Analytical justification referencing the syllabus units, historical question patterns, or core departmental focus (cite source file/book and page if available in context).

Return EXACTLY a valid JSON object:
{{
    "predictions": [
        {{"topic": "Topic Name", "probability": 85, "reason": "Why it might appear based on syllabus or past trends"}}
    ]
}}"""

    try:
        return {"status": "success", "data": call_gemini_json(prompt)}
    except Exception as e:  # 🔴 THE CRASH: was `except Exception as e:a` — a bare
        # syntax error that made this ENTIRE FILE fail to import, which
        # crashes the whole FastAPI app at startup (main.py's
        # `from app.api import ..., powerups, ...` throws immediately).
        # This is almost certainly the real cause of "network issues" —
        # the backend process wasn't running at all.
        print(f"Predictor error: {e}")
        raise HTTPException(status_code=500, detail="Predictor failed.")


# ==========================================
# ⚔️ 4. DEBATE ARENA — was completely missing from this file.
# The frontend has been calling POST /powerups/gamify with
# feature_type "debate"/"judge" this whole time with NO matching route,
# meaning every debate message and every judge verdict has been 404ing.
# Ported from the Streamlit source (Tab 2 > Arena & Battle), minus the
# voice/Whisper transcription and Tavily live-search calls — the current
# React Debate Arena only sends text, so those pieces have no caller yet.
# Add them back here later if you build voice input into the React page.
# ==========================================
@router.post("/gamify")
async def powerups_gamify(req: GamifyRequest, current_user: dict = Depends(get_current_user)):
    if not current_user.get("sub"):
        raise HTTPException(status_code=401, detail="Unauthorized")

    if req.feature_type == "debate":
        return await _handle_debate(req)
    elif req.feature_type == "judge":
        return await _handle_judge(req)

    raise HTTPException(status_code=400, detail=f"Unknown feature_type '{req.feature_type}' for /powerups/gamify.")


async def _handle_debate(req: GamifyRequest):
    persona = req.extra_data.get("persona", "Aggressive Realist")
    history = req.extra_data.get("history", [])
    memory_str = "\n".join([f"{m.get('role')}: {m.get('content')}" for m in history[-6:]])

    prompt = f"""Act as a master debater and Elite Geopolitical Analyst with a '{persona}' persona.

Debate History:
{memory_str}

User's latest point: {req.topic}

INSTRUCTIONS: Counter the user aggressively using solid, well-reasoned facts and IR theory.
Acknowledge their point but dismantle it. Answer with short, rational, direct & logical sentences, maximum 3 sentences per response. Do not return JSON —
respond with plain argumentative text only."""

    try:
        client = genai.Client(api_key=gemini_key)
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return {"status": "success", "data": {"ai_response": response.text.strip()}}
    except Exception as e:
        print(f"Debate generation error: {e}")
        raise HTTPException(status_code=500, detail="Debate engine failed to respond.")


async def _handle_judge(req: GamifyRequest):
    transcript = req.extra_data.get("transcript", "")
    if not transcript:
        raise HTTPException(status_code=400, detail="No transcript provided to judge.")

    prompt = f"""You are an unbiased IR Debate Judge.
Review the debate transcript between the User and AI Opponent.
Evaluate arguments based strictly on authentic International Relations (IR) theory,
historical data, current geopolitical dynamics, and factual accuracy.

Debate transcript:
{transcript}

Strictly output ONLY valid JSON in exactly this shape:
{{
    "winner": "User or AI",
    "user_score": <int 0-100 based on factual accuracy>,
    "ai_score": <int 0-100 based on factual accuracy>,
    "verdict_summary": "<3-sentence analysis of why the winner won>"
}}"""

    try:
        return {"status": "success", "data": call_gemini_json(prompt)}
    except Exception as e:
        print(f"Judge AI error: {e}")
        raise HTTPException(status_code=500, detail="Judge AI failed to parse a verdict. Try again.")