"""
Schedule Posts Page - Manage scheduled LinkedIn posts
Allows users to schedule posts, view scheduled posts, and manage timing
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
from pathlib import Path
import sys
import pytz
from typing import List, Dict, Optional
import asyncio

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Local imports
from config import config
from src.database import db, Post
from src.linkedin_client import LinkedInPublisher, LinkedInScheduler, check_linkedin_connection
from utils.helpers import format_datetime, get_time_ago, get_optimal_posting_times

# Page config
st.set_page_config(
    page_title="Schedule Posts - LinkedIn Generator",
    page_icon="📅",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    /* Schedule cards */
    .schedule-card {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    
    .schedule-card-urgent {
        border-left: 4px solid #dc3545;
    }
    
    .schedule-card-soon {
        border-left: 4px solid #ffc107;
    }
    
    .schedule-card-future {
        border-left: 4px solid #28a745;
    }
    
    /* Calendar styling */
    .calendar-container {
        background: white;
        border-radius: 8px;
        padding: 1rem;
    }
    
    /* Time slots */
    .time-slot {
        background: #e3f2fd;
        border: 1px solid #2196f3;
        border-radius: 4px;
        padding: 0.5rem;
        margin: 0.25rem;
        text-align: center;
        cursor: pointer;
    }
    
    .time-slot:hover {
        background: #bbdefb;
    }
    
    .time-slot.selected {
        background: #2196f3;
        color: white;
    }
    
    /* Status indicators */
    .status-pending { color: #ffc107; }
    .status-published { color: #28a745; }
    .status-failed { color: #dc3545; }
    .status-cancelled { color: #6c757d; }
</style>
""", unsafe_allow_html=True)


def init_page_state():
    """Initialize page-specific session state"""
    if 'selected_post_for_scheduling' not in st.session_state:
        st.session_state.selected_post_for_scheduling = None
    
    if 'schedule_date' not in st.session_state:
        st.session_state.schedule_date = datetime.now().date() + timedelta(days=1)
    
    if 'schedule_time' not in st.session_state:
        st.session_state.schedule_time = time(9, 0)
    
    if 'timezone' not in st.session_state:
        st.session_state.timezone = config.TIMEZONE


def render_header():
    """Render page header with LinkedIn status"""
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.title("📅 Schedule Posts")
        st.markdown("Plan and manage your LinkedIn posting schedule")
    
    with col2:
        # LinkedIn connection status
        connection_status = check_linkedin_connection()
        if connection_status['authenticated']:
            st.success("✅ LinkedIn Connected")
        else:
            st.error(f"❌ LinkedIn: {connection_status.get('error', 'Not connected')}")
    
    with col3:
        # Current time info
        tz = pytz.timezone(st.session_state.timezone)
        current_time = datetime.now(tz)
        st.info(f"🕐 {current_time.strftime('%H:%M')} {st.session_state.timezone}")


def render_schedule_new_post():
    """Render section for scheduling a new post"""
    st.markdown("## 📝 Schedule New Post")
    
    # Check if there's a post to schedule from session state
    if hasattr(st.session_state, 'post_to_schedule') and st.session_state.post_to_schedule:
        post_id = st.session_state.post_to_schedule
        post = db.get_post(post_id)
        if post:
            st.success(f"✅ Post ready for scheduling: {post.content[:50]}...")
            st.session_state.selected_post_for_scheduling = post
            del st.session_state.post_to_schedule
    
    # Post selection
    if not st.session_state.selected_post_for_scheduling:
        render_post_selection()
    else:
        render_scheduling_interface()


def render_post_selection():
    """Render interface for selecting a post to schedule"""
    # Get draft posts
    draft_posts = db.get_posts(status='draft', limit=20)
    
    if not draft_posts:
        st.info("No draft posts available. Create a post first to schedule it.")
        if st.button("📝 Create New Post"):
            st.switch_page("pages/1_📝_Create_Post.py")
        return
    
    st.markdown("### Select a post to schedule:")
    
    # Display posts for selection
    for post in draft_posts:
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.markdown(f"**{post.post_type.title()}** - {post.tone.title()}")
                preview = post.content[:100] + "..." if len(post.content) > 100 else post.content
                st.text(preview)
                st.caption(f"Created: {format_datetime(post.created_at)}")
            
            with col2:
                st.metric("Characters", len(post.content))
                if post.model_used:
                    st.caption(f"Model: {post.model_used.split('-')[0].upper()}")
            
            with col3:
                if st.button("📅 Schedule", key=f"schedule_post_{post.id}"):
                    st.session_state.selected_post_for_scheduling = post
                    st.rerun()
                
                if st.button("👁️ Preview", key=f"preview_post_{post.id}"):
                    st.session_state.preview_post = post


