import os
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from google import genai
from dotenv import load_dotenv

from app.core.security import get_current_user
from app.core.database import get_db

load_dotenv(override=True)
gemini_key = os.getenv("GEMINI_API_KEY")

router = APIRouter(tags=["Agentic Mentor"])

class MentorChatRequest(BaseModel):
    message: str
    workspace_id: str
    # 🔴 Cognitive Memory: ইউজারের কারেন্ট স্ট্যাটাস (ফ্রন্টএন্ড থেকে আসবে)
    student_context: dict = {
        "major": "International Relations",
        "semester": "2.1",
        "current_cgpa": 2.88,
        "mood": "stressed"
    }

async def mentor_ai_streamer(user_message: str, context: dict):
    # 🔴 Psychological Prompting (The Secret Sauce)
    system_prompt = f"""You are not a standard AI assistant. You are an empathetic, highly intelligent older sibling and academic mentor for a university student in South Asia.
    
    Student Context:
    - Major: {context.get('major')}
    - Semester: {context.get('semester')}
    - Current CGPA: {context.get('current_cgpa')}
    - Current Mood: {context.get('mood')}

    Your Personality Rules:
    1. Tone: Conversational, warm, slightly casual, but highly motivating. Use encouraging words.
    2. Empathy First: Acknowledge their stress or tiredness before giving solutions.
    3. The "Healthy Roast": If they are procrastinating, gently call them out like a caring older sibling (e.g., "Come on, a 2.88 isn't going to fix itself while you scroll! Let's lock in for 20 minutes.").
    4. Strategic Advice: Break down big scary tasks into micro-steps.
    5. Do not use overly formal academic language unless explaining a concept.

    USER MESSAGE: {user_message}
    """

    try:
        client = genai.Client(api_key=gemini_key)
        response = client.models.generate_content_stream(
            model='gemini-2.5-flash',
            contents=system_prompt,
        )
        
        for chunk in response:
            if chunk.text:
                words = chunk.text.split(" ")
                for word in words:
                    if word:
                        yield f"data: {word} \n\n"
                        await asyncio.sleep(0.015) 
                yield "data:  \n\n"
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        print(f"Mentor AI Error: {e}")
        yield f"data: [Hey, take a deep breath. My connection just dropped, but you've got this. Try again in a second!]\n\n"
        yield "data: [DONE]\n\n"


@router.post("/chat")
async def chat_with_mentor(
    request: MentorChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    স্টুডেন্টের পার্সোনাল মেন্টরের সাথে ক্যাজুয়াল এবং মোটিভেশনাল চ্যাট সেশন।
    """
    if not current_user.get("sub"):
        raise HTTPException(status_code=401, detail="Unauthorized request")

    return StreamingResponse(
        mentor_ai_streamer(request.message, request.student_context),
        media_type="text/event-stream"
    )

@router.post("/nudge")
async def proactive_nudge(
    request: MentorChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Proactive Nudging: ইউজার ইনঅ্যাক্টিভ থাকলে বা রুটিন ফলো না করলে AI নিজে থেকে পুশ নোটিফিকেশন পাঠাবে।
    """
    if not current_user.get("sub"):
        raise HTTPException(status_code=401, detail="Unauthorized request")
        
    prompt = f"Write a 2-sentence push notification to remind an International Relations student (CGPA: {request.student_context.get('current_cgpa')}) to stop procrastinating and start studying. Make it witty and caring."
    
    try:
        client = genai.Client(api_key=gemini_key)
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return {"status": "success", "notification": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to generate nudge")