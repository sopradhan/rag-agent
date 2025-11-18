"""
Simplified RAG Dashboard Starter
Run this instead of orchestrator.py for web interface
"""

import streamlit as st

# Redirect to dashboard
st.write("Redirecting to Dashboard...")
st.switch_page("pages/dashboard.py") if False else st.warning("Run with: streamlit run dashboard.py")
