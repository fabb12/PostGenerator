# pages/4_⚙️_Settings.py

"""
Settings Page
View app configuration and test connections.
"""

import streamlit as st
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config import config
from src.linkedin_client import check_linkedin_connection
from src.post_generator import get_model_info

st.set_page_config(
    page_title="Settings - LinkedIn Generator",
    page_icon="⚙️",
    layout="centered"
)

st.title("⚙️ App Settings & Status")

# --- LinkedIn Settings ---
with st.container(border=True):
    st.subheader("🔗 LinkedIn Connection")

    email = config.LINKEDIN_EMAIL
    if email:
        st.markdown(f"**Email Configured:** `{email}`")
    else:
        st.error("LinkedIn email not configured in `.env` file.")

    if st.button("Test LinkedIn Connection"):
        with st.spinner("Testing connection..."):
            status = check_linkedin_connection()
            if status.get('authenticated'):
                st.success("✅ Connection successful! Authenticated with LinkedIn.")
            else:
                st.error(f"❌ Connection failed: {status.get('error')}")

# --- AI Model Settings ---
with st.container(border=True):
    st.subheader("🤖 AI Model Status")

    model_info = get_model_info()

    if model_info['gemini']['available']:
        st.success(f"**Google Gemini:** Configured (Model: `{model_info['gemini']['model']}`)")
    else:
        st.warning(f"**Google Gemini:** Not configured. Add `GOOGLE_API_KEY` to `.env`.")

    if model_info['claude']['available']:
        st.success(f"**Anthropic Claude:** Configured (Model: `{model_info['claude']['model']}`)")
    else:
        st.warning(f"**Anthropic Claude:** Not configured. Add `ANTHROPIC_API_KEY` to `.env`.")

    if model_info['openai']['available']:
        st.success(f"**OpenAI GPT:** Configured (Model: `{model_info['openai']['model']}`)")
    else:
        st.warning(f"**OpenAI GPT:** Not configured. Add `OPENAI_API_KEY` to `.env`.")

# --- Automation Settings ---
with st.container(border=True):
    st.subheader("🚀 Automation Defaults")
    st.markdown("These values from your `.env` file are used for automated post generation.")

    col1, col2 = st.columns(2)
    col1.metric("Default Tone", config.AUTOMATION_DEFAULT_TONE.title())
    col2.metric("Default Post Type", config.AUTOMATION_DEFAULT_POST_TYPE.replace('_', ' ').title())

    st.markdown(f"**Scheduling Hours:** Posts will be scheduled for `{config.AUTOMATION_SCHEDULING_HOURS}`:00.")
    st.markdown(f"**Min Days Between Posts:** `{config.AUTOMATION_MIN_DAYS_BETWEEN_POSTS}` day(s).")