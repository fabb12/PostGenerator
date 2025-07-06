# pages/2_🚀_Schedule_&_Automation.py

"""
Unified page for Scheduling, Automation, and Publishing.
"""

import streamlit as st
import pandas as pd
import asyncio
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config import config
from src.database import db
from src.linkedin_client import LinkedInScheduler
from src.automation_manager import AutomationManager
from utils.helpers import format_datetime, validate_url

st.set_page_config(
    page_title="Schedule & Automation - LinkedIn Generator",
    page_icon="🚀",
    layout="wide"
)

st.title("🚀 Schedule & Automation")
st.markdown("Manage your content pipeline, from automated generation to final publishing.")

# --- TABS FOR DIFFERENT ACTIONS ---
tab1, tab2, tab3 = st.tabs(["▶️ Publishing Queue", "⚙️ Automation Settings", "📊 Scheduled Posts"])

# --- TAB 1: Publishing Queue ---
with tab1:
    st.header("▶️ Publishing Queue")
    st.markdown(
        "Posts that are scheduled and ready to be published will appear here. Click the button to process the queue.")

    posts_to_publish = db.get_posts_to_publish()

    if not posts_to_publish:
        st.info("The publishing queue is empty. No posts are currently due.")
    else:
        st.warning(f"**{len(posts_to_publish)} post(s)** are ready to be published now!")
        for post in posts_to_publish:
            st.markdown(f"- **Post ID {post.id}**: Scheduled for {format_datetime(post.scheduled_for)}")

    if st.button("🚀 Process Publishing Queue Now", type="primary", use_container_width=True,
                 disabled=not posts_to_publish):
        with st.spinner("Connecting to LinkedIn and publishing posts..."):
            scheduler = LinkedInScheduler()
            # Run async function in Streamlit
            results = asyncio.run(scheduler.process_scheduled_posts())

            if not results:
                st.info("No posts were published.")
            else:
                st.success("Publishing process finished!")
                for result in results:
                    if result.get('status') == 'published':
                        st.success(f"✅ Published post ID {result.get('post_id')}.")
                    else:
                        st.error(f"❌ Failed post ID {result.get('post_id')}: {result.get('error')}")
                st.rerun()

# --- TAB 2: Automation Settings ---
with tab2:
    st.header("⚙️ Automation Settings")
    st.markdown("Manage sources for automatic post generation.")

    # Add new source
    with st.form("add_source_form"):
        new_source_url = st.text_input("Add a new URL source (e.g., a blog or news feed)",
                                       placeholder="https://example.com/blog")
        submitted = st.form_submit_button("➕ Add Source")
        if submitted and validate_url(new_source_url):
            if db.add_automation_source(url=new_source_url):
                st.success(f"Source added: {new_source_url}")
            else:
                st.error("Source might already exist.")
        elif submitted:
            st.error("Please enter a valid URL.")

    st.subheader("📋 Active Automation Sources")
    sources = db.get_active_automation_sources()
    if not sources:
        st.info("No automation sources found. Add one above to get started.")
    else:
        for source in sources:
            col1, col2, col3 = st.columns([4, 2, 1])
            col1.markdown(f"[{source.url}]({source.url})")
            col2.caption(
                f"Last checked: {format_datetime(source.last_checked_at) if source.last_checked_at else 'Never'}")
            if col3.button("🗑️", key=f"del_{source.id}", help="Delete source"):
                db.delete_automation_source(source.id)
                st.rerun()

    st.subheader("⚡ Run Post Generation")
    st.markdown("Click this button to fetch content from your sources and automatically create and schedule new posts.")
    force_run = st.checkbox("Force run on all sources (ignores 24h check interval)")
    if st.button("🤖 Generate and Schedule Posts", use_container_width=True):
        with st.spinner("Running automation... This may take a few minutes."):
            manager = AutomationManager()
            summary = manager.run(force_run=force_run)
            st.success("Automation run complete!")
            st.metric("New Posts Scheduled", summary['scheduled'])
            with st.expander("View Log"):
                st.json(summary)

# --- TAB 3: Scheduled Posts List ---
with tab3:
    st.header("📊 All Scheduled & Past Posts")
    st.markdown("A history of all posts that are scheduled, published, or have failed.")

    scheduled_data = db.get_scheduled_posts()

    if not scheduled_data:
        st.info("No posts have been scheduled yet.")
    else:
        post_list = []
        for item in scheduled_data:
            post_list.append({
                "Post ID": item['post']['id'],
                "Status": item['scheduled']['status'].title(),
                "Content": item['post']['content'][:100] + "...",
                "Scheduled For": format_datetime(datetime.fromisoformat(item['scheduled']['scheduled_time'])),
                "Published At": format_datetime(datetime.fromisoformat(item['scheduled']['published_at'])) if
                item['scheduled']['published_at'] else "N/A"
            })

        df = pd.DataFrame(post_list)
        st.dataframe(df, use_container_width=True)