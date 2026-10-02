import os
from tavily import TavilyClient

class AIEngine:
    """Handles hybrid search (Local DB + Live Web)"""
    
    @staticmethod
    def fetch_live_web_data(query: str, max_results: int = 3) -> str:
        """Scrapes the live web for current geopolitical events if needed."""
        tavily_key = os.getenv("TAVILY_API_KEY")
        if not tavily_key:
            return "No web data available (API Key missing)."
            
        try:
            client = TavilyClient(api_key=tavily_key)
            response = client.search(query=query, max_results=max_results, include_answer=True)
            
            web_context = f"Live Summary: {response.get('answer', '')}\n\n"
            for r in response.get('results', []):
                web_context += f"Source: {r.get('title')}\nLink: {r.get('url')}\n\n"
            return web_context
        except Exception as e:
            print(f"Web Engine Error: {e}")
            return "Web search temporarily unavailable."