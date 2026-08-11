import os
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from google import genai
from dotenv import load_dotenv

from app.core.security import get_current_user
from app.core.vector_store import get_workspace_vectorstore

load_dotenv(override=True)
gemini_key = os.getenv("GEMINI_API_KEY")

router = APIRouter(tags=["Power-Ups"])


def call_gemini_json(prompt: str) -> dict:
    """Shared helper — every endpoint in this file was duplicating this exact
    client-init + JSON-cleanup pattern five times. One place to fix it now."""
    client = genai.Client(api_key=gemini_key)
    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
    raw_text = response.text.replace("```json", "").replace("```", "").strip()
    return json.loads(raw_text)


# --- Request Models ---
class ResearchRequest(BaseModel):
    topic: str
    task_mode: str  # "gap_hunter" or "literature_review"


class RoastRequest(BaseModel):
    question: str
    answer: str


class PredictorRequest(BaseModel):
    workspace_id: str
    course_code: str


class GamifyRequest(BaseModel):
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

    context_text = "No past questions or syllabus found in DB. Base prediction on standard university curriculum."
    try:
        vectorstore = get_workspace_vectorstore(req.workspace_id)
        similar_docs = vectorstore.similarity_search(req.course_code, k=4)
        if similar_docs:
            context_text = "\n".join([doc.page_content for doc in similar_docs])
    except Exception as e:
        print(f"RAG context fetch failed (falling back to generic prediction): {e}")

    prompt = f"""Act as an AI Exam Predictor for the university course '{req.course_code}'.
    Analyze this context from past papers/syllabus: {context_text}
    Predict 3 highly probable exam topics.
    Return EXACTLY a valid JSON object:
    {{
        "predictions": [
            {{"topic": "Topic Name", "probability": 85, "reason": "Why it might appear"}}
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
Acknowledge their point but dismantle it. Keep it under 150 words. Do not return JSON —
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