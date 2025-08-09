# pages/4_⚙️_Settings.py

"""
Settings Page
Manage LinkedIn accounts, view app configuration, and test connections.
"""

import streamlit as st
from pathlib import Path
import sys
import time

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config import config
from src.database import db, LinkedInAccount
from src.linkedin_connector import LinkedInPublisher  # To test connections
from src.post_generator import get_model_info
from src.encryption import decrypt_password

st.set_page_config(
    page_title="Settings - LinkedIn Generator",
    page_icon="⚙️",
    layout="centered"
)

st.title("⚙️ App Settings & Status")

# --- Function to test a specific account ---
def test_account_connection(account: LinkedInAccount):
    """Tests connection for a single LinkedIn account."""
    with st.spinner(f"Testing connection for {account.email}..."):
        try:
            password = decrypt_password(account.encrypted_password)
            publisher = LinkedInPublisher(email=account.email, password=password)

            if publisher.authenticate():
                st.success(f"✅ Connection successful for {account.email}!")
            else:
                st.error(f"❌ Authentication failed for {account.email}. Check credentials.")
        except Exception as e:
            st.error(f"❌ An error occurred while testing {account.email}: {e}")

# --- LinkedIn Account Management ---
with st.container(border=True):
    st.subheader("🔗 LinkedIn Account Management")

    # --- Add New Account Form ---
    with st.expander("➕ Add New LinkedIn Account"):
        with st.form("new_account_form", clear_on_submit=True):
            new_email = st.text_input("LinkedIn Email")
            new_password = st.text_input("LinkedIn Password", type="password")
            submitted = st.form_submit_button("Add Account")

            if submitted:
                if new_email and new_password:
                    try:
                        db.add_linkedin_account(email=new_email, password=new_password)
                        st.success(f"Account for {new_email} added successfully!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error adding account: {e}")
                else:
                    st.warning("Please provide both email and password.")

    st.divider()

    # --- Display Existing Accounts ---
    accounts = db.get_linkedin_accounts()
    if not accounts:
        st.info("No LinkedIn accounts configured. Add one above to get started.")
    else:
        st.markdown("##### Configured Accounts")
        active_account = next((acc for acc in accounts if acc.is_active), None)

        for acc in accounts:
            is_active = " (Active)" if acc.is_active else ""
            st.markdown(f"**Email:** `{acc.email}`{is_active}")

            col1, col2, col3 = st.columns(3)

            # Set Active Button
            if col1.button("Set Active", key=f"activate_{acc.id}", disabled=acc.is_active, use_container_width=True):
                db.set_active_linkedin_account(acc.id)
                st.success(f"{acc.email} is now the active account.")
                time.sleep(1)
                st.rerun()

            # Test Connection Button
            if col2.button("Test Connection", key=f"test_{acc.id}", use_container_width=True):
                test_account_connection(acc)

            # Delete Button
            if col3.button("🗑️ Delete", key=f"delete_{acc.id}", use_container_width=True):
                db.delete_linkedin_account(acc.id)
                st.warning(f"Account {acc.email} deleted.")
                time.sleep(1)
                st.rerun()
            st.markdown("---")

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