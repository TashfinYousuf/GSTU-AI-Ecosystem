from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.core.security import get_current_user
from app.services.core_agents import generate_research_assistance, generate_genz_features

router = APIRouter(tags=["Scholar Hub"])

class ActionRequest(BaseModel):
    topic: str = None
    task_mode: str = None
    question: str = None
    answer: str = None

@router.post("/{endpoint}")
async def process_scholar_action(endpoint: str, req: ActionRequest, current_user: dict = Depends(get_current_user)):
    """Advanced Scholar Hub - Handles both Research and Critical Peer Review (Roast)"""
    if not current_user.get("sub"):
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    try:
        if endpoint == "research":
            # Map task_mode to backend logic
            task_type = "Research Gap Hunter" if req.task_mode == "gap_hunter" else "Literature Review"
            response = generate_research_assistance(topic=req.topic, task_type=task_type)
            
        elif endpoint == "roast":
            # Map Critical Peer Review to the Gen-Z Roast Engine
            response = generate_genz_features(topic=req.question, feature_type="roast", extra_data={"answer": req.answer})
            
        else:
            raise HTTPException(status_code=404, detail="Invalid endpoint")

        if response.get("status") == "error":
            raise HTTPException(status_code=500, detail=response.get("message"))
            
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))