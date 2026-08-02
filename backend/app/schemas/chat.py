from pydantic import BaseModel
from typing import List, Dict, Any

class ChatRequest(BaseModel):
    query: str
    model_name: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    chat_history: List[Dict[str, Any]] = []
    is_offline: bool = False

class ChatResponse(BaseModel):
    response: str
    model_used: str
    status: str