from langchain_core.tools import tool

@tool
def analyze_student_progress(user_id: str) -> str:
    """Analyzes the student's progress and returns a summary. Use this when the user asks about their performance."""
    return f"Data indicates that student {user_id} has been actively querying International Relations topics. Strong performance in Political Geography, but needs more focus on French Methodology."

@tool
def fetch_latest_geopolitics(topic: str) -> str:
    """Fetches the latest strategic geopolitics insights on a specific topic."""
    return f"Recent strategic movements regarding {topic} suggest high diplomatic tensions and policy shifts. Advise user to monitor global news closely."

# The list exported to app.py
astra_core_tools = [analyze_student_progress, fetch_latest_geopolitics]