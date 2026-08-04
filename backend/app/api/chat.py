import os
import asyncio
from google import genai 
from google.genai import types
from groq import Groq
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

# SDK-কে নিশ্চিত করতে GEMINI_API_KEY ম্যানুয়ালি ডিফাইন করা
gemini_key = os.getenv("GEMINI_API_KEY")
if gemini_key:
    os.environ["GEMINI_API_KEY"] = gemini_key

router = APIRouter(tags=["AI Engine"])

class ChatRequest(BaseModel):
    message: str
    workspace_id: str

async def real_ai_streamer(user_message: str, workspace_id: str):
    full_ai_response = ""
    
    # 🔴 1. RAG Pipeline: Fetch Metadata (Source & Page)
    context_text = ""
    try:
        vectorstore = get_workspace_vectorstore(workspace_id)
        # সবচেয়ে প্রাসঙ্গিক ৩টি খণ্ড ফেচ করবে
        similar_docs = vectorstore.similarity_search(user_message, k=3)
        
        if similar_docs:
            for doc in similar_docs:
                source_name = doc.metadata.get("source", "Unknown Document")
                page_number = doc.metadata.get("page", 0) + 1
                context_text += f"[Source: {source_name} | Page: {page_number}]\n{doc.page_content}\n\n"
                
    except Exception as v_err:
        print(f"Vector search warning (No docs yet or empty DB): {v_err}")

    # 🔴 2. Dynamic Prompt with Citation Instructions
    if context_text:
        prompt = f"""You are an intelligent AI Assistant for this university workspace. 
Answer the user's question using the provided context documents below. 

IMPORTANT RULE: If the answer is found in the context, you MUST cite the source and page number at the end of the relevant sentence (e.g., "According to the rules... [Source: syllabus.pdf, Page: 2]").
If the answer is not in the context, use your general knowledge but mention that it is not from the uploaded documents.

--- CONTEXT FROM UPLOADED DOCUMENTS ---
{context_text}
---------------------------------------

USER QUESTION: {user_message}
"""
    else:
        prompt = user_message

    try:
        # 🟢 1st Attempt: Google Gemini 2.5 Flash
        client = genai.Client(api_key=gemini_key)
        response = client.models.generate_content_stream(
            model='gemini-2.5-flash',
            contents=prompt,
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
                
    except Exception as gemini_err:
        print(f"⚠️ Gemini Failed ({gemini_err}). Switching to GROQ Fallback...")
        
        # 🟠 2nd Attempt: Fallback to Groq (Llama-3)
        try:
            groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
            groq_response = groq_client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {"role": "system", "content": "You are a helpful university AI assistant."},
                    {"role": "user", "content": prompt}
                ],
                stream=True
            )
            
            for chunk in groq_response:
                if chunk.choices[0].delta.content:
                    word = chunk.choices[0].delta.content
                    full_ai_response += word
                    yield f"data: {word.replace('\n', ' ')}\n\n"
                    await asyncio.sleep(0.015)
            yield "data:  \n\n"
            
        except Exception as groq_err:
            print(f"❌ Both Models Failed: {groq_err}")
            yield f"data: [System Overloaded: Both AI engines are currently unavailable. Please try again in a minute.]\n\n"
            yield "data: [DONE]\n\n"
            return


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