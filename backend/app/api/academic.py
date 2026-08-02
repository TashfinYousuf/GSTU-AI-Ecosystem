from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

router = APIRouter()

class RoutineRequest(BaseModel):
    study_hours: int = 4
    focus_areas: List[str] = ["International Relations Theories", "Political Geography"]

class ExamRequest(BaseModel):
    topic: str
    difficulty: str = "University Level"

@router.post("/routine")
async def generate_smart_routine(request: RoutineRequest):
    """
    ইউজারের ফোকাস এরিয়া এবং সময়ের ওপর ভিত্তি করে একটি প্রোডাক্টিভ স্টাডি রুটিন তৈরি করবে।
    (ভবিষ্যতে এখানে LLM বসিয়ে ডাইনামিক করা হবে, আপাতত ফ্রন্টএন্ডের জন্য স্ট্রাকচার রেডি)
    """
    try:
        # TODO: Connect with Groq/Llama for dynamic generation
        return {
            "status": "success",
            "message": "Routine generated successfully",
            "data": [
                {"time": "08:00 AM", "task": f"Review notes on {request.focus_areas[0]}", "type": "study"},
                {"time": "10:30 AM", "task": "Read primary sources on Global Power Dynamics", "type": "research"},
                {"time": "12:00 PM", "task": "Break & Academic Refresh", "type": "break"},
                {"time": "02:00 PM", "task": "Build AI Ecosystem Architecture (FastAPI & Next.js)", "type": "project"},
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/mock-exam")
async def generate_mock_exam(request: ExamRequest):
    """
    নির্দিষ্ট টপিকের ওপর ডিপার্টমেন্টাল স্ট্যান্ডার্ডের মক এক্সাম জেনারেট করবে
    """
    try:
         # TODO: Connect with RAG + LLM to fetch department past papers
         return {
             "status": "success",
             "topic": request.topic,
             "questions": [
                 {"q_no": 1, "question": f"Critically analyze the impact of {request.topic} on modern global policies.", "marks": 10},
                 {"q_no": 2, "question": "Evaluate the theoretical frameworks that support this concept.", "marks": 10}
             ]
         }
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))