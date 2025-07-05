"""
Schedule Posts Page - VERSIONE COMPLETA CORRETTA
Fix per tutti i problemi di accesso agli attributi Post
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
    
    .status-pending { color: #ffc107; }
    .status-published { color: #28a745; }
    .status-failed { color: #dc3545; }
    .status-cancelled { color: #6c757d; }
    
    .post-preview {
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


def init_page_state():
    """Initialize page-specific session state"""
    if 'selected_post_id_for_scheduling' not in st.session_state:
        st.session_state.selected_post_id_for_scheduling = None

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
        try:
            connection_status = check_linkedin_connection()
            if connection_status.get('authenticated', False):
                st.success("✅ LinkedIn Connected")
            else:
                st.error(f"❌ LinkedIn: {connection_status.get('error', 'Not connected')}")
        except Exception as e:
            st.error(f"❌ LinkedIn: Connection error")

    with col3:
        # Current time info
        try:
            tz = pytz.timezone(st.session_state.timezone)
            current_time = datetime.now(tz)
            st.info(f"🕐 {current_time.strftime('%H:%M')} {st.session_state.timezone}")
        except:
            st.info(f"🕐 {datetime.now().strftime('%H:%M')} Local")


def render_schedule_new_post():
    """Render section for scheduling a new post"""
    st.markdown("## 📝 Schedule New Post")

    # Check if there's a post to schedule from session state
    if hasattr(st.session_state, 'post_to_schedule') and st.session_state.post_to_schedule:
        post_id = st.session_state.post_to_schedule

        # Ensure post_id is an integer
        if not isinstance(post_id, int):
            try:
                post_id = int(post_id)
            except (ValueError, TypeError):
                st.error("Invalid post ID")
                del st.session_state.post_to_schedule
                return

        # Get the post
        try:
            post = db.get_post(post_id)
            if post:
                content_preview = (post.content[:50] if post.content else "No content")
                st.success(f"✅ Post ready for scheduling: {content_preview}...")
                st.session_state.selected_post_id_for_scheduling = post_id
                del st.session_state.post_to_schedule
            else:
                st.error("Post not found")
                del st.session_state.post_to_schedule
        except Exception as e:
            st.error(f"Error loading post: {str(e)}")
            del st.session_state.post_to_schedule

    # Post selection
    if not st.session_state.selected_post_id_for_scheduling:
        render_post_selection()
    else:
        render_scheduling_interface()


def render_post_selection():
    """Render interface for selecting a post to schedule"""
    # Get draft posts
    try:
        draft_posts = db.get_posts(status='draft', limit=20)
    except Exception as e:
        st.error(f"Error loading posts: {str(e)}")
        return

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
                # Safe attribute access
                post_type_display = "Unknown"
                if post.post_type:
                    post_type_display = post.post_type.replace('_', ' ').title()

                tone_display = "Unknown"
                if post.tone:
                    tone_display = post.tone.title()

                st.markdown(f"**{post_type_display}** - {tone_display}")

                # Safe content preview
                content = post.content or ""
                preview = content[:100] + "..." if len(content) > 100 else content
                st.text(preview)

                # Safe date formatting
                created_at = post.created_at or datetime.now()
                st.caption(f"Created: {format_datetime(created_at)}")

            with col2:
                # Character count
                content_length = len(post.content or "")
                st.metric("Characters", content_length)

                # Model info
                if post.model_used:
                    model_display = post.model_used.split('-')[0].upper()
                    st.caption(f"Model: {model_display}")

            with col3:
                # Action buttons
                if st.button("📅 Schedule", key=f"schedule_post_{post.id}"):
                    st.session_state.selected_post_id_for_scheduling = post.id
                    st.rerun()

                if st.button("👁️ Preview", key=f"preview_post_{post.id}"):
                    with st.expander("Post Preview", expanded=True):
                        st.text_area("Content", value=post.content or "", height=150, disabled=True)


def render_scheduling_interface():
    """Render scheduling interface for selected post"""
    post_id = st.session_state.selected_post_id_for_scheduling

    try:
        post = db.get_post(post_id)
    except Exception as e:
        st.error(f"Error loading post: {str(e)}")
        st.session_state.selected_post_id_for_scheduling = None
        st.rerun()
        return

    if not post:
        st.error("Post not found. Please select another post.")
        st.session_state.selected_post_id_for_scheduling = None
        st.rerun()
        return

    st.markdown("### 📝 Post to Schedule")

    # Post preview
    with st.expander("👁️ Post Preview", expanded=True):
        st.text_area(
            "Content",
            value=post.content or "",
            height=200,
            disabled=True
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Characters", len(post.content or ""))
        with col2:
            post_type_display = "Unknown"
            if post.post_type:
                post_type_display = post.post_type.replace('_', ' ').title()
            st.metric("Type", post_type_display)
        with col3:
            tone_display = "Unknown"
            if post.tone:
                tone_display = post.tone.title()
            st.metric("Tone", tone_display)

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

        try:
            tz = pytz.timezone(timezone)
            scheduled_time = tz.localize(schedule_datetime)
        except Exception as e:
            st.error(f"Timezone error: {str(e)}")
            return

        # Show converted time
        st.info(f"⏰ Scheduled for: {scheduled_time.strftime('%Y-%m-%d %H:%M %Z')}")

        # Show time until posting
        try:
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
        except Exception as e:
            st.warning(f"Time calculation error: {str(e)}")

    with col2:
        # Optimal posting times
        st.markdown("### 💡 Suggested Times")
        st.markdown("**Best times to post:**")

        # Orari ottimali definiti direttamente (più affidabile)
        optimal_times_data = [
            {"time": "09:00", "hour": 9, "minute": 0, "desc": "Morning peak"},
            {"time": "10:00", "hour": 10, "minute": 0, "desc": "Late morning"},
            {"time": "14:00", "hour": 14, "minute": 0, "desc": "Early afternoon"},
            {"time": "15:00", "hour": 15, "minute": 0, "desc": "Mid afternoon"}
        ]

        for time_data in optimal_times_data:
            col_btn, col_desc = st.columns([1, 2])

            with col_btn:
                if st.button(f"🕐 {time_data['time']}", key=f"optimal_{time_data['time']}"):
                    st.session_state.schedule_time = time(time_data['hour'], time_data['minute'])
                    st.success(f"✅ Time set to {time_data['time']}")
                    st.rerun()

            with col_desc:
                st.caption(time_data['desc'])

        st.markdown("---")
        st.caption("📊 Based on LinkedIn engagement data")
        st.caption("💡 Business hours typically perform best")

    # Schedule button
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        if st.button("🚀 Schedule Post", type="primary", use_container_width=True):
            if schedule_datetime > datetime.now():
                try:
                    # Schedule the post
                    success = db.schedule_post(
                        post_id=post.id,
                        scheduled_time=scheduled_time.replace(tzinfo=None)
                    )

                    if success:
                        st.success("✅ Post scheduled successfully!")

                        # Update session state
                        st.session_state.schedule_date = schedule_date
                        st.session_state.schedule_time = schedule_time
                        st.session_state.timezone = timezone
                        st.session_state.selected_post_id_for_scheduling = None

                        # Refresh the page
                        st.rerun()
                    else:
                        st.error("Failed to schedule post")

                except Exception as e:
                    st.error(f"Error scheduling post: {str(e)}")
            else:
                st.error("Cannot schedule post in the past!")

    # Cancel button
    if st.button("❌ Cancel", use_container_width=True):
        st.session_state.selected_post_id_for_scheduling = None
        st.rerun()


def render_scheduled_posts():
    """Render list of scheduled posts"""
    st.markdown("## 📋 Scheduled Posts")

    # Get scheduled posts
    try:
        scheduled_posts = db.get_scheduled_posts()
    except Exception as e:
        st.error(f"Error loading scheduled posts: {str(e)}")
        return

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
        try:
            scheduled_info = item['scheduled']
            post_info = item['post']

            # Apply filters
            if status_filter != 'All' and scheduled_info.get('status', '') != status_filter.lower():
                continue

            render_scheduled_post_card(scheduled_info, post_info)
        except Exception as e:
            st.error(f"Error displaying scheduled post: {str(e)}")


def render_scheduled_post_card(scheduled_info: Dict, post_info: Dict):
    """Render a single scheduled post card"""
    try:
        # Determine card style based on timing
        scheduled_time_str = scheduled_info.get('scheduled_time', '')
        if not scheduled_time_str:
            st.error("Invalid scheduled time")
            return

        scheduled_time = datetime.fromisoformat(scheduled_time_str)
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
                content = post_info.get('content', '')
                content_preview = content[:100] + "..." if len(content) > 100 else content

                # Safe access to post_type
                post_type = post_info.get('post_type', 'unknown')
                post_type_display = post_type.replace('_', ' ').title() if post_type else "Unknown"

                st.markdown(f"**{post_type_display}** - {content_preview}")

                # Scheduled time
                st.markdown(f"<span style='color: {time_color};'>{time_status}</span> - {format_datetime(scheduled_time)}",
                           unsafe_allow_html=True)

            with col2:
                # Status
                status = scheduled_info.get('status', 'unknown')
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
                        if st.button("✏️", key=f"edit_{scheduled_info.get('id')}", help="Edit schedule"):
                            st.session_state.selected_post_id_for_scheduling = scheduled_info.get('post_id')
                            st.rerun()

                    with col_cancel:
                        if st.button("❌", key=f"cancel_{scheduled_info.get('id')}", help="Cancel"):
                            try:
                                # Cancel scheduled post
                                db.update_post(
                                    post_id=scheduled_info.get('post_id'),
                                    status='draft',
                                    scheduled_for=None
                                )
                                st.success("Post cancelled and moved back to drafts")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error cancelling post: {str(e)}")

                elif status == 'failed':
                    if st.button("🔄", key=f"retry_{scheduled_info.get('id')}", help="Retry"):
                        st.session_state.selected_post_id_for_scheduling = scheduled_info.get('post_id')
                        st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Error rendering scheduled post card: {str(e)}")


def render_bulk_scheduling():
    """Render bulk scheduling interface"""
    with st.expander("📦 Bulk Scheduling"):
        st.markdown("Schedule multiple posts at optimal times")

        # Get draft posts
        try:
            draft_posts = db.get_posts(status='draft', limit=10)
        except Exception as e:
            st.error(f"Error loading posts: {str(e)}")
            return

        if not draft_posts:
            st.info("No draft posts available for bulk scheduling.")
            return

        # Select posts for bulk scheduling
        selected_post_ids = []
        st.markdown("**Select posts to schedule:**")

        for post in draft_posts:
            col1, col2 = st.columns([3, 1])

            with col1:
                content = post.content or ""
                preview = content[:80] + "..." if len(content) > 80 else content

                post_type = post.post_type or "unknown"
                post_type_display = post_type.replace('_', ' ').title()

                selected = st.checkbox(
                    f"{post_type_display} - {preview}",
                    key=f"bulk_select_{post.id}"
                )
                if selected:
                    selected_post_ids.append(post.id)

            with col2:
                created_at = post.created_at or datetime.now()
                st.caption(f"Created: {format_datetime(created_at)}")

        if selected_post_ids:
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
                try:
                    # Implement bulk scheduling logic
                    scheduled_count = schedule_posts_bulk(selected_post_ids, start_date, posting_frequency)
                    st.success(f"✅ Scheduled {scheduled_count} posts successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error bulk scheduling: {str(e)}")


def schedule_posts_bulk(post_ids: List[int], start_date: datetime.date, frequency: str) -> int:
    """Schedule multiple posts with optimal timing"""
    try:
        optimal_times = [time(9, 0), time(10, 0), time(14, 0), time(15, 0)]
        scheduled_count = 0

        current_date = start_date

        for i, post_id in enumerate(post_ids):
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
                db.schedule_post(post_id, schedule_datetime)
                scheduled_count += 1
            except Exception as e:
                st.warning(f"Failed to schedule post {post_id}: {str(e)}")

        return scheduled_count
    except Exception as e:
        st.error(f"Bulk scheduling error: {str(e)}")
        return 0


def render_publishing_status():
    """Render current publishing status and manual controls"""
    st.markdown("## 🚀 Publishing Status")

    try:
        # Get LinkedIn publisher status
        publisher = LinkedInPublisher()
        stats = publisher.get_posting_stats()

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Posts Today", stats.get('posts_today', 0))

        with col2:
            st.metric("Daily Limit", stats.get('daily_limit', 0))

        with col3:
            remaining = stats.get('posts_remaining', 0)
            st.metric("Remaining", remaining)

        with col4:
            can_post = "✅ Yes" if stats.get('can_post_now', False) else "❌ No"
            st.metric("Can Post Now", can_post)

        # Manual publishing controls
        if st.button("🔄 Process Scheduled Posts Now"):
            with st.spinner("Processing scheduled posts..."):
                try:
                    scheduler = LinkedInScheduler()

                    # Run async function
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    results = loop.run_until_complete(scheduler.process_scheduled_posts())
                    loop.close()

                    if results:
                        st.success(f"Processed {len(results)} posts")
                        for result in results:
                            if result.get('status') == 'published':
                                st.success(f"✅ Post {result.get('post_id')} published successfully")
                            else:
                                st.error(f"❌ Post {result.get('post_id')} failed: {result.get('error', 'Unknown error')}")
                    else:
                        st.info("No posts were ready for publishing")
                except Exception as e:
                    st.error(f"Error processing scheduled posts: {str(e)}")

    except Exception as e:
        st.error(f"Error loading publishing status: {str(e)}")


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