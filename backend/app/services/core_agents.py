import os
import re
import json
import traceback
import logging
import random
import datetime
from langchain_groq import ChatGroq
from dotenv import load_dotenv

# LangChain Imports
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from app.services.analytics_engine import generate_progress_report
from app.services.memory_db import save_study_plan


load_dotenv()
logger = logging.getLogger(__name__)


def intent_router(query: str):
    """
    Layer 1: Classifies user query to save 50%+ API costs.
    Returns: 'greeting', 'live_news', 'research', or 'academic_rag'
    """
    query_lower = query.lower()
    
    # 1. Greetings & Simple Chitchat (0 RAG, 0 Web Search cost)
    greetings = ["hi", "hello", "hey", "thanks", "thank you", "good morning", "how are you", "who are you"]
    if query_lower in greetings or len(query_lower.split()) <= 2:
        return "greeting"
        
    # 2. Live News / Contemporary Events (Requires Web Search)
    news_keywords = ["recent", "news", "update", "now", "today", "2025", "2026", "current event"]
    if any(word in query_lower for word in news_keywords):
        return "live_news"
        
    # 3. Complex Research / Compare (Requires Heavy Model)
    research_keywords = ["compare", "analyze", "literature review", "critique", "thesis"]
    if any(word in query_lower for word in research_keywords):
        return "research"
        
    # 4. Default: Core Academic Questions (RAG Only)
    return "academic_rag"


# ==========================================
# 1. LLM ORCHESTRATOR
# ==========================================
def get_specialist_llm(intent="academic_rag"):
    """
    Layer 2 & 3: Multi-Provider Fallback & Model Routing
    Groq -> Gemini -> OpenRouter
    """
    # Fetch Keys safely
    groq_key = os.getenv("GROQ_API_KEY")
    gemini_key = os.getenv("GOOGLE_API_KEY")
    openrouter_key = os.getenv("OPENROUTER_API_KEY")

    # --- ROUTING LOGIC BASED ON INTENT ---
    if intent == "research":
        # Complex task: Try to use best model first
        primary_model = "llama-3.3-70b-versatile"
        fallback_model = "gemini-1.5-pro" # Or gemini-1.5-flash
    else:
        # Standard task: Use fast/cheap models
        primary_model = "llama-3.1-8b-instant"
        fallback_model = "gemini-1.5-flash"

    # 1. PRIMARY PROVIDER (Groq - Super Fast)
    primary_llm = ChatGroq(
        model_name=primary_model, 
        temperature=0.2, 
        api_key=groq_key, 
        max_retries=1
    )

    # 2. FALLBACK PROVIDER 1 (Google Gemini - High Rate Limits)
    fallback_1 = ChatGoogleGenerativeAI(
        model=fallback_model, 
        temperature=0.2, 
        google_api_key=gemini_key, 
        max_retries=1
    )

    # 3. FALLBACK PROVIDER 2 (OpenRouter - Universal Backup)
    fallback_2 = ChatOpenAI(
        model_name="meta-llama/llama-3-8b-instruct:free", 
        temperature=0.2, 
        api_key=openrouter_key, 
        base_url="https://openrouter.ai/api/v1", 
        max_retries=1
    )

    # 🔴 THE MAGIC: Bind them together for automatic failover!
    robust_llm = primary_llm.with_fallbacks([fallback_1, fallback_2])
    
    return robust_llm


