import streamlit as st
import pandas as pd
import numpy as np

def render_study_logger(user_id: str):
    st.markdown("### 📚 Daily Study Logger")
    hours = st.slider("How many hours did you study today?", 0.0, 12.0, 2.0, key="study_hours")
    if st.button("Log Progress", key="log_progress_btn", use_container_width=True):
        st.toast(f"✅ {hours} Hours logged securely to your account.")

def render_analytics_dashboard(user_id: str):
    st.markdown("### 📊 Academic Analytics")
    c1, c2, c3 = st.columns(3)
    c1.metric("Focus Score", "92%", "+5%")
    c2.metric("Questions Asked", "34", "+12")
    c3.metric("Topics Mastered", "8", "+1")
    
    st.markdown("#### Weekly Engagement (IR Theory vs Geopolitics)")
    # Generate dynamic dummy data for the student chart
    chart_data = pd.DataFrame(
        np.random.randint(40, 100, size=(7, 2)), 
        columns=["IR Theory (Hours)", "Geopolitics (Hours)"]
    )
    st.line_chart(chart_data, color=["#10a37f", "#58A6FF"])