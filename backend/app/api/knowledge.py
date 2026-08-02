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

class GraphRequest(BaseModel):
    workspace_id: str
    topic: str

@router.post("/generate-graph")
async def generate_knowledge_graph(
    request: GraphRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    RAG (ChromaDB) থেকে ডেটা নিয়ে একটি Knowledge Graph (Nodes & Edges) জেনারেট করবে।
    এটি ফ্রন্টএন্ডে রিয়েল-টাইম মাইন্ড-ম্যাপ বা নেটওয়ার্ক গ্রাফ দেখানোর জন্য কাজ করবে
    """
    if not current_user.get("sub"):
        raise HTTPException(status_code=401, detail="Unauthorized")

    # ১. RAG থেকে ডেটা ফেচ করা
    context_text = ""
    try:
        vectorstore = get_workspace_vectorstore(request.workspace_id)
        similar_docs = vectorstore.similarity_search(request.topic, k=4)
        if similar_docs:
            context_text = "\n\n".join([doc.page_content for doc in similar_docs])
    except Exception as e:
        print(f"GraphRAG Context Warning: {e}")

    # ২. Gemini কে দিয়ে JSON ফরম্যাটে Nodes & Edges বের করে আনা
    prompt = f"""You are a GraphRAG extraction AI. Analyze the topic '{request.topic}' using the provided context.
Generate a Knowledge Graph with 'nodes' (entities/concepts) and 'edges' (relationships between them).

Return EXACTLY a valid JSON object in this format (no markdown, no formatting):
{{
  "nodes": [
    {{"id": "Concept1", "group": 1}},
    {{"id": "Concept2", "group": 2}}
  ],
  "edges": [
    {{"source": "Concept1", "target": "Concept2", "label": "influences"}}
  ]
}}

CONTEXT:
{context_text}
"""

    try:
        client = genai.Client(api_key=gemini_key)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        
        # AI অনেক সময় ব্যাকটিক (```json) দেয়, সেটা রিমুভ করে পিওর JSON পার্স করা
        raw_text = response.text.replace("```json", "").replace("```", "").strip()
        graph_data = json.loads(raw_text)
        
        return {"status": "success", "graph": graph_data}
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="AI failed to generate valid graph format.")
    except Exception as e:
        print(f"Graph Generation Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate Knowledge Graph.")