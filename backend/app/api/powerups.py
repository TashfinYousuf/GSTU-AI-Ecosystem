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

router = APIRouter()

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

# ==========================================
# 🔬 1. ELITE RESEARCH OS (Gap Hunter & Lit Review)
# ==========================================
@router.post("/research")
async def generate_research_os(
    req: ResearchRequest,
    current_user: dict = Depends(get_current_user)
):
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
        client = genai.Client(api_key=gemini_key)
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        raw_text = response.text.replace("```json", "").replace("```", "").strip()
        return {"status": "success", "data": json.loads(raw_text)}
    except Exception as e:
        print(f"Research OS Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate research data.")

# ==========================================
# 😈 2. GEN-Z SAVAGE ROAST MODE
# ==========================================
@router.post("/roast")
async def savage_roast_mode(
    req: RoastRequest,
    current_user: dict = Depends(get_current_user)
):
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
        client = genai.Client(api_key=gemini_key)
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        raw_text = response.text.replace("```json", "").replace("```", "").strip()
        return {"status": "success", "data": json.loads(raw_text)}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Roast engine failed.")

# ==========================================
# 🔮 3. AI EXAM PREDICTOR (RAG POWERED)
# ==========================================
@router.post("/predict")
async def exam_predictor(
    req: PredictorRequest,
    current_user: dict = Depends(get_current_user)
):
    if not current_user.get("sub"):
        raise HTTPException(status_code=401, detail="Unauthorized")

    # 🔴 RAG Integration: Fetching syllabus/past papers from Vector DB
    context_text = "No past questions or syllabus found in DB. Base prediction on standard university curriculum."
    try:
        vectorstore = get_workspace_vectorstore(req.workspace_id)
        similar_docs = vectorstore.similarity_search(req.course_code, k=4)
        if similar_docs:
            context_text = "\n".join([doc.page_content for doc in similar_docs])
    except Exception:
        pass

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
        client = genai.Client(api_key=gemini_key)
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        raw_text = response.text.replace("```json", "").replace("```", "").strip()
        return {"status": "success", "data": json.loads(raw_text)}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Predictor failed.")