# ==========================================
# 2. STUDY PLANNER AGENT (CGPA BOOST LOGIC)
# ==========================================
def generate_cgpa_boost_plan(user_id: str):
    """
    ইউজারের উইকনেস রিপোর্ট এনালাইজ করে ৭ দিনের ডাইনামিক রুটিন তৈরি করবে এবং ডাটাবেসে সেভ করবে।
    """
    import json
    import re
    import traceback
    
    try:
        # Step 1: Hook the Analytics Engine
        report = generate_progress_report(user_id)
        
        # Step 2: Initialize Agent
        llm = get_specialist_llm()
        
        # Step 3: Agentic Prompt Design
        system_prompt = """You are an elite Academic AI Agent for the International Relations (IR) Department.
Your goal is to create a highly optimized, realistic 7-day Study Plan for an undergrad student based on their analytics report.

CRITICAL INSTRUCTIONS:
1. Focus heavily on their 'focus_needed_on' (weaknesses) to boost their CGPA.
2. Ensure the plan balances hard topics with lighter revision of 'strong_areas'.
3. You MUST output ONLY valid JSON in the exact format below. Do not include markdown blocks, intros, or outros.

JSON FORMAT:
{{
    "day_1": {{"focus_subject": "Course Name", "strategy": "What specifically to study and how"}},
    "day_2": {{"focus_subject": "Course Name", "strategy": "What specifically to study and how"}},
    "day_3": {{"focus_subject": "Course Name", "strategy": "What specifically to study and how"}},
    "day_4": {{"focus_subject": "Course Name", "strategy": "What specifically to study and how"}},
    "day_5": {{"focus_subject": "Course Name", "strategy": "What specifically to study and how"}},
    "day_6": {{"focus_subject": "Course Name", "strategy": "What specifically to study and how"}},
    "day_7": {{"focus_subject": "Mock Test / Review", "strategy": "Testing knowledge"}},
    "ai_advice": "A short, highly motivational advice based on their growth trend."
}}"""

        human_prompt = "Here is the student's current academic analytics report: {report_data}\n\nGenerate the 7-day CGPA Boost Plan JSON now."
        
        from langchain_core.prompts import ChatPromptTemplate
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", human_prompt)
        ])
        
        # Step 4: Execute Chain
        chain = prompt_template | llm
        response = chain.invoke({"report_data": json.dumps(report)})
        
        # 🔴 THE ULTIMATE JSON EXTRACTOR
        clean_text = response.content.strip()
        start_idx = clean_text.find('{')
        end_idx = clean_text.rfind('}')
        
        if start_idx != -1 and end_idx != -1:
            clean_json_str = clean_text[start_idx:end_idx+1]
            plan_json = json.loads(clean_json_str)
            
            # Step 5: Parse and Save to Database (Ensure save_study_plan saves to "smart_routines")
            save_success = save_study_plan(user_id=user_id, plan_type="7-Day CGPA Boost", plan_data=plan_json)
            
            if save_success:
                return {"status": "success", "plan": plan_json}
            else:
                return {"status": "error", "message": "⚠️ Failed to save the plan to database."}
        else:
            return {"status": "error", "message": "⚠️ AI Output did not contain valid JSON."}

    except json.JSONDecodeError:
        return {"status": "error", "message": "⚠️ AI Output parsing failed. Invalid JSON structure."}
    
    except Exception as e:
    # 🔴 X-RAY DEBUGGER: Catch exactly where it crashed
        error_trace = traceback.format_exc()
        logger.error(f"Study Planner Agent Crash: {error_trace}")
        return {"status": "error", "message": f"System Crash: {str(e)}\n\nTraceback: {error_trace}"}
    

