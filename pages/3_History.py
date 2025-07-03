"""
Post History & Analytics Page
View past posts, analytics, and performance metrics
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from pathlib import Path
import sys
from typing import List, Dict, Optional, Any
import json

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Local imports
from config import config
from src.database import db, Post
from utils.helpers import (
    format_datetime, 
    get_time_ago, 
    calculate_engagement_rate,
    export_posts_to_csv,
    get_post_performance_category
)

# Page config
st.set_page_config(
    page_title="History & Analytics - LinkedIn Generator",
    page_icon="📊",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    /* Analytics cards */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        text-align: center;
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
        margin: 0.5rem 0;
    }
    
    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
    
    /* Post cards */
    .post-card {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        background: white;
    }
    
    .post-card:hover {
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        transition: box-shadow 0.3s ease;
    }
    
    .post-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.5rem;
    }
    
    .post-status {
        padding: 0.25rem 0.5rem;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    
    .status-published { background: #d4edda; color: #155724; }
    .status-draft { background: #fff3cd; color: #856404; }
    .status-scheduled { background: #cce5ff; color: #004085; }
    .status-failed { background: #f8d7da; color: #721c24; }
    
    /* Performance indicators */
    .performance-high { border-left: 4px solid #28a745; }
    .performance-medium { border-left: 4px solid #ffc107; }
    .performance-low { border-left: 4px solid #dc3545; }
    
    /* Charts */
    .chart-container {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)


def init_page_state():
    """Initialize page-specific session state"""
    if 'date_range' not in st.session_state:
        st.session_state.date_range = 30  # Default to last 30 days
    
    if 'status_filter' not in st.session_state:
        st.session_state.status_filter = 'All'
    
    if 'performance_filter' not in st.session_state:
        st.session_state.performance_filter = 'All'


def render_header():
    """Render page header with summary stats"""
    st.title("📊 Post History & Analytics")
    st.markdown("Track your LinkedIn post performance and insights")
    
    # Get summary analytics
    analytics = db.get_analytics_summary()
    
    # Display key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total Posts",
            value=analytics['total_posts'],
            delta=None
        )
    
    with col2:
        st.metric(
            label="Published",
            value=analytics['published_posts'],
            delta=f"{analytics['published_posts'] - (analytics['total_posts'] - analytics['published_posts'])} vs drafts"
        )
    
    with col3:
        st.metric(
            label="Avg Engagement",
            value=f"{analytics['average_engagement_rate']:.1f}%",
            delta="Industry avg: 2.3%" if analytics['average_engagement_rate'] > 2.3 else None
        )
    
    with col4:
        st.metric(
            label="Total Views",
            value=f"{analytics['total_views']:,}",
            delta=None
        )


def render_analytics_dashboard():
    """Render analytics dashboard with charts"""
    st.markdown("## 📈 Analytics Dashboard")
    
    # Time range selector
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        date_range = st.selectbox(
            "Time Range",
            options=[7, 30, 90, 180, 365],
            format_func=lambda x: f"Last {x} days",
            index=1  # Default to 30 days
        )
    
    with col2:
        post_type_filter = st.selectbox(
            "Post Type",
            options=['All'] + [t.replace('_', ' ').title() for t in config.POST_TYPE_OPTIONS]
        )
    
    with col3:
        if st.button("📊 Refresh Analytics"):
            st.rerun()
    
    # Get posts for the time range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=date_range)
    
    posts = db.get_posts(status='published', limit=200)
    posts_df = prepare_posts_dataframe(posts, start_date, end_date)
    
    if posts_df.empty:
        st.info("No published posts found for the selected time range.")
        return
    
    # Create charts
    render_engagement_trend_chart(posts_df)
    
    col1, col2 = st.columns(2)
    
    with col1:
        render_post_type_performance_chart(posts_df)
    
    with col2:
        render_posting_time_analysis_chart(posts_df)
    
    # Performance insights
    render_performance_insights(posts_df)


def prepare_posts_dataframe(posts: List[Post], start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """Prepare posts data for analytics"""
    data = []
    
    for post in posts:
        if not post.published_at:
            continue
        
        if start_date <= post.published_at <= end_date:
            # Calculate engagement rate
            total_interactions = (post.likes or 0) + (post.comments or 0) + (post.shares or 0)
            engagement_rate = (total_interactions / post.views * 100) if post.views else 0
            
            data.append({
                'id': post.id,
                'published_at': post.published_at,
                'post_type': post.post_type,
                'tone': post.tone,
                'content_length': len(post.content),
                'views': post.views or 0,
                'likes': post.likes or 0,
                'comments': post.comments or 0,
                'shares': post.shares or 0,
                'engagement_rate': engagement_rate,
                'model_used': post.model_used,
                'hashtag_count': len(post.hashtags) if post.hashtags else 0,
                'hour': post.published_at.hour,
                'day_of_week': post.published_at.strftime('%A'),
                'content_preview': post.content[:100] + "..." if len(post.content) > 100 else post.content
            })
    
    return pd.DataFrame(data)


def render_engagement_trend_chart(df: pd.DataFrame):
    """Render engagement trend over time"""
    st.markdown("### 📈 Engagement Trend")
    
    if df.empty:
        st.info("No data available for trend analysis.")
        return
    
    # Group by date
    daily_engagement = df.groupby(df['published_at'].dt.date).agg({
        'engagement_rate': 'mean',
        'views': 'sum',
        'likes': 'sum',
        'comments': 'sum',
        'shares': 'sum'
    }).reset_index()
    
    # Create line chart
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=daily_engagement['published_at'],
        y=daily_engagement['engagement_rate'],
        mode='lines+markers',
        name='Engagement Rate (%)',
        line=dict(color='#0A66C2', width=3),
        marker=dict(size=8)
    ))
    
    fig.update_layout(
        title="Daily Engagement Rate Trend",
        xaxis_title="Date",
        yaxis_title="Engagement Rate (%)",
        height=400,
        showlegend=False,
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_post_type_performance_chart(df: pd.DataFrame):
    """Render post type performance comparison"""
    st.markdown("### 📝 Post Type Performance")
    
    if df.empty:
        st.info("No data available.")
        return
    
    # Group by post type
    type_performance = df.groupby('post_type').agg({
        'engagement_rate': 'mean',
        'views': 'mean',
        'id': 'count'
    }).reset_index()
    
    type_performance.columns = ['Post Type', 'Avg Engagement Rate', 'Avg Views', 'Post Count']
    
    # Create bar chart
    fig = px.bar(
        type_performance,
        x='Post Type',
        y='Avg Engagement Rate',
        color='Avg Engagement Rate',
        color_continuous_scale='viridis',
        title="Average Engagement Rate by Post Type",
        text='Post Count'
    )
    
    fig.update_traces(texttemplate='%{text} posts', textposition='outside')
    fig.update_layout(height=400, showlegend=False)
    
    st.plotly_chart(fig, use_container_width=True)


def render_posting_time_analysis_chart(df: pd.DataFrame):
    """Render posting time analysis"""
    st.markdown("### 🕐 Best Posting Times")
    
    if df.empty:
        st.info("No data available.")
        return
    
    # Group by hour
    hourly_performance = df.groupby('hour').agg({
        'engagement_rate': 'mean',
        'id': 'count'
    }).reset_index()
    
    # Create heatmap-style chart
    fig = px.bar(
        hourly_performance,
        x='hour',
        y='engagement_rate',
        color='engagement_rate',
        color_continuous_scale='RdYlGn',
        title="Engagement Rate by Posting Hour",
        labels={'hour': 'Hour of Day', 'engagement_rate': 'Avg Engagement Rate (%)'}
    )
    
    fig.update_layout(height=400, showlegend=False)
    fig.update_xaxis(tickmode='linear', tick0=0, dtick=2)
    
    st.plotly_chart(fig, use_container_width=True)


def render_performance_insights(df: pd.DataFrame):
    """Render AI-powered performance insights"""
    st.markdown("### 🔍 Performance Insights")
    
    if df.empty:
        st.info("No data available for insights.")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🏆 Top Performing Posts")
        
        top_posts = df.nlargest(3, 'engagement_rate')
        
        for _, post in top_posts.iterrows():
            st.markdown(f"""
            **{post['engagement_rate']:.1f}% engagement**
            
            {post['content_preview']}
            
            📊 {post['views']} views • ❤️ {post['likes']} likes • 💬 {post['comments']} comments
            """)
            st.markdown("---")
    
    with col2:
        st.markdown("#### 💡 Recommendations")
        
        # Generate insights
        insights = generate_performance_insights(df)
        
        for insight in insights:
            st.markdown(f"• {insight}")


def generate_performance_insights(df: pd.DataFrame) -> List[str]:
    """Generate performance insights from data"""
    insights = []
    
    if df.empty:
        return ["Not enough data for insights."]
    
    # Best performing post type
    best_type = df.groupby('post_type')['engagement_rate'].mean().idxmax()
    insights.append(f"**{best_type.replace('_', ' ').title()}** posts perform best with {df[df['post_type'] == best_type]['engagement_rate'].mean():.1f}% avg engagement")
    
    # Best posting hour
    best_hour = df.groupby('hour')['engagement_rate'].mean().idxmax()
    insights.append(f"Posts at **{best_hour}:00** get highest engagement ({df[df['hour'] == best_hour]['engagement_rate'].mean():.1f}%)")
    
    # Content length insights
    high_eng_length = df[df['engagement_rate'] > df['engagement_rate'].mean()]['content_length'].mean()
    insights.append(f"High-engagement posts average **{high_eng_length:.0f} characters**")
    
    # Hashtag insights
    if 'hashtag_count' in df.columns:
        optimal_hashtags = df.groupby('hashtag_count')['engagement_rate'].mean().idxmax()
        insights.append(f"Posts with **{optimal_hashtags} hashtags** tend to perform better")
    
    # Model performance
    if 'model_used' in df.columns and df['model_used'].nunique() > 1:
        best_model = df.groupby('model_used')['engagement_rate'].mean().idxmax()
        model_name = best_model.split('-')[0].upper() if best_model else "Unknown"
        insights.append(f"**{model_name}** generated content shows higher engagement")
    
    return insights


def render_post_history():
    """Render filterable post history"""
    st.markdown("## 📋 Post History")
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        status_filter = st.selectbox(
            "Status",
            options=['All', 'Published', 'Draft', 'Scheduled', 'Failed']
        )
    
    with col2:
        post_type_filter = st.selectbox(
            "Type",
            options=['All'] + config.POST_TYPE_OPTIONS
        )
    
    with col3:
        date_filter = st.selectbox(
            "Date Range",
            options=['All time', 'Last 7 days', 'Last 30 days', 'Last 90 days']
        )
    
    with col4:
        sort_option = st.selectbox(
            "Sort by",
            options=['Newest first', 'Oldest first', 'Highest engagement', 'Most views']
        )
    
    # Get filtered posts
    posts = get_filtered_posts(status_filter, post_type_filter, date_filter, sort_option)
    
    # Display posts
    if not posts:
        st.info("No posts found matching the selected filters.")
        return
    
    # Pagination
    posts_per_page = 10
    total_pages = (len(posts) - 1) // posts_per_page + 1
    
    if total_pages > 1:
        page = st.selectbox(f"Page (1-{total_pages})", range(1, total_pages + 1)) - 1
        start_idx = page * posts_per_page
        end_idx = start_idx + posts_per_page
        posts_to_show = posts[start_idx:end_idx]
    else:
        posts_to_show = posts
    
    # Display posts
    for post in posts_to_show:
        render_post_card(post)


def get_filtered_posts(status_filter: str, post_type_filter: str, date_filter: str, sort_option: str) -> List[Post]:
    """Get posts based on filters"""
    # Base query
    posts = db.get_posts(limit=1000)  # Get all posts
    
    # Apply filters
    filtered_posts = []
    
    for post in posts:
        # Status filter
        if status_filter != 'All' and post.status != status_filter.lower():
            continue
        
        # Post type filter
        if post_type_filter != 'All' and post.post_type != post_type_filter:
            continue
        
        # Date filter
        if date_filter != 'All time':
            days = {'Last 7 days': 7, 'Last 30 days': 30, 'Last 90 days': 90}[date_filter]
            cutoff_date = datetime.now() - timedelta(days=days)
            
            if post.created_at < cutoff_date:
                continue
        
        filtered_posts.append(post)
    
    # Sort posts
    if sort_option == 'Newest first':
        filtered_posts.sort(key=lambda x: x.created_at, reverse=True)
    elif sort_option == 'Oldest first':
        filtered_posts.sort(key=lambda x: x.created_at)
    elif sort_option == 'Highest engagement':
        filtered_posts.sort(key=lambda x: x.engagement_rate or 0, reverse=True)
    elif sort_option == 'Most views':
        filtered_posts.sort(key=lambda x: x.views or 0, reverse=True)
    
    return filtered_posts


def render_post_card(post: Post):
    """Render a single post card"""
    # Determine performance category
    performance = get_post_performance_category(post.engagement_rate or 0)
    performance_class = f"performance-{performance}"
    
    with st.container():
        st.markdown(f"<div class='post-card {performance_class}'>", unsafe_allow_html=True)
        
        # Header
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.markdown(f"**{post.post_type.replace('_', ' ').title()}** - {post.tone.title()}")
        
        with col2:
            # Status badge
            status_class = f"status-{post.status}"
            st.markdown(f"<span class='post-status {status_class}'>{post.status.title()}</span>", 
                       unsafe_allow_html=True)
        
        with col3:
            st.caption(format_datetime(post.created_at))
        
        # Content preview
        content_preview = post.content[:200] + "..." if len(post.content) > 200 else post.content
        st.text(content_preview)
        
        # Metrics (if published)
        if post.status == 'published' and (post.views or post.likes or post.comments):
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric("Views", post.views or 0)
            with col2:
                st.metric("Likes", post.likes or 0)
            with col3:
                st.metric("Comments", post.comments or 0)
            with col4:
                st.metric("Shares", post.shares or 0)
            with col5:
                engagement = post.engagement_rate or 0
                st.metric("Engagement", f"{engagement:.1f}%")
        
        # Actions
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("👁️ View", key=f"view_{post.id}"):
                show_post_details(post)
        
        with col2:
            if st.button("📋 Copy", key=f"copy_{post.id}"):
                st.code(post.content)
                st.success("Content ready to copy!")
        
        with col3:
            if post.status == 'draft':
                if st.button("📅 Schedule", key=f"schedule_{post.id}"):
                    st.session_state.post_to_schedule = post.id
                    st.switch_page("pages/2_📅_Schedule.py")
        
        with col4:
            if post.linkedin_post_url:
                st.markdown(f"[🔗 LinkedIn]({post.linkedin_post_url})")
        
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("")  # Add spacing


def show_post_details(post: Post):
    """Show detailed post information in modal"""
    with st.expander(f"📄 Post Details - {post.id}", expanded=True):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### Content")
            st.text_area("Full content", post.content, height=200, disabled=True)
            
            if post.hashtags:
                st.markdown("### Hashtags")
                st.write(" ".join(post.hashtags))
        
        with col2:
            st.markdown("### Metadata")
            st.write(f"**Status:** {post.status.title()}")
            st.write(f"**Type:** {post.post_type.replace('_', ' ').title()}")
            st.write(f"**Tone:** {post.tone.title()}")
            st.write(f"**Created:** {format_datetime(post.created_at)}")
            
            if post.published_at:
                st.write(f"**Published:** {format_datetime(post.published_at)}")
            
            if post.scheduled_for:
                st.write(f"**Scheduled:** {format_datetime(post.scheduled_for)}")
            
            if post.model_used:
                st.write(f"**Model:** {post.model_used}")
            
            st.markdown("### Performance")
            if post.status == 'published':
                st.write(f"**Views:** {post.views or 0:,}")
                st.write(f"**Likes:** {post.likes or 0:,}")
                st.write(f"**Comments:** {post.comments or 0:,}")
                st.write(f"**Shares:** {post.shares or 0:,}")
                st.write(f"**Engagement Rate:** {post.engagement_rate or 0:.2f}%")
            else:
                st.write("Not published yet")


def render_export_options():
    """Render data export options"""
    st.markdown("## 📥 Export Data")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Export Analytics CSV"):
            # Generate analytics CSV
            posts = db.get_posts(status='published', limit=1000)
            csv_data = export_posts_to_csv(posts)
            
            st.download_button(
                label="📊 Download Analytics CSV",
                data=csv_data,
                file_name=f"linkedin_analytics_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    
    with col2:
        if st.button("📝 Export All Posts JSON"):
            # Generate posts JSON
            posts = db.get_posts(limit=1000)
            posts_data = [post.to_dict() for post in posts]
            json_data = json.dumps(posts_data, indent=2, default=str)
            
            st.download_button(
                label="📝 Download Posts JSON",
                data=json_data,
                file_name=f"linkedin_posts_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json"
            )
    
    with col3:
        if st.button("📈 Export Performance Report"):
            # Generate performance report
            posts = db.get_posts(status='published', limit=1000)
            df = prepare_posts_dataframe(posts, datetime.now() - timedelta(days=365), datetime.now())
            
            if not df.empty:
                report = generate_performance_report(df)
                
                st.download_button(
                    label="📈 Download Report",
                    data=report,
                    file_name=f"linkedin_performance_report_{datetime.now().strftime('%Y%m%d')}.txt",
                    mime="text/plain"
                )


def generate_performance_report(df: pd.DataFrame) -> str:
    """Generate a text-based performance report"""
    report = f"""
LinkedIn Post Performance Report
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

=== SUMMARY ===
Total Posts Analyzed: {len(df)}
Average Engagement Rate: {df['engagement_rate'].mean():.2f}%
Total Views: {df['views'].sum():,}
Total Likes: {df['likes'].sum():,}
Total Comments: {df['comments'].sum():,}
Total Shares: {df['shares'].sum():,}

=== TOP PERFORMING POSTS ===
"""
    
    top_posts = df.nlargest(5, 'engagement_rate')
    for i, (_, post) in enumerate(top_posts.iterrows(), 1):
        report += f"""
{i}. Engagement: {post['engagement_rate']:.1f}%
   Type: {post['post_type']}
   Views: {post['views']:,} | Likes: {post['likes']} | Comments: {post['comments']}
   Content: {post['content_preview']}
"""
    
    report += f"""

=== INSIGHTS ===
"""
    
    insights = generate_performance_insights(df)
    for insight in insights:
        report += f"• {insight}\n"
    
    return report


def main():
    """Main function for history page"""
    init_page_state()
    render_header()
    
    # Navigation tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Analytics", "📋 Post History", "🔍 Details", "📥 Export"])
    
    with tab1:
        render_analytics_dashboard()
    
    with tab2:
        render_post_history()
    
    with tab3:
        st.markdown("## 🔍 Detailed Analytics")
        st.info("Advanced analytics features coming soon! This will include:")
        st.markdown("""
        - **Content Analysis**: AI-powered content performance analysis
        - **Audience Insights**: Who's engaging with your posts
        - **Competitor Benchmarking**: Compare your performance
        - **Trend Analysis**: Identify trending topics and hashtags
        - **ROI Tracking**: Measure business impact of your posts
        """)
    
    with tab4:
        render_export_options()


if __name__ == "__main__":
    main()
