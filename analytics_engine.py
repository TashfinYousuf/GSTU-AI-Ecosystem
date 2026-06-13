import logging
import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta, timezone
from memory_db import supabase  # memory_db থেকে ডাটাবেস কানেকশন ইমপোর্ট করা হলো

logger = logging.getLogger(__name__)


# =====================================================================
# 📚 1. REAL-TIME STUDY LOGGER
# =====================================================================
def render_study_logger(user_id: str):
    st.markdown("### 📚 Daily Study Logger")
    
    topic = st.text_input("Topic studied (Optional):", placeholder="e.g., Migration Theories")
    hours = st.slider("How many hours did you study today?", 0.0, 12.0, 2.0, key="study_hours")
    mood = st.select_slider("Mood/Focus level:", options=[1, 2, 3, 4, 5], value=3, help="1 = Poor, 5 = Deep Focus")
    
    if st.button("Log Progress 🚀", key="log_progress_btn", use_container_width=True, type="primary"):
        try:
            # Assuming 'supabase' is globally available or imported in this file
            final_topic = topic if topic else "General Studies"
            
            supabase.table("study_sessions").insert({
                "user_id": user_id,
                "topic": final_topic,
                "hours": hours,
                "mood": mood,
                "timestamp": datetime.datetime.now().isoformat()
            }).execute()
            
            st.success(f"✅ {hours} Hours logged securely to your account.")
            time.sleep(0.6)
            st.rerun()
        except Exception as e:
            st.error(f"⚠️ Database Error: {e}")

# =====================================================================
# 📊 2. REAL-TIME ANALYTICS DASHBOARD
# =====================================================================
def render_analytics_dashboard(user_id: str):
    st.markdown("### 📊 Live Academic Analytics")
    
    try:
        # 🔴 Fetch REAL data directly from Supabase
        study_res = supabase.table("study_sessions").select("topic, hours, mood, timestamp").eq("user_id", user_id).execute()
        chat_res = supabase.table("ai_training_logs").select("id").eq("user_id", user_id).execute()
        
        study_data = study_res.data if study_res else []
        total_interactions = len(chat_res.data) if chat_res and chat_res.data else 0
        
        if not study_data:
            st.info("No study data available yet. Start logging your sessions to see your progress chart!")
            return

        # 🔴 Process Data using Pandas
        df = pd.DataFrame(study_data)
        df['Date'] = pd.to_datetime(df['timestamp']).dt.date
        df['Focus Score (%)'] = (df['mood'] / 5.0) * 100  # Convert 1-5 scale to percentage
        
        # Calculate Metrics
        current_focus = int(df['Focus Score (%)'].mean())
        total_hours = round(df['hours'].sum(), 1)
        
        # Count unique topics where mood was 4 or 5 (Mastered)
        strong_topics_count = df[df['mood'] >= 4]['topic'].nunique() if len(df) > 0 else 0

        # 🔴 Render True Metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Focus Score", f"{current_focus}%", "Based on your logs")
        col2.metric("Total Hours", f"{total_hours} hrs", "Lifetime")
        col3.metric("Topics Mastered", f"{strong_topics_count}", "High Focus Topics")
        
        # 🔴 Render True Line Chart (Grouped by Date)
        st.markdown("#### 📈 Focus Performance Trend")
        
        # Group by date to get daily average focus score
        daily_focus = df.groupby('Date')['Focus Score (%)'].mean().reset_index()
        daily_focus.set_index('Date', inplace=True)
        
        # Streamlit automatically plots the index on X-axis and columns on Y-axis
        st.line_chart(daily_focus, use_container_width=True, color="#10a37f")

    except Exception as e:
        st.error(f"⚠️ Failed to load real-time analytics. System Error: {e}")
    