# ====================================================
# 3. ASSESSMENT AGENT (TEACHER SUITE & MOCK EXAMS)
# ====================================================
def generate_smart_assessment(topic: str, user_role: str):
    """
    University standard dynamic assessment generator.
    Strictly follows Academic Books + Contemporary updates.
    """
    try:
        llm = get_specialist_llm()
        random_seed = random.randint(10000, 99999)
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if user_role == "Faculty" or user_role == "Admin":
            system_prompt = """You are an Elite Academic Question Setter for the International Relations (IR) Department.
Your task is to generate a university-standard question paper based STRICTLY on core academic textbooks, theories, and the latest contemporary geopolitical events (RAG context).
Randomness Seed: {random_seed} (Timestamp: {current_time})
CRITICAL: DO NOT repeat generic or common questions. Think out of the box.

Output EXACTLY in this JSON format (No markdown ticks, just raw JSON):
{{
    "assessment_type": "Faculty Question Paper",
    "mcqs": [
        {{"q": "Question 1 (Critical & Analytical)", "options": ["A", "B", "C", "D"], "answer": "Correct Option"}}
        // Generate EXACTLY 10 tough MCQs
    ],
    "broad_questions": [
        {{"q": "Broad Q1", "difficulty": "Critical", "expected_points": ["Theory 1", "Recent Event Link"]}},
        {{"q": "Broad Q2", "difficulty": "Critical", "expected_points": ["Theory 1", "Recent Event Link"]}},
        {{"q": "Broad Q3", "difficulty": "Medium", "expected_points": ["Point 1", "Point 2"]}},
        {{"q": "Broad Q4", "difficulty": "Medium", "expected_points": ["Point 1", "Point 2"]}},
        {{"q": "Broad Q5", "difficulty": "Easy", "expected_points": ["Point 1", "Point 2"]}},
        {{"q": "Broad Q6", "difficulty": "Easy", "expected_points": ["Point 1", "Point 2"]}}
    ]
}}"""
        else:
            system_prompt = """You are a strict University Professor conducting a full Mock Exam for an IR student.
Create a curriculum-standard Mock Exam paper based strictly on core academic books and latest contemporary events (RAG context).

Exam Rules: Time: 3 Hours | Full Marks: 60 | Answer any 4 questions (15 Marks each).
Include EXACTLY 6 questions (2 Critical, 2 Medium, 2 Easy).
Randomness Seed: {random_seed} (Timestamp: {current_time})
CRITICAL: The question MUST be different every single time. Combine real-world recent events with core theories to create unique, thought-provoking questions.

Output EXACTLY in this JSON format (No markdown ticks, just raw JSON):
{{
    "assessment_type": "Mock Exam",
    "exam_rules": "Time: 3 Hours | Full Marks: 60 | Answer any 4 questions (15 Marks each)",
    "questions": [
        {{"q": "Question 1 (Scenario based)", "difficulty": "Critical", "hints": ["Hint 1", "Hint 2"], "key_points": ["Must mention Realism", "Must link to current event"],
            "model_answer": "A perfect 100-word ideal answer for this specific question."}},
        {{"q": "Question 2 (Analytical)", "difficulty": "Critical", "hints": ["Hint 1", "Hint 2"], "key_points": ["Must mention Realism", "Must link to current event"],
            "model_answer": "A perfect 100-word ideal answer for this specific question."}},
        {{"q": "Question 3 (Theoretical)", "difficulty": "Medium", "hints": ["Hint 1", "Hint 2"], "key_points": ["Must mention Realism", "Must link to current event"],
            "model_answer": "A perfect 100-word ideal answer for this specific question."}},
        {{"q": "Question 4 (Comparative)", "difficulty": "Medium", "hints": ["Hint 1", "Hint 2"], "key_points": ["Must mention Realism", "Must link to current event"],
            "model_answer": "A perfect 100-word ideal answer for this specific question."}},
        {{"q": "Question 5 (Conceptual)", "difficulty": "Easy", "hints": ["Hint 1", "Hint 2"], "key_points": ["Must mention Realism", "Must link to current event"],
            "model_answer": "A perfect 100-word ideal answer for this specific question."}},
        {{"q": "Question 6 (Direct)", "difficulty": "Easy", "hints": ["Hint 1", "Hint 2"], "key_points": ["Must mention Realism", "Must link to current event"],
            "model_answer": "A perfect 100-word ideal answer for this specific question."}}
    ]
}}"""

        prompt_template = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Topic for Assessment: {topic}\n\nGenerate the assessment JSON now. Ensure it reflects standard university curriculum.")
        ])
        
        chain = prompt_template | llm
        response = chain.invoke({
            "topic": topic,
            "random_seed": random_seed,
            "current_time": current_time
        })
        
        clean_json_str = response.content.strip().replace("```json", "").replace("```", "").strip()
        
        try:
            assessment_json = json.loads(clean_json_str)
            return {"status": "success", "data": assessment_json}
        except json.JSONDecodeError:
            return {"status": "error", "message": f"Failed to parse JSON. Raw: {clean_json_str}"}

    except Exception as e:
        logger.error(f"Assessment Agent Error: {str(e)}")
        return {"status": "error", "message": str(e)}
    

