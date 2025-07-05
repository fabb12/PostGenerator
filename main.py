"""
LinkedIn Post Generator - Main Streamlit Application
Professional tool for generating and managing LinkedIn content
"""

import streamlit as st
from pathlib import Path
import sys
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Dict, List, Optional

# Add src to path for imports
sys.path.append(str(Path(__file__).parent))

# Local imports
from config import config
from src.database import db, Post
from src.content_extractor import ContentExtractor, ExtractedContent
from src.post_generator import PostGenerator, PostTone, PostType
from utils.helpers import (
    format_datetime, 
    get_time_ago, 
    validate_linkedin_url,
    estimate_read_time
)

# Page configuration
st.set_page_config(
    page_title=config.APP_NAME,
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/yourusername/linkedin-post-generator',
        'Report a bug': 'https://github.com/yourusername/linkedin-post-generator/issues',
        'About': f"{config.APP_NAME} - AI-powered LinkedIn content generation"
    }
)

# Custom CSS
st.markdown("""
<style>
    /* Main container */
    .main {
        padding: 2rem;
    }
    
    /* Headers */
    h1 {
        color: #0A66C2;
        font-weight: 700;
        margin-bottom: 1.5rem;
    }
    
    h2 {
        color: #000000;
        font-weight: 600;
        margin-top: 2rem;
    }
    
    /* Metric cards */
    div[data-testid="metric-container"] {
        background-color: #F3F6F8;
        border: 1px solid #E0E0E0;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    /* Success messages */
    .success-box {
        background-color: #D4EDDA;
        border: 1px solid #C3E6CB;
        color: #155724;
        padding: 1rem;
        border-radius: 4px;
        margin: 1rem 0;
    }
    
    /* LinkedIn style button */
    .stButton > button {
        background-color: #0A66C2;
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: 600;
        border-radius: 24px;
        transition: background-color 0.3s;
    }
    
    .stButton > button:hover {
        background-color: #004182;
    }
    
    /* Post preview */
    .post-preview {
        background-color: #FFFFFF;
        border: 1px solid #E0E0E0;
        border-radius: 8px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background-color: #F8F9FA;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if 'current_post' not in st.session_state:
        st.session_state.current_post = None
    
    if 'generated_posts' not in st.session_state:
        st.session_state.generated_posts = []
    
    if 'selected_sources' not in st.session_state:
        st.session_state.selected_sources = []
    
    if 'show_success' not in st.session_state:
        st.session_state.show_success = False


def validate_configuration():
    """Validate app configuration and show warnings"""
    errors = config.validate()
    
    if errors:
        st.warning("⚠️ Configuration Issues Detected")
        for error in errors:
            st.error(f"• {error}")
        
        with st.expander("📚 Configuration Help"):
            st.markdown("""
            **To fix configuration issues:**
            
            1. Copy `.env.example` to `.env`
            2. Add your API keys:
               - Get Claude API key from [Anthropic Console](https://console.anthropic.com/)
               - Get OpenAI API key from [OpenAI Platform](https://platform.openai.com/)
            3. Add LinkedIn credentials (email/password)
            4. Restart the application
            
            **Need help?** Check the [documentation](https://github.com/yourusername/linkedin-post-generator)
            """)
        
        return False
    
    return True


def render_sidebar():
    """Render sidebar with navigation and stats"""
    with st.sidebar:
        # Logo/Header
        st.markdown("# 🚀 LinkedIn Post Generator")
        st.markdown("---")

        # Navigation info
        st.info("""
        **Navigation:**
        - 📝 **Create Post**: Generate new content
        - 📅 **Schedule**: Manage scheduled posts  
        - 📊 **History**: View past posts
        """)

        # Quick Stats
        st.markdown("### 📈 Quick Stats")

        try:
            # Get stats from database
            total_posts = len(db.get_posts())
            published = len(db.get_posts(status='published'))
            scheduled = len(db.get_posts(status='scheduled'))
            drafts = len(db.get_posts(status='draft'))

            # Source stats
            total_sources = len(db.get_content_sources())

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Posts", total_posts)
                st.metric("Published", published)
                st.metric("Sources Saved", total_sources)
            with col2:
                st.metric("Scheduled", scheduled)
                st.metric("Drafts", drafts)
                st.metric("Recent Sources", len(db.get_recent_sources(limit=10)))
        except Exception as e:
            st.error(f"Error loading stats: {str(e)}")

        # Configuration Status
        st.markdown("---")
        st.markdown("### ⚙️ Configuration")

        # Show available AI models
        ai_models = []
        if config.ANTHROPIC_API_KEY:
            ai_models.append("✅ Claude")
        if config.OPENAI_API_KEY:
            ai_models.append("✅ OpenAI")
        if config.GOOGLE_API_KEY:
            ai_models.append("✅ Gemini 2.0 Pro")

        if ai_models:
            for model in ai_models:
                st.success(model)
        else:
            st.error("❌ No AI models configured")

        # LinkedIn status
        if config.LINKEDIN_EMAIL:
            st.success("✅ LinkedIn configured")
        else:
            st.warning("⚠️ LinkedIn not configured")

        # Footer
        st.markdown("---")
        st.caption(f"v1.0.0 | {config.ENVIRONMENT.title()}")


def render_hero_section():
    """Render hero section on homepage"""
    col1, col2, col3 = st.columns([2, 3, 2])
    
    with col2:
        st.markdown("""
        <div style='text-align: center; padding: 2rem 0;'>
            <h1 style='font-size: 3rem; margin-bottom: 1rem;'>
                🚀 LinkedIn Post Generator
            </h1>
            <p style='font-size: 1.2rem; color: #666; margin-bottom: 2rem;'>
                Create engaging LinkedIn content with AI in seconds
            </p>
        </div>
        """, unsafe_allow_html=True)


def render_recent_posts():
    """Render recent posts section"""
    st.markdown("## 📑 Recent Posts")
    
    recent_posts = db.get_posts(limit=5)
    
    if not recent_posts:
        st.info("No posts yet. Create your first post to get started!")
        return
    
    for post in recent_posts:
        with st.expander(
            f"{post.post_type.title()} - {format_datetime(post.created_at)}",
            expanded=False
        ):
            # Post content
            st.markdown(f"**Content:**")
            st.text(post.content[:200] + "..." if len(post.content) > 200 else post.content)
            
            # Metadata
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Status", post.status.title())
            with col2:
                st.metric("Tone", post.tone.title())
            with col3:
                st.metric("Model", post.model_used or "N/A")
            with col4:
                if post.engagement_rate:
                    st.metric("Engagement", f"{post.engagement_rate:.1f}%")
            
            # Actions
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("📋 Copy", key=f"copy_{post.id}"):
                    st.code(post.content)
                    st.success("Content ready to copy!")
            
            with col2:
                if post.status == 'draft':
                    if st.button("📅 Schedule", key=f"schedule_{post.id}"):
                        st.session_state.current_post = post
                        st.info("Go to Schedule page to set time")
            
            with col3:
                if post.linkedin_post_url:
                    st.markdown(f"[🔗 View on LinkedIn]({post.linkedin_post_url})")


def render_analytics_preview():
    """Render analytics preview"""
    st.markdown("## 📊 Analytics Overview")
    
    # Get published posts for analytics
    published_posts = db.get_posts(status='published', limit=30)
    
    if not published_posts:
        st.info("No published posts yet. Analytics will appear here once you start publishing.")
        return
    
    # Create sample data for visualization
    dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
    engagement_data = pd.DataFrame({
        'Date': dates,
        'Engagement Rate': [2.5 + i * 0.1 + (i % 7) * 0.5 for i in range(30)]
    })
    
    # Engagement trend chart
    fig = px.line(
        engagement_data,
        x='Date',
        y='Engagement Rate',
        title='Engagement Rate Trend (30 days)',
        line_shape='spline'
    )
    
    fig.update_layout(
        showlegend=False,
        height=300,
        margin=dict(l=0, r=0, t=30, b=0)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Best performing posts
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🏆 Top Performing Posts")
        top_posts = sorted(
            [p for p in published_posts if p.engagement_rate], 
            key=lambda x: x.engagement_rate, 
            reverse=True
        )[:3]
        
        for i, post in enumerate(top_posts, 1):
            st.markdown(f"**{i}.** {post.content[:50]}... ({post.engagement_rate:.1f}% engagement)")
    
    with col2:
        st.markdown("### 📈 Post Type Performance")
        # Mock data for post type performance
        post_types = ['Informative', 'News Sharing', 'Thought Leadership', 'Tips & Tricks']
        performance = [4.2, 3.8, 5.1, 4.5]
        
        fig = go.Figure(data=[
            go.Bar(x=post_types, y=performance, marker_color='#0A66C2')
        ])
        
        fig.update_layout(
            showlegend=False,
            height=250,
            margin=dict(l=0, r=0, t=0, b=0),
            yaxis_title="Avg Engagement %"
        )
        
        st.plotly_chart(fig, use_container_width=True)


def render_quick_actions():
    """Render quick action buttons"""
    st.markdown("## 🎯 Quick Actions")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📝 Create New Post", use_container_width=True):
            st.switch_page("pages/1_📝_Create_Post.py")
    
    with col2:
        if st.button("📅 Schedule Post", use_container_width=True):
            st.switch_page("pages/2_📅_Schedule.py")
    
    with col3:
        if st.button("📊 View Analytics", use_container_width=True):
            st.switch_page("pages/3_📊_History.py")
    
    with col4:
        if st.button("⚙️ Settings", use_container_width=True):
            st.info("Settings page coming soon!")


def main():
    """Main application entry point"""
    # Initialize session state
    init_session_state()
    
    # Render sidebar
    render_sidebar()
    
    # Check configuration
    if not validate_configuration():
        st.stop()
    
    # Main content area
    render_hero_section()
    
    # Success message if any
    if st.session_state.show_success:
        st.success(st.session_state.show_success)
        st.session_state.show_success = False
    
    # Quick actions
    render_quick_actions()
    
    # Two column layout for content
    col1, col2 = st.columns([3, 2])
    
    with col1:
        render_recent_posts()
    
    with col2:
        render_analytics_preview()
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666; padding: 2rem 0;'>
            <p style='font-size: 0.9rem;'>
                <a href='https://github.com/yourusername/linkedin-post-generator' style='color: #0A66C2;'>GitHub</a> | 
                <a href='#' style='color: #0A66C2;'>Documentation</a> | 
                <a href='#' style='color: #0A66C2;'>Support</a>
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
