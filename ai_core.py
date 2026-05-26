import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

class AICoreEngine:
    """Core Engine to manage multiple LLM models and Agentic behavior."""
    
    @staticmethod
    def load_model(model_id: str, temperature: float = 0.1):
        """Dynamically loads the requested AI engine based on user selection."""
        if "gemini" in model_id.lower():
            return ChatGoogleGenerativeAI(model=model_id, temperature=temperature, google_api_key=os.getenv("GOOGLE_API_KEY"))
        elif "llama" in model_id.lower() or "qwen" in model_id.lower():
            return ChatGroq(model_name=model_id, temperature=temperature, groq_api_key=os.getenv("GROQ_API_KEY"))
        else:
            return ChatOpenAI(model_name=model_id, temperature=temperature, openai_api_key=os.getenv("OPENROUTER_API_KEY"), openai_api_base="https://openrouter.ai/api/v1")
            
    @staticmethod
    def get_strict_language_guard(is_bengali: bool) -> str:
        """Returns the ultimate prompt constraint to prevent hallucination and language mixing."""
        if is_bengali:
            return "CRITICAL: You MUST answer ENTIRELY in BENGALI (বাংলা ফন্ট). Do not use English words unless absolute necessary for terminology."
        else:
            return "CRITICAL: You MUST answer ENTIRELY in ENGLISH. Do not use Bengali under any circumstances."