# =================================================
# 4. ELITE RESEARCH OS (GAP HUNTER & LIT REVIEW)
# =================================================
def generate_research_assistance(topic: str, task_type: str):
    """
    IR Students-দের জন্য PhD লেভেলের লিটারেচার রিভিউ এবং রিসার্চ গ্যাপ অ্যানালাইসিস করবে।
    task_type: "Literature Review" or "Research Gap Hunter"
    """
    try:
        llm = get_specialist_llm()
        
        if task_type == "Research Gap Hunter":
            system_prompt = """You are a World-Class Academic Research Director.
Your job is to find the 'Research Gap' for a thesis topic.
Analyze existing research trends and point out what is MISSING (e.g., geopolitical implications, economic factors, unexplored regions).
Output EXACTLY in this JSON format:
{{
    "task": "Research Gap Analysis",
    "existing_research_focus": ["Point 1", "Point 2"],
    "the_gap": "A powerful 2-3 sentence explanation of what is missing in current literature.",
    "proposed_thesis_titles": ["Title 1", "Title 2", "Title 3"]
}}"""
        else:  # Literature Review
            system_prompt = """You are a World-Class Academic Research Assistant.
Provide a structured Literature Review synthesis for the given topic.

Output EXACTLY in this JSON format:
{{
    "task": "Literature Review Synthesis",
    "main_arguments": ["Argument 1", "Argument 2"],
    "areas_of_agreement": "What scholars agree on.",
    "areas_of_disagreement": "What scholars debate on.",
    "key_scholars": ["Scholar 1", "Scholar 2"]
}}"""

        prompt_template = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Research Topic: {topic}\n\nExecute the {task_type} and output JSON.")
        ])
        
        chain = prompt_template | llm
        response = chain.invoke({
            "topic": topic,
            "task_type": task_type
        })
        
        clean_json_str = response.content.strip().replace("```json", "").replace("```", "").strip()
        
        try:
            research_json = json.loads(clean_json_str)
            return {"status": "success", "data": research_json}
        except json.JSONDecodeError:
            return {"status": "error", "message": f"JSON Parse Failed. Raw: {clean_json_str}"}

    except Exception as e:
        logger.error(f"Research Agent Error: {str(e)}")
        return {"status": "error", "message": str(e)}