def render_scheduling_interface():
    """Render scheduling interface for selected post"""
    post = st.session_state.selected_post_for_scheduling
    
    st.markdown("### 📝 Post to Schedule")
    
    # Post preview
    with st.expander("👁️ Post Preview", expanded=True):
        st.text_area(
            "Content",
            value=post.content,
            height=200,
            disabled=True
        )
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Characters", len(post.content))
        with col2:
            st.metric("Type", post.post_type.title())
        with col3:
            st.metric("Tone", post.tone.title())
    
    st.markdown("### 🕐 Schedule Settings")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Date and time selection
        col_date, col_time = st.columns(2)
        
        with col_date:
            schedule_date = st.date_input(
                "Date",
                value=st.session_state.schedule_date,
                min_value=datetime.now().date(),
                max_value=datetime.now().date() + timedelta(days=365)
            )
        
        with col_time:
            schedule_time = st.time_input(
                "Time",
                value=st.session_state.schedule_time
            )
        
        # Timezone selection
        timezone = st.selectbox(
            "Timezone",
            options=[
                'Europe/Rome', 'Europe/London', 'Europe/Paris', 'Europe/Berlin',
                'America/New_York', 'America/Los_Angeles', 'America/Chicago',
                'Asia/Tokyo', 'Asia/Shanghai', 'Asia/Dubai'
            ],
            index=0,
            help="Select your timezone for scheduling"
        )
        
        # Combine date and time
        schedule_datetime = datetime.combine(schedule_date, schedule_time)
        tz = pytz.timezone(timezone)
        scheduled_time = tz.localize(schedule_datetime)
        
        # Show converted time
        st.info(f"⏰ Scheduled for: {scheduled_time.strftime('%Y-%m-%d %H:%M %Z')}")
        
        # Show time until posting
        time_until = scheduled_time - datetime.now(tz)
        if time_until.total_seconds() > 0:
            days = time_until.days
            hours, remainder = divmod(time_until.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            
            if days > 0:
                time_str = f"{days} days, {hours} hours, {minutes} minutes"
            elif hours > 0:
                time_str = f"{hours} hours, {minutes} minutes"
            else:
                time_str = f"{minutes} minutes"
            
            st.success(f"🕐 Will post in: {time_str}")
        else:
            st.error("⚠️ Scheduled time is in the past!")
    
    with col2:
        # Optimal posting times
        st.markdown("### 💡 Suggested Times")
        optimal_times = get_optimal_posting_times()
        
        st.markdown("**Best times to post:**")
        for time_slot in optimal_times:
            if st.button(f"🕐 {time_slot}", key=f"optimal_{time_slot}"):
                hour, minute = map(int, time_slot.split(':'))
                st.session_state.schedule_time = time(hour, minute)
                st.rerun()
        
        st.caption("Based on LinkedIn engagement data")
    
    # Schedule button
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button("🚀 Schedule Post", type="primary", use_container_width=True):
            if schedule_datetime > datetime.now():
                # Schedule the post
                try:
                    updated_post = db.schedule_post(
                        post_id=post.id,
                        scheduled_time=scheduled_time.replace(tzinfo=None)  # Store as UTC
                    )
                    
                    st.success("✅ Post scheduled successfully!")
                    
                    # Update session state
                    st.session_state.schedule_date = schedule_date
                    st.session_state.schedule_time = schedule_time
                    st.session_state.timezone = timezone
                    st.session_state.selected_post_for_scheduling = None
                    
                    # Refresh the page
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error scheduling post: {str(e)}")
            else:
                st.error("Cannot schedule post in the past!")
    
    # Cancel button
    if st.button("❌ Cancel", use_container_width=True):
        st.session_state.selected_post_for_scheduling = None
        st.rerun()


def render_scheduled_posts():
    """Render list of scheduled posts"""
    st.markdown("## 📋 Scheduled Posts")
    
    # Get scheduled posts
    scheduled_posts = db.get_scheduled_posts()
    
    if not scheduled_posts:
        st.info("No posts scheduled yet.")
        return
    
    # Filter and sort options
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.selectbox(
            "Filter by status",
            options=['All', 'Pending', 'Published', 'Failed', 'Cancelled'],
            index=0
        )
    
    with col2:
        time_filter = st.selectbox(
            "Time range",
            options=['All', 'Next 24 hours', 'Next week', 'Past'],
            index=0
        )
    
    with col3:
        sort_option = st.selectbox(
            "Sort by",
            options=['Scheduled time (nearest first)', 'Created date', 'Status'],
            index=0
        )
    
    # Process and display posts
    for item in scheduled_posts:
        scheduled_info = item['scheduled']
        post_info = item['post']
        
        # Apply filters
        if status_filter != 'All' and scheduled_info['status'] != status_filter.lower():
            continue
        
        render_scheduled_post_card(scheduled_info, post_info)


def render_scheduled_post_card(scheduled_info: Dict, post_info: Dict):
    """Render a single scheduled post card"""
    # Determine card style based on timing
    scheduled_time = datetime.fromisoformat(scheduled_info['scheduled_time'])
    now = datetime.now()
    time_diff = scheduled_time - now
    
    if time_diff.total_seconds() < 0:
        card_class = "schedule-card-urgent"  # Past due
        time_status = "⚠️ Overdue"
        time_color = "red"
    elif time_diff.total_seconds() < 3600:  # Less than 1 hour
        card_class = "schedule-card-soon"
        time_status = "🕐 Soon"
        time_color = "orange"
    else:
        card_class = "schedule-card-future"
        time_status = "📅 Scheduled"
        time_color = "green"
    
    with st.container():
        st.markdown(f"<div class='schedule-card {card_class}'>", unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        
        with col1:
            # Post content preview
            content_preview = post_info['content'][:100] + "..." if len(post_info['content']) > 100 else post_info['content']
            st.markdown(f"**{post_info['post_type'].title()}** - {content_preview}")
            
            # Scheduled time
            st.markdown(f"<span style='color: {time_color};'>{time_status}</span> - {format_datetime(scheduled_time)}", 
                       unsafe_allow_html=True)
        
        with col2:
            # Status
            status = scheduled_info['status']
            status_color = {
                'pending': '#ffc107',
                'published': '#28a745',
                'failed': '#dc3545',
                'cancelled': '#6c757d'
            }.get(status, '#6c757d')
            
            st.markdown(f"<span style='color: {status_color};'>●</span> {status.title()}", 
                       unsafe_allow_html=True)
        
        with col3:
            # Time until/since
            if time_diff.total_seconds() > 0:
                time_until = get_time_ago(scheduled_time, future=True)
                st.caption(f"In {time_until}")
            else:
                time_since = get_time_ago(scheduled_time)
                st.caption(f"{time_since} ago")
        
        with col4:
            # Actions
            if status == 'pending':
                col_edit, col_cancel = st.columns(2)
                
                with col_edit:
                    if st.button("✏️", key=f"edit_{scheduled_info['id']}", help="Edit schedule"):
                        # Load post for rescheduling
                        post = db.get_post(scheduled_info['post_id'])
                        if post:
                            st.session_state.selected_post_for_scheduling = post
                            st.rerun()
                
                with col_cancel:
                    if st.button("❌", key=f"cancel_{scheduled_info['id']}", help="Cancel"):
                        # Cancel scheduled post
                        db.update_post(
                            post_id=scheduled_info['post_id'],
                            status='draft',
                            scheduled_for=None
                        )
                        st.success("Post cancelled and moved back to drafts")
                        st.rerun()
            
            elif status == 'failed':
                if st.button("🔄", key=f"retry_{scheduled_info['id']}", help="Retry"):
                    # Retry failed post
                    post = db.get_post(scheduled_info['post_id'])
                    if post:
                        st.session_state.selected_post_for_scheduling = post
                        st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)


def render_bulk_scheduling():
    """Render bulk scheduling interface"""
    with st.expander("📦 Bulk Scheduling"):
        st.markdown("Schedule multiple posts at optimal times")
        
        # Get draft posts
        draft_posts = db.get_posts(status='draft', limit=10)
        
        if not draft_posts:
            st.info("No draft posts available for bulk scheduling.")
            return
        
        # Select posts for bulk scheduling
        selected_posts = []
        st.markdown("**Select posts to schedule:**")
        
        for post in draft_posts:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                preview = post.content[:80] + "..." if len(post.content) > 80 else post.content
                selected = st.checkbox(
                    f"{post.post_type.title()} - {preview}",
                    key=f"bulk_select_{post.id}"
                )
                if selected:
                    selected_posts.append(post)
            
            with col2:
                st.caption(f"Created: {format_datetime(post.created_at)}")
        
        if selected_posts:
            col1, col2 = st.columns(2)
            
            with col1:
                start_date = st.date_input(
                    "Start date",
                    value=datetime.now().date() + timedelta(days=1),
                    min_value=datetime.now().date()
                )
            
            with col2:
                posting_frequency = st.selectbox(
                    "Posting frequency",
                    options=['Daily', 'Every 2 days', 'Weekly', 'Custom intervals']
                )
            
            if st.button("📅 Schedule Selected Posts", type="primary"):
                # Implement bulk scheduling logic
                scheduled_count = schedule_posts_bulk(selected_posts, start_date, posting_frequency)
                st.success(f"✅ Scheduled {scheduled_count} posts successfully!")
                st.rerun()


def schedule_posts_bulk(posts: List[Post], start_date: datetime.date, frequency: str) -> int:
    """Schedule multiple posts with optimal timing"""
    optimal_times = [time(9, 0), time(10, 0), time(14, 0), time(15, 0)]
    scheduled_count = 0
    
    current_date = start_date
    
    for i, post in enumerate(posts):
        # Calculate posting time
        if frequency == 'Daily':
            days_offset = i
        elif frequency == 'Every 2 days':
            days_offset = i * 2
        elif frequency == 'Weekly':
            days_offset = i * 7
        else:
            days_offset = i  # Default to daily
        
        post_date = current_date + timedelta(days=days_offset)
        post_time = optimal_times[i % len(optimal_times)]
        
        schedule_datetime = datetime.combine(post_date, post_time)
        
        try:
            db.schedule_post(post.id, schedule_datetime)
            scheduled_count += 1
        except Exception as e:
            print(f"Error scheduling post {post.id}: {e}")
    
    return scheduled_count


def render_publishing_status():
    """Render current publishing status and manual controls"""
    st.markdown("## 🚀 Publishing Status")
    
    # Get LinkedIn publisher status
    publisher = LinkedInPublisher()
    stats = publisher.get_posting_stats()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Posts Today", stats['posts_today'])
    
    with col2:
        st.metric("Daily Limit", stats['daily_limit'])
    
    with col3:
        remaining = stats['posts_remaining']
        st.metric("Remaining", remaining)
    
    with col4:
        can_post = "✅ Yes" if stats['can_post_now'] else "❌ No"
        st.metric("Can Post Now", can_post)
    
    # Manual publishing controls
    if st.button("🔄 Process Scheduled Posts Now"):
        with st.spinner("Processing scheduled posts..."):
            scheduler = LinkedInScheduler()
            
            # Run async function
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(scheduler.process_scheduled_posts())
            loop.close()
            
            if results:
                st.success(f"Processed {len(results)} posts")
                for result in results:
                    if result['status'] == 'published':
                        st.success(f"✅ Post {result['post_id']} published successfully")
                    else:
                        st.error(f"❌ Post {result['post_id']} failed: {result.get('error', 'Unknown error')}")
            else:
                st.info("No posts were ready for publishing")


def main():
    """Main function for schedule page"""
    init_page_state()
    render_header()
    
    # Navigation tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Schedule New", "📋 Scheduled Posts", "📦 Bulk Schedule", "🚀 Publishing"])
    
    with tab1:
        render_schedule_new_post()
    
    with tab2:
        render_scheduled_posts()
    
    with tab3:
        render_bulk_scheduling()
    
    with tab4:
        render_publishing_status()
    
    # Footer with helpful tips
    st.markdown("---")
    st.markdown("### 💡 Pro Tips")
    st.info("""
    **Best practices for LinkedIn scheduling:**
    • Post during business hours (9-10 AM, 2-3 PM) for higher engagement
    • Maintain consistent posting frequency
    • Schedule posts 1-2 days in advance to avoid timing issues
    • Monitor your daily posting limits to avoid being blocked
    """)


if __name__ == "__main__":
    main()
