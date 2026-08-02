import os
import asyncio
from google import genai 
from google.genai import types
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from dotenv import load_dotenv

from app.core.security import get_current_user
from app.core.database import get_db
from app.models.user import Message
from app.core.vector_store import get_workspace_vectorstore

# 🔴 Force .env to win every time
load_dotenv(override=True)

# SDK-কে নিশ্চিত করতে GEMINI_API_KEY ম্যানুয়ালি ডিফাইন করা
gemini_key = os.getenv("GEMINI_API_KEY")
if gemini_key:
    os.environ["GEMINI_API_KEY"] = gemini_key

router = APIRouter(tags=["AI Engine"])

class ChatRequest(BaseModel):
    message: str
    workspace_id: str

async def real_ai_streamer(user_message: str, workspace_id: str):
    full_ai_response = ""
    
    # 🔴 RAG Pipeline: Search ChromaDB for relevant uploaded documents
    context_text = ""
    try:
        vectorstore = get_workspace_vectorstore(workspace_id)
        # সবচেয়ে প্রাসঙ্গিক ৩টি পার্ট ফেচ করবে
        similar_docs = vectorstore.similarity_search(user_message, k=3)
        if similar_docs:
            context_text = "\n\n".join([doc.page_content for doc in similar_docs])
    except Exception as v_err:
        print(f"Vector search warning (No docs yet or empty DB): {v_err}")

    # Prompt Engineering with RAG Context
    if context_text:
        prompt = f"""You are an intelligent AI Assistant for this workspace. 
Answer the user's question using the provided context documents below. 
If the answer is not contained in the context, use your general knowledge but mention it.

--- CONTEXT FROM UPLOADED DOCUMENTS ---
{context_text}
---------------------------------------

USER QUESTION: {user_message}
"""
    else:
        prompt = user_message

    try:
        client = genai.Client(api_key=gemini_key)
        response = client.models.generate_content_stream(
            model='gemini-2.5-flash',
            contents=prompt,
            # 🔴 AI-কে রিয়েল-টাইম ইন্টারনেট অ্যাক্সেস দেওয়া হলো
            config=types.GenerateContentConfig(
                tools=[{"google_search": {}}]
            )
        )
        
        for chunk in response:
            if chunk.text:
                words = chunk.text.split(" ")
                for word in words:
                    if word:
                        full_ai_response += word + " "
                        yield f"data: {word} \n\n"
                        await asyncio.sleep(0.015) 
                yield "data:  \n\n"
                
        # Save AI Response to Database
        db = next(get_db())
        try:
            ai_msg = Message(workspace_id=workspace_id, role="ai", content=full_ai_response.strip())
            db.add(ai_msg)
            db.commit()
        except Exception as db_err:
            print(f"DB Save Error: {db_err}")
            
        yield "data: [DONE]\n\n"
        return

    except Exception as e:
        print(f"AI Generation Error: {e}")
        yield f"data: [System Error: {str(e)}]\n\n"
        yield "data: [DONE]\n\n"


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized request")

    # Save User Message to Database
    user_msg = Message(workspace_id=request.workspace_id, role="user", content=request.message)
    db.add(user_msg)
    db.commit()

    return StreamingResponse(
        real_ai_streamer(request.message, request.workspace_id),
        media_type="text/event-stream"
    )

@router.get("/history/{workspace_id}")
def get_chat_history(
    workspace_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    messages = db.query(Message).filter(Message.workspace_id == workspace_id).order_by(Message.created_at.asc()).all()
    return [{"id": str(m.id), "role": m.role, "content": m.content} for m in messages]