# ==========================================
# 5. GEN-Z GAMIFIED EDTECH ENGINE
# ==========================================
def generate_genz_features(topic: str, feature_type: str, extra_data: dict = None):
    try:
        llm = get_specialist_llm()
        messages = []
        
        if feature_type == "debate":
            system_prompt = """You are a master debater and geopolitical thinker.
            Counter the user's argument aggressively. 
            CRITICAL RULES: 
            1. Respond in the EXACT SAME LANGUAGE as the user (Bengali or English).
            2. Keep it punchy, direct, and SHORT (Maximum 3 sentences)."""
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=f"Argument: {topic}")]

        elif feature_type == "roast":
            student_ans = extra_data.get("answer", "") if extra_data else ""
            system_prompt = """You are a Savage, Brutally Honest Academic Professor.
            Evaluate the student's answer conceptually. 
            If wrong: ROAST them brutally with dark humor/Gen-Z slang, then provide the correct concept.
            If correct: Give a sarcastic compliment.
            Output EXACTLY in this JSON format without markdown ticks:
            {
                "is_correct": false,
                "roast_text": "The brutal roast or sarcastic compliment",
                "correct_concept": "The actual academic truth (short)"
            }"""
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=f"Q: {topic}\nAns: {student_ans}")]
        
        elif feature_type == "flashcards":
            difficulty = extra_data.get("difficulty", "Medium") if extra_data else "Medium"
            # 🔴 Separated f-string from the JSON block to ensure clean single {} brackets
            system_prompt = f"You are an AI creating a highly addictive, gamified MCQ flashcard game.\nCurrent Difficulty Level: {difficulty}\n"
            system_prompt += """ CRITICAL RULES:
            1. Make the question DIRECT, SHORT, and TO THE POINT (Max 1-2 lines).
            2. Use easy but standard academic language.
            3. Ensure the question is 100% UNIQUE.
            4. If difficulty is Hard, ask analytical/conceptual questions. If Easy, ask direct factual definitions.
            
            Output EXACTLY in this JSON format without markdown ticks:
            {
                "flashcards": [
                    {
                        "q": "Short question here?", 
                        "options": ["A. Option", "B. Option", "C. Option", "D. Option"], 
                        "correct_option": "A. Option", 
                        "explanation": "1 short sentence explanation."
                    }
                ]
            }"""
            # Using single braces inside double braces for string formatting safety in python
            messages = [SystemMessage(content=system_prompt.replace("{{", "{").replace("}}", "}")), HumanMessage(content=f"Topic: {topic}\nGenerate 5 unique flashcards for a continuous swipe game.")]

        elif feature_type == "predictor":
            rag_context = extra_data.get("context", "No direct DB context found.") if extra_data else ""
            system_prompt = """You are an Elite AI Exam Predictor. 
            Based on the provided RAG Context (Syllabus/Past papers), mathematically predict the most probable exam topics.
            Output EXACTLY in this JSON format without markdown ticks:
            {
                "predictions": [
                    {"topic": "Predicted Topic 1", "probability": 85, "reason": "Based on past frequency..."}
                ]
            }"""
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=f"Course: {topic}\nRAG Context: {rag_context}")]
        
        elif feature_type == "judge":
            transcript = extra_data.get("transcript", "") if extra_data else ""
            system_prompt = """You are an Elite Academic Debate unbiased Judge (IR Specialist).
            Review the debate transcript between the User and AI Opponent.
            Evaluate arguments based strictly on authentic International Relations (IR) books, historical data, current geopolitics dynamics and factual accuracy.
            Output EXACTLY in this JSON format without markdown ticks:
            {
                "winner": "User or AI",
                "user_score": <int 0-100 based on factual accuracy>,
                "ai_score": <int 0-100 based on factual accuracy>,
                "verdict_summary": "<3-sentence deep analysis of why the winner won, explicitly mentioning who had better 2026 factual accuracy.>"
    
            }"""
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=f"Transcript:\n{transcript}")]

        # 🔴 Direct Invoke bypasses Langchain template parsing errors
        response = llm.invoke(messages)
        content = response.content.strip()
        
        # Parse JSON for specific features
        if feature_type in ["flashcards", "predictor", "roast", "judge"]:
            clean_json_str = content.replace("```json", "").replace("```", "").strip()
            return {"status": "success", "data": json.loads(clean_json_str)}
        else:
            return {"status": "success", "data": content}

    except Exception as e:
        logger.error(f"Gen-Z Engine Error: {str(e)}")
        return {"status": "error", "message": str(e)}


def create_agent_messages(query: str, chat_history: list = [], context: str = ""):
    
    # 🔴 System Prompt আপডেট করা হলো যাতে সে Context ফলো করে
    system_prompt = f"""You are GSTU AI, an advanced academic assistant for the students of Gopalganj Science and Technology University (GSTU).
    
    CRITICAL INSTRUCTIONS:
    1. Base your answers strictly on the provided 'KNOWLEDGE BASE CONTEXT' below.
    2. If the context contains the answer, explain it professionally.
    3. If the context is empty or lacks the answer, use your general knowledge but admit that it's not from the official GSTU database.
    
    ====================
    KNOWLEDGE BASE CONTEXT:
    {context}
    ====================
    """
    
    messages = [SystemMessage(content=system_prompt)]
    
    for msg in chat_history[-5:]:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant" or role == "ai":
            messages.append(AIMessage(content=content))
            
    messages.append(HumanMessage(content=query))
    
    return messages


# ==========================================================
# 6. THE VERIFIER ENGINE (ZERO HALLUCINATION)
# ==========================================================
def create_verifier_messages(query: str, context: str, draft_answer: str, is_bengali: bool):
    """
    মেইন এআই এর দেওয়া ড্রাফট অ্যানসারকে ফ্যাক্ট-চেক করে ফাইনাল প্রম্পট তৈরি করে।
    """
    try:
        lang_instruction = "MUST output in flawless BENGALI SCRIPT." if is_bengali else "MUST output in highly formal ENGLISH."
        
        system_prompt = f"""You are the 'Elite Verifier & Fact-Checker Agent' for GSTU IR Department.
Your job is to strictly review a 'Draft Answer' against the 'Provided Context' before it reaches the student.

CRITICAL RULES:
1. FACT-CHECK: If the Draft Answer contains ANY information, dates, or claims NOT present in the Context, completely REMOVE them. Do not hallucinate.
2. If the context says "No relevant data found", ensure the answer clearly admits lack of information instead of making things up.
3. REFINEMENT: Improve the academic tone. Use bullet points and bold text for readability.
4. {lang_instruction}
5. OUTPUT: Output ONLY the final verified answer. Do NOT add notes like "I have verified..." or "The draft is good". Just provide the final, clean text.
"""
        
        human_prompt = f"USER QUERY: {query}\n\nPROVIDED CONTEXT (Truth):\n{context}\n\nAI DRAFT ANSWER (Needs Review):\n{draft_answer}\n\nProvide the FINAL verified answer now:"
        
        # Return the message array so the main app can stream it directly
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]
        
        return {"status": "success", "messages": messages}
        
    except Exception as e:
        logger.error(f"Verifier Engine Error: {str(e)}")
        return {"status": "error", "message": str(e)}
    

# ==========================================================
# 7. OMNICHANNEL CS AGENT (PHASE 3 - SUPPORT & ESCALATION)
# ==========================================================
def process_customer_service(query: str, user_id: str):
    """
    Handles administrative queries, app issues, and automated escalation to human admins.
    """
    try:
        llm = get_specialist_llm()
        
        system_prompt = """You are the official 'Customer Support & Admin Agent' for GSTU IR Department.
        Your job is to handle administrative queries, fee issues, app complaints, or routine questions.
        
        RULES:
        1. If it's a general question (e.g., "What are the fees?", "How to use the app?", "Who is the developer?"), provide a polite, helpful answer.
        2. ESCALATION TRIGGER: If it's a specific payment failure, a bug, a personal complaint, or something requiring human admin intervention (e.g., "My payment of 500 tk failed", "Change my email", "I am facing an error"), you MUST escalate it.
        3. Respond in the same language as the user input (Bengali or English).
        
        Output EXACTLY in this JSON format without markdown ticks:
        {
            "status": "answered" OR "escalated",
            "response": "Your helpful answer OR a polite message saying a support ticket has been created for the Admin.",
            "escalation_category": "Payment/Technical/Academic/None"
        }"""
        
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", f"Student Query: {query}")
        ])
        
        chain = prompt_template | llm
        res = chain.invoke({})
        
        clean_json_str = res.content.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_json_str)
        
        # 🔴 ESCALATION PIPELINE: Save ticket to database if escalated
        if data.get("status") == "escalated":
            try:
                from auth_logic import supabase
                supabase.table("support_tickets").insert({
                    "user_id": user_id,
                    "query": query,
                    "category": data.get("escalation_category", "General"),
                    "ticket_status": "open",
                    "created_at": datetime.datetime.now().isoformat()
                }).execute()
            except Exception as db_err:
                logger.error(f"Failed to create support ticket: {db_err}")
                
        return {"status": "success", "data": data}
        
    except Exception as e:
        logger.error(f"CS Agent Error: {str(e)}")
        return {"status": "error", "message": str(e)}


def get_llm_engine(model_name: str):
    """
    ফ্রন্টএন্ড থেকে পাঠানো মডেলের নাম অনুযায়ী সঠিক LangChain ইঞ্জিন লোড করবে।
    """
    model_name_lower = model_name.lower()
    
    if "llama" in model_name_lower or "mixtral" in model_name_lower:
        return ChatGroq(
            api_key=os.getenv("GROQ_API_KEY"),
            model_name=model_name,
            temperature=0.3,
            max_tokens=2048
        )
    elif "gemini" in model_name_lower:
        return ChatGoogleGenerativeAI(
            google_api_key=os.getenv("GEMINI_API_KEY"),
            model=model_name,
            temperature=0.3
        )
    else:
        # Default Fallback (যদি কোনো মডেল ম্যাচ না করে)
        return ChatGroq(
            api_key=os.getenv("GROQ_API_KEY"),
            model_name="meta-llama/llama-4-scout-17b-16e-instruct",
            temperature=0.3
        )