# ==========================================
# 1. PRODUCTIVITY & GROWTH CALCULATION
# ==========================================
def calculate_productivity_trend(user_id: str, course_code: str = None):
    """
    গত ৭ দিনের ডেটার সাথে তার আগের ৭ দিনের ডেটার তুলনা করে 
    Productivity Boost Rate (%) ক্যালকুলেট করবে।
    """
    try:
        # বর্তমান সময় থেকে গত ৭ দিন এবং তার আগের ৭ দিনের টাইমলাইন
        now = datetime.now(timezone.utc)
        seven_days_ago = now - timedelta(days=7)
        fourteen_days_ago = now - timedelta(days=14)

        # Query builder
        query = supabase.table("academic_analytics").select("quiz_score, recorded_at").eq("user_id", user_id)
        if course_code:
            query = query.eq("course_code", course_code)
            
        res = query.execute()
        
        if not res.data:
            return {"status": "insufficient_data", "growth_percent": 0.0, "message": "Keep studying to unlock analytics!"}

        # ডেটা ফিল্টার করা
        this_week_scores = [d['quiz_score'] for d in res.data if datetime.fromisoformat(d['recorded_at'].replace('Z', '+00:00')).replace(tzinfo=timezone.utc) >= seven_days_ago]
        last_week_scores = [d['quiz_score'] for d in res.data if fourteen_days_ago <= datetime.fromisoformat(d['recorded_at'].replace('Z', '+00:00')).replace(tzinfo=timezone.utc) < seven_days_ago]

        # গড় স্কোর বের করা
        avg_this_week = sum(this_week_scores) / len(this_week_scores) if this_week_scores else 0
        avg_last_week = sum(last_week_scores) / len(last_week_scores) if last_week_scores else 0

        # % Growth Formula: ((New - Old) / Old) * 100
        if avg_last_week > 0:
            growth_percent = ((avg_this_week - avg_last_week) / avg_last_week) * 100
        else:
            growth_percent = 100.0 if avg_this_week > 0 else 0.0

        return {
            "status": "success",
            "growth_percent": round(growth_percent, 2),
            "trend": "Upward 📈" if growth_percent > 0 else "Downward 📉" if growth_percent < 0 else "Neutral ➖"
        }

    except Exception as e:
        logger.error(f"Analytics Calculation Error: {e}")
        return {"status": "error", "growth_percent": 0.0}


# ==========================================
# 2. WEAKNESS SEVERITY ANALYSIS
# ==========================================
def analyze_weakness_severity(user_id: str):
    """
    memory_db থেকে ইউজারের উইকনেস গ্রাফ এনে প্রায়োরিটি লিস্ট তৈরি করবে।
    Study Planner Agent এই লিস্ট দেখেই রুটিন বানাবে।
    """
    try:
        res = supabase.table("user_profiles").select("academic_weaknesses").eq("id", user_id).execute()
        
        if not res.data or not res.data[0].get("academic_weaknesses"):
            return {"status": "no_weakness", "critical_areas": []}
            
        weaknesses = res.data[0].get("academic_weaknesses", {})
        
        # 'Weak' ট্যাগ থাকা সাবজেক্টগুলো আলাদা করা
        critical_areas = [course for course, status in weaknesses.items() if str(status).lower() == 'weak']
        mastered_areas = [course for course, status in weaknesses.items() if str(status).lower() == 'mastered']
        
        return {
            "critical_areas": critical_areas,     # এগুলোতে বেশি ফোকাস করতে হবে
            "mastered_areas": mastered_areas,     # এগুলো শুধু রিভিশন দিলেই হবে
            "total_tracked_topics": len(weaknesses)
        }
        
    except Exception as e:
        logger.error(f"Weakness Analysis Error: {e}")
        return {"critical_areas": []}


# ==========================================
# 3. STUDENT REPORT CARD GENERATOR
# ==========================================
def generate_progress_report(user_id: str):
    """
    স্টুডেন্টের সম্পূর্ণ প্রোগ্রেস সামারি এক জায়গায় করে UI বা Agent-কে পাঠাবে।
    """
    growth_data = calculate_productivity_trend(user_id)
    weakness_data = analyze_weakness_severity(user_id)
    
    report = {
        "user_id": user_id,
        "weekly_growth": growth_data.get("growth_percent", 0.0),
        "performance_trend": growth_data.get("trend", "Neutral ➖"),
        "focus_needed_on": weakness_data.get("critical_areas", []),
        "strong_areas": weakness_data.get("mastered_areas", []),
        "ai_insight": ""
    }
    
    # AI Insight Logic
    if report["weekly_growth"] > 0 and not report["focus_needed_on"]:
        report["ai_insight"] = "🎉 Excellent progress! You are dominating your syllabus. Keep it up!"
    elif report["weekly_growth"] > 0 and report["focus_needed_on"]:
        report["ai_insight"] = f"📈 You are growing, but you still need to focus heavily on: {', '.join(report['focus_needed_on'])}."
    elif report["weekly_growth"] <= 0 and report["focus_needed_on"]:
        report["ai_insight"] = "⚠️ Warning: Productivity is down. We need to create an aggressive rescue plan for your weak subjects."
        
    return report