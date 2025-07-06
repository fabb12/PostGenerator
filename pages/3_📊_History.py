# pages/3_📊_History.py

"""
Simplified Analytics & History Page
Provides a clean dashboard with key metrics and a filterable post history.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config import config
from src.database import db, Post
from utils.helpers import format_datetime, export_posts_to_csv, get_post_performance_category

st.set_page_config(
    page_title="Analytics & History - LinkedIn Generator",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Analytics & History")
st.markdown("Monitor your content performance and review past posts.")

# --- 1. Key Performance Indicators (KPIs) ---
st.header("📈 Key Metrics")

# Get all published posts for analytics
all_published_posts = db.get_posts(status='published', limit=1000)

if not all_published_posts:
    st.info("No published posts yet. Analytics will appear here once you start publishing.")
else:
    total_views = sum(p.views for p in all_published_posts if p.views)
    total_likes = sum(p.likes for p in all_published_posts if p.likes)
    total_comments = sum(p.comments for p in all_published_posts if p.comments)
    total_shares = sum(p.shares for p in all_published_posts if p.shares)

    total_interactions = total_likes + total_comments + total_shares
    avg_engagement_rate = (total_interactions / total_views * 100) if total_views else 0.0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Published Posts", len(all_published_posts))
    col2.metric("Total Views", f"{total_views:,}")
    col3.metric("Total Interactions", f"{total_interactions:,}")
    col4.metric("Avg. Engagement Rate", f"{avg_engagement_rate:.2f}%")

    # --- 2. Analytics Charts ---
    st.header("💡 Performance Insights")

    # Prepare data for charts
    posts_df_data = [{
        'published_at': p.published_at,
        'post_type': p.post_type.replace('_', ' ').title(),
        'engagement_rate': p.engagement_rate or 0
    } for p in all_published_posts if p.published_at]

    posts_df = pd.DataFrame(posts_df_data)

    if not posts_df.empty:
        posts_df['published_at'] = pd.to_datetime(posts_df['published_at'])

        col1, col2 = st.columns(2)

        with col1:
            # Engagement Trend Chart
            st.subheader("Engagement Trend")
            daily_engagement = posts_df.groupby(posts_df['published_at'].dt.date)[
                'engagement_rate'].mean().reset_index()
            fig_trend = px.line(
                daily_engagement,
                x='published_at',
                y='engagement_rate',
                title="Daily Average Engagement Rate",
                labels={'published_at': 'Date', 'engagement_rate': 'Avg. Engagement Rate (%)'}
            )
            fig_trend.update_layout(height=350)
            st.plotly_chart(fig_trend, use_container_width=True)

        with col2:
            # Post Type Performance Chart
            st.subheader("Performance by Post Type")
            type_performance = posts_df.groupby('post_type')['engagement_rate'].mean().reset_index().sort_values(
                by='engagement_rate', ascending=False)
            fig_type = px.bar(
                type_performance,
                x='post_type',
                y='engagement_rate',
                title="Average Engagement Rate by Type",
                labels={'post_type': 'Post Type', 'engagement_rate': 'Avg. Engagement Rate (%)'},
                color='engagement_rate',
                color_continuous_scale='viridis'
            )
            fig_type.update_layout(height=350)
            st.plotly_chart(fig_type, use_container_width=True)

# --- 3. Post History List ---
st.header("📋 Post History")

# Get all posts (draft, scheduled, published, etc.)
all_posts = db.get_posts(limit=1000, order_by='created_at_desc')

if not all_posts:
    st.info("No posts have been created yet.")
else:
    # Filters
    col1, col2, col3 = st.columns(3)
    status_filter = col1.selectbox("Filter by Status", ['All'] + ['Published', 'Scheduled', 'Draft', 'Failed'], index=0)
    sort_by = col2.selectbox("Sort by", ['Newest First', 'Highest Engagement'], index=0)

    # Export Button
    csv_data = export_posts_to_csv(all_posts)
    col3.download_button(
        label="📥 Export All to CSV",
        data=csv_data,
        file_name=f"linkedin_posts_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True
    )

    # Filter and sort data
    filtered_posts = all_posts
    if status_filter != 'All':
        filtered_posts = [p for p in filtered_posts if p.status.lower() == status_filter.lower()]

    if sort_by == 'Highest Engagement':
        filtered_posts.sort(key=lambda p: p.engagement_rate or 0, reverse=True)

    # Display posts
    for post in filtered_posts:
        with st.container(border=True):
            col1, col2, col3 = st.columns([4, 1, 1])

            with col1:
                # Determine performance for published posts
                performance_emoji = ""
                if post.status == 'published':
                    performance = get_post_performance_category(post.engagement_rate or 0)
                    emojis = {'high': '🏆', 'medium': '👍', 'low': '⚪'}
                    performance_emoji = emojis.get(performance, '')

                st.markdown(f"**{performance_emoji} Post ID: {post.id}** ({post.post_type.replace('_', ' ').title()})")
                st.text_area(
                    "Content",
                    value=post.content,
                    height=100,
                    disabled=True,
                    key=f"content_{post.id}"
                )

            with col2:
                st.metric("Status", post.status.title())
                if post.status == 'published':
                    st.metric("Engagement", f"{post.engagement_rate or 0:.2f}%")
                elif post.status == 'scheduled' and post.scheduled_for:
                    st.markdown("**Scheduled For:**")
                    st.caption(format_datetime(post.scheduled_for))

            with col3:
                st.markdown("**Created:**")
                st.caption(format_datetime(post.created_at))
                if post.linkedin_post_url and post.linkedin_post_url != "manual_publish":
                    st.link_button("View on LinkedIn", post.linkedin_post_url)

                # Copy button
                if st.button("📋 Copy Text", key=f"copy_{post.id}"):
                    st.code(post.content)
                    st.success("Post content copied to clipboard!")