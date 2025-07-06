"""
Create Post Page - Generate LinkedIn posts from various sources
UPDATED with Gemini support and Manual Publishing functionality
"""

import streamlit as st
import asyncio
import time
from datetime import datetime
from pathlib import Path
import sys
from typing import List, Dict, Optional

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Local imports
from config import config
from src.content_extractor import ContentExtractor, ExtractedContent, extract_content
from src.post_generator import PostGenerator, PostTone, PostType, generate_post
from src.database import db
from templates.prompts import PromptLibrary
from utils.helpers import validate_url, estimate_read_time, count_hashtags

# Page config
st.set_page_config(
    page_title="Create Post - LinkedIn Generator",
    page_icon="📝",
    layout="wide"
)

# Custom CSS for this page
st.markdown("""
<style>
    /* Source input cards */
    .source-card {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    
    /* Post preview cards */
    .post-card {
        background-color: #ffffff;
        border: 2px solid #0A66C2;
        border-radius: 8px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* Selected post highlight */
    .post-card-selected {
        background-color: #e7f3ff;
        border: 3px solid #0A66C2;
    }
    
    /* Character count */
    .char-count {
        text-align: right;
        color: #666;
        font-size: 0.9rem;
        margin-top: 0.5rem;
    }
    
    /* Success animation */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .success-message {
        animation: fadeIn 0.5s ease-out;
    }
    
    /* Manual publish interface */
    .linkedin-preview {
        border: 1px solid #e0e0e0; 
        border-radius: 8px; 
        padding: 16px; 
        background: white;
        margin: 16px 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)


def init_page_state():
    """Initialize page-specific session state"""
    if 'sources' not in st.session_state:
        st.session_state.sources = []

    if 'extracted_content' not in st.session_state:
        st.session_state.extracted_content = []

    if 'generated_posts' not in st.session_state:
        st.session_state.generated_posts = []

    if 'selected_post_index' not in st.session_state:
        st.session_state.selected_post_index = None

    if 'generation_in_progress' not in st.session_state:
        st.session_state.generation_in_progress = False

    # Manual publish state
    if 'show_manual_publish' not in st.session_state:
        st.session_state.show_manual_publish = False

    if 'edited_content' not in st.session_state:
        st.session_state.edited_content = ""

    # Load recent sources from database if sources is empty
    if 'sources_loaded' not in st.session_state:
        st.session_state.sources_loaded = False

    if 'show_recent_sources' not in st.session_state:
        st.session_state.show_recent_sources = False

def render_header():
    """Render page header"""
    col1, col2 = st.columns([3, 1])

    with col1:
        st.title("📝 Create New Post")
        st.markdown("Generate engaging LinkedIn content from multiple sources")

    with col2:
        # Quick stats
        active_llm, _ = config.get_llm_config()
        st.info(f"**Active Model:** {active_llm.upper() if active_llm else 'None'}")


def render_source_input():
    """Render source input section"""
    st.markdown("## 📥 Step 1: Add Content Sources")
    st.markdown("Add one or more sources to generate content from")

    # Tabs for different input types
    tab1, tab2, tab3, tab4 = st.tabs(["🌐 Web URL", "📄 Text/LinkedIn", "📑 PDF Upload", "🔗 Multiple URLs"])

    with tab1:
        render_url_input()

    with tab2:
        render_text_input()

    with tab3:
        render_pdf_input()

    with tab4:
        render_bulk_url_input()

    # Display added sources
    if st.session_state.sources:
        render_source_list()


def render_url_input():
    """Render single URL input"""
    url = st.text_input(
        "Enter article or webpage URL",
        placeholder="https://example.com/article",
        help="Paste a URL to extract content from"
    )

    col1, col2 = st.columns([1, 4])

    with col1:
        if st.button("➕ Add URL", type="primary", use_container_width=True):
            if url and validate_url(url):
                st.session_state.sources.append({
                    'type': 'url',
                    'content': url,
                    'added_at': datetime.now()
                })
                st.success("✅ URL added successfully!")
                st.rerun()
            elif url:
                st.error("❌ Please enter a valid URL")


def render_text_input():
    """Render text/LinkedIn content input"""
    text_content = st.text_area(
        "Paste text content or LinkedIn post",
        placeholder="Paste your content here...\n\nThis can be:\n- LinkedIn post/profile content\n- Article text\n- Any other text content",
        height=200
    )

    if st.button("➕ Add Text", type="primary"):
        if text_content.strip():
            st.session_state.sources.append({
                'type': 'text',
                'content': text_content,
                'added_at': datetime.now()
            })
            st.success("✅ Text content added!")
            st.rerun()
        else:
            st.error("❌ Please enter some text content")


def render_pdf_input():
    """Render PDF upload input"""
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=['pdf'],
        help="Upload a PDF document to extract content from"
    )

    if uploaded_file:
        st.info(f"📄 Selected: {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)")

        if st.button("➕ Add PDF", type="primary"):
            # Save PDF temporarily and add to sources
            temp_path = Path(f"temp_{uploaded_file.name}")
            with open(temp_path, 'wb') as f:
                f.write(uploaded_file.getbuffer())

            st.session_state.sources.append({
                'type': 'pdf',
                'content': str(temp_path),
                'filename': uploaded_file.name,
                'added_at': datetime.now()
            })
            st.success("✅ PDF added successfully!")
            st.rerun()


def render_bulk_url_input():
    """Render bulk URL input"""
    urls_text = st.text_area(
        "Enter multiple URLs (one per line)",
        placeholder="https://example.com/article1\nhttps://example.com/article2\nhttps://example.com/article3",
        height=150
    )

    if st.button("➕ Add All URLs", type="primary"):
        urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
        valid_urls = [url for url in urls if validate_url(url)]

        if valid_urls:
            for url in valid_urls:
                st.session_state.sources.append({
                    'type': 'url',
                    'content': url,
                    'added_at': datetime.now()
                })
            st.success(f"✅ Added {len(valid_urls)} URLs!")

            invalid_count = len(urls) - len(valid_urls)
            if invalid_count > 0:
                st.warning(f"⚠️ Skipped {invalid_count} invalid URLs")

            st.rerun()
        else:
            st.error("❌ No valid URLs found")


def render_source_list():
    """Render list of added sources"""
    st.markdown("### 📋 Added Sources")

    for i, source in enumerate(st.session_state.sources):
        with st.container():
            col1, col2, col3 = st.columns([1, 4, 1])

            with col1:
                if source['type'] == 'url':
                    st.markdown("🌐 **URL**")
                elif source['type'] == 'text':
                    st.markdown("📄 **Text**")
                elif source['type'] == 'pdf':
                    st.markdown("📑 **PDF**")

            with col2:
                if source['type'] == 'url':
                    st.text(source['content'])
                elif source['type'] == 'text':
                    st.text(source['content'][:100] + "..." if len(source['content']) > 100 else source['content'])
                elif source['type'] == 'pdf':
                    st.text(source['filename'])

            with col3:
                if st.button("🗑️", key=f"remove_{i}", help="Remove source"):
                    st.session_state.sources.pop(i)
                    st.rerun()

    # Clear all button
    if len(st.session_state.sources) > 1:
        if st.button("🗑️ Clear All Sources"):
            st.session_state.sources = []
            st.session_state.extracted_content = []
            st.rerun()


def render_generation_settings():
    """Render post generation settings"""
    st.markdown("## ⚙️ Step 2: Configure Post Generation")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        tone = st.selectbox(
            "Tone",
            options=[t.value for t in PostTone],
            format_func=lambda x: x.replace('_', ' ').title(),
            help="Select the tone for your post"
        )

    with col2:
        post_type = st.selectbox(
            "Post Type",
            options=[t.value for t in PostType],
            format_func=lambda x: x.replace('_', ' ').title(),
            help="Choose the type of post to generate"
        )

    with col3:
        num_variants = st.number_input(
            "Variants",
            min_value=1,
            max_value=5,
            value=1,
            help="Number of post variations to generate"
        )

    with col4:
        # Determine available models
        available_options = []

        # Check Claude
        if hasattr(config, 'ANTHROPIC_API_KEY') and config.ANTHROPIC_API_KEY:
            available_options.append("claude")

        # Check OpenAI
        if hasattr(config, 'OPENAI_API_KEY') and config.OPENAI_API_KEY:
            available_options.append("openai")

        # Check Gemini
        if hasattr(config, 'GOOGLE_API_KEY') and config.GOOGLE_API_KEY:
            available_options.append("gemini")

        # Fallback if no models available
        if not available_options:
            st.error("❌ No AI models configured!")
            st.info("Add at least one API key: ANTHROPIC_API_KEY, OPENAI_API_KEY, or GOOGLE_API_KEY")
            return None

        # Model selection
        model_choice = st.selectbox(
            "AI Model",
            options=available_options,
            format_func=lambda x: {
                "claude": "Claude (Anthropic)",
                "openai": "OpenAI GPT",
                "gemini": "Gemini 2.0 Pro (Google)"
            }.get(x, x.title()),
            index=2,
            help="Choose which AI model to use"
        )

        # Show model status
        if model_choice == 'claude':
            st.caption("🤖 Anthropic Claude")
        elif model_choice == 'openai':
            st.caption("🤖 OpenAI GPT")
        elif model_choice == 'gemini':
            st.caption("🤖 Google Gemini")

    # Advanced settings
    with st.expander("🎯 Advanced Settings"):
        col1, col2 = st.columns(2)

        with col1:
            target_audience = st.text_input(
                "Target Audience",
                placeholder="e.g., Supply chain managers, C-level executives",
                help="Specify your target audience for better content"
            )

            include_hashtags = st.checkbox(
                "Include default hashtags",
                value=True,
                help=f"Add these hashtags: {' '.join(config.DEFAULT_HASHTAGS)}"
            )

        with col2:
            additional_instructions = st.text_area(
                "Additional Instructions",
                placeholder="Any specific requirements or points to emphasize...",
                height=100,
                help="Provide any additional context or requirements"
            )

    # Return settings - FIXED: use model_choice instead of undefined 'model'
    return {
        'tone': tone,
        'post_type': post_type,
        'num_variants': num_variants,
        'model': model_choice,  # CORRETTO: usa model_choice
        'target_audience': target_audience,
        'include_hashtags': include_hashtags,
        'additional_instructions': additional_instructions
    }


def extract_all_content():
    """Extract content from all sources"""
    st.session_state.extracted_content = []

    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, source in enumerate(st.session_state.sources):
        status_text.text(f"Extracting from source {i + 1} of {len(st.session_state.sources)}...")
        progress_bar.progress((i + 1) / len(st.session_state.sources))

        try:
            if source['type'] == 'url':
                # Simple URL content extraction
                import requests
                from bs4 import BeautifulSoup

                response = requests.get(source['content'], timeout=10)
                soup = BeautifulSoup(response.content, 'html.parser')

                # Simple text extraction
                text = soup.get_text()
                lines = (line.strip() for line in text.splitlines())
                content = ' '.join(line for line in lines if line)[:2000]  # Limit to 2000 chars

                extracted = ExtractedContent(
                    source_type="web",
                    source=source['content'],
                    content=content,
                    title=soup.title.string if soup.title else "Web Content"
                )

                st.session_state.extracted_content.append(extracted)

            elif source['type'] == 'text':
                extracted = ExtractedContent(
                    source_type="text",
                    source="pasted_text",
                    content=source['content'],
                    title="Pasted Text"
                )
                st.session_state.extracted_content.append(extracted)

        except Exception as e:
            st.error(f"Error extracting source {i + 1}: {str(e)}")

    progress_bar.empty()
    status_text.empty()

    return len(st.session_state.extracted_content) > 0


def generate_posts(settings: Dict):
    """Generate posts based on settings"""
    generator = PostGenerator()

    # Prepare additional context
    additional_context = []
    if settings['target_audience']:
        additional_context.append(f"Target audience: {settings['target_audience']}")
    if settings['additional_instructions']:
        additional_context.append(settings['additional_instructions'])
    if settings['include_hashtags']:
        additional_context.append(f"Include these hashtags: {' '.join(config.DEFAULT_HASHTAGS)}")

    # Generate posts
    try:
        posts = generator.generate_sync(
            sources=st.session_state.extracted_content,
            tone=PostTone(settings['tone']),
            post_type=PostType(settings['post_type']),
            num_variants=settings['num_variants'],
            additional_context=' '.join(additional_context) if additional_context else None,
            preferred_model=settings['model']
        )

        st.session_state.generated_posts = posts
        return True

    except Exception as e:
        st.error(f"Error generating posts: {str(e)}")
        return False


def render_generated_posts():
    """Render generated posts for selection"""
    st.markdown("## 🎯 Step 3: Choose Your Post")

    if not st.session_state.generated_posts:
        return

    # View mode selector
    view_mode = st.radio(
        "View Mode",
        ["Side by Side", "One at a Time"],
        horizontal=True
    )

    if view_mode == "Side by Side":
        render_posts_grid()
    else:
        render_posts_carousel()

    # Show selected post actions
    if st.session_state.selected_post_index is not None:
        render_post_actions()


def render_posts_grid():
    """Render posts in a grid layout"""
    cols = st.columns(min(len(st.session_state.generated_posts), 3))

    for idx, (col, post) in enumerate(zip(cols, st.session_state.generated_posts[:3])):
        with col:
            # Check if this post is selected
            is_selected = st.session_state.selected_post_index == idx

            # Post container
            with st.container():
                if is_selected:
                    st.markdown(f"<div class='post-card post-card-selected'>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='post-card'>", unsafe_allow_html=True)

                # Variant header
                st.markdown(f"### Variant {idx + 1}")

                # Post content
                st.text_area(
                    "Content",
                    value=post.content,
                    height=300,
                    disabled=True,
                    key=f"post_content_{idx}"
                )

                # Character count
                st.markdown(
                    f"<div class='char-count'>{post.char_count}/{config.MAX_POST_LENGTH} characters</div>",
                    unsafe_allow_html=True
                )

                # Post stats
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Words", post.word_count)
                with col2:
                    st.metric("Hashtags", post.hashtag_count)
                with col3:
                    st.metric("Read Time", f"{estimate_read_time(post.content)}s")

                # Select button
                if st.button(
                    "✅ Select This" if not is_selected else "✓ Selected",
                    key=f"select_{idx}",
                    type="primary" if not is_selected else "secondary",
                    use_container_width=True
                ):
                    st.session_state.selected_post_index = idx
                    st.rerun()

                st.markdown("</div>", unsafe_allow_html=True)


def render_posts_carousel():
    """Render posts one at a time with navigation"""
    if 'current_post_index' not in st.session_state:
        st.session_state.current_post_index = 0

    idx = st.session_state.current_post_index
    post = st.session_state.generated_posts[idx]

    # Navigation
    col1, col2, col3 = st.columns([1, 8, 1])

    with col1:
        if st.button("◀", disabled=idx == 0):
            st.session_state.current_post_index -= 1
            st.rerun()

    with col2:
        st.markdown(f"### Variant {idx + 1} of {len(st.session_state.generated_posts)}")

    with col3:
        if st.button("▶", disabled=idx >= len(st.session_state.generated_posts) - 1):
            st.session_state.current_post_index += 1
            st.rerun()

    # Post content
    st.text_area(
        "Content",
        value=post.content,
        height=400,
        disabled=True,
        key=f"carousel_post_{idx}"
    )

    # Stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Characters", f"{post.char_count}/{config.MAX_POST_LENGTH}")
    with col2:
        st.metric("Words", post.word_count)
    with col3:
        st.metric("Hashtags", post.hashtag_count)
    with col4:
        st.metric("Model", post.model_used.split('-')[0].upper())

    # Select button
    is_selected = st.session_state.selected_post_index == idx
    if st.button(
        "✅ Select This Post" if not is_selected else "✓ Selected",
        type="primary" if not is_selected else "secondary",
        use_container_width=True
    ):
        st.session_state.selected_post_index = idx
        st.success("Post selected!")


# ===============================================
# MANUAL PUBLISH FUNCTIONS
# ===============================================

def prepare_manual_publish(content: str, post_metadata: dict = None) -> str:
    """Prepare content for manual publishing on LinkedIn"""
    formatted_content = content.strip()

    instructions = f"""
📋 LINKEDIN POST - READY TO PUBLISH
{'='*50}

{formatted_content}

{'='*50}
📝 MANUAL POSTING INSTRUCTIONS:

1. 📱 Go to LinkedIn.com (or open LinkedIn app)
2. 🖱️ Click "Start a post" button  
3. 📋 Copy and paste the content above
4. 👀 Review the post preview
5. 🎯 Adjust visibility if needed (Public/Connections)
6. 🚀 Click "Post" to publish

💡 TIPS FOR BETTER ENGAGEMENT:
• Post during business hours (9-10 AM, 2-3 PM)
• Respond to comments within the first hour
• Use relevant hashtags (already included)
• Tag relevant people or companies if appropriate

📊 POST STATISTICS:
• Characters: {len(formatted_content):,}
• Words: {len(formatted_content.split()):,}
• Hashtags: {len([tag for tag in formatted_content.split() if tag.startswith('#')]):,}
• Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    if post_metadata:
        instructions += f"""
• Tone: {post_metadata.get('tone', 'N/A').title()}
• Type: {post_metadata.get('post_type', 'N/A').replace('_', ' ').title()}
• Model: {post_metadata.get('model', 'N/A').upper()}
"""

    return instructions


def show_manual_publish_interface(content: str, original_post, post_metadata: dict):
    """Show the manual publish interface with copy-paste functionality"""
    st.markdown("## 📤 Manual Publishing")
    st.markdown("Your post is ready for manual publishing on LinkedIn!")

    # Create tabs for different views
    tab1, tab2, tab3 = st.tabs(["📋 Copy & Paste", "👁️ Preview", "📊 Analytics"])

    with tab1:
        st.markdown("### 📋 Ready to Copy")
        st.info("Select all text below and copy it (Ctrl+C or Cmd+C)")

        # Main content in a code block for easy copying
        st.code(content, language="text")

        # Copy button simulation
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("📋 Select Text Above ⬆️", use_container_width=True):
                st.success("✅ Text selected! Press Ctrl+C (or Cmd+C) to copy")

        # Quick instructions
        st.markdown("### 📝 Quick Steps")
        st.markdown("""
        1. **Copy the text above** (Ctrl+C or Cmd+C)
        2. **Go to LinkedIn.com**
        3. **Click "Start a post"**
        4. **Paste your content** (Ctrl+V or Cmd+V)
        5. **Click "Post"** to publish
        """)

    with tab2:
        st.markdown("### 👁️ LinkedIn Preview")
        st.markdown("This is how your post will look on LinkedIn:")

        # Simulate LinkedIn post appearance
        with st.container():
            st.markdown("""
            <div class='linkedin-preview'>
            """, unsafe_allow_html=True)

            # Mock profile section
            col1, col2 = st.columns([1, 8])
            with col1:
                st.markdown("👤")
            with col2:
                st.markdown("**Your Name**")
                st.caption("Your Title • Now")

            # Post content
            st.markdown("---")
            st.markdown(content)

            # Mock engagement section
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.caption("👍 Like")
            with col2:
                st.caption("💬 Comment")
            with col3:
                st.caption("🔄 Repost")

            st.markdown("</div>", unsafe_allow_html=True)

    with tab3:
        st.markdown("### 📊 Post Analytics")

        # Post statistics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Characters", len(content))
            if len(content) > 3000:
                st.warning("⚠️ Long post")
            elif len(content) > 1300:
                st.info("ℹ️ Medium post")
            else:
                st.success("✅ Short post")

        with col2:
            words = len(content.split())
            st.metric("Words", words)
            read_time = max(1, words // 200)
            st.caption(f"~{read_time} min read")

        with col3:
            hashtags = len([tag for tag in content.split() if tag.startswith('#')])
            st.metric("Hashtags", hashtags)
            if hashtags < 3:
                st.warning("Consider more hashtags")
            elif hashtags > 7:
                st.warning("Too many hashtags")
            else:
                st.success("Good hashtag count")

        with col4:
            mentions = len([tag for tag in content.split() if tag.startswith('@')])
            st.metric("Mentions", mentions)

        # Engagement prediction
        st.markdown("### 🎯 Engagement Prediction")

        # Simple scoring algorithm
        score = 0
        feedback = []

        # Length score
        if 500 <= len(content) <= 1500:
            score += 20
            feedback.append("✅ Good length for engagement")
        elif len(content) < 300:
            score += 10
            feedback.append("⚠️ Might be too short")
        else:
            score += 15
            feedback.append("ℹ️ Long posts can work for thought leadership")

        # Hashtag score
        if 3 <= hashtags <= 5:
            score += 20
            feedback.append("✅ Optimal hashtag count")
        elif hashtags > 0:
            score += 10
            feedback.append("ℹ️ Consider 3-5 hashtags for best reach")

        # Question score
        if '?' in content:
            score += 15
            feedback.append("✅ Contains question - good for engagement")
        else:
            feedback.append("💡 Consider adding a question to drive comments")

        # Emoji score
        if any(ord(c) > 127000 for c in content):
            score += 10
            feedback.append("✅ Contains emojis - good for visibility")

        # Call-to-action score
        cta_words = ['comment', 'share', 'thoughts', 'opinion', 'experience', 'agree', 'think']
        if any(word in content.lower() for word in cta_words):
            score += 15
            feedback.append("✅ Contains call-to-action")

        # Display score
        col1, col2 = st.columns([1, 2])

        with col1:
            if score >= 70:
                st.success(f"🎯 Engagement Score: {score}/100")
                st.success("High engagement potential!")
            elif score >= 50:
                st.warning(f"🎯 Engagement Score: {score}/100")
                st.info("Good engagement potential")
            else:
                st.error(f"🎯 Engagement Score: {score}/100")
                st.warning("Consider improvements")

        with col2:
            st.markdown("**Feedback:**")
            for item in feedback:
                st.markdown(f"• {item}")

    # Action buttons
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("💾 Save as Draft", use_container_width=True):
            save_post_as_draft(content, original_post)

    with col2:
        if st.button("📅 Schedule for Later", use_container_width=True):
            save_post_and_redirect_to_schedule(content, original_post)

    with col3:
        if st.button("✅ Mark as Published", use_container_width=True):
            mark_as_manually_published(content, original_post, post_metadata)

    with col4:
        if st.button("🔙 Back to Edit", use_container_width=True):
            st.session_state.show_manual_publish = False
            st.rerun()


def mark_as_manually_published(content: str, original_post, post_metadata: dict):
    """Mark a post as manually published and save to database"""
    try:
        # Extract hashtags
        hashtags = [tag for tag in content.split() if tag.startswith('#')]

        # Save to database as published
        post_id = db.create_post(
            content=content,
            post_type=getattr(original_post, 'post_type', 'informative'),
            tone=getattr(original_post, 'tone', 'professional'),
            sources=getattr(original_post, 'sources_used', []),
            model_used=getattr(original_post, 'model_used', None),
            generation_temperature=post_metadata.get('temperature', config.LLM_TEMPERATURE),
            prompt_tokens=post_metadata.get('prompt_tokens', 0),
            completion_tokens=post_metadata.get('completion_tokens', 0),
            hashtags=hashtags,
            status='published'  # Mark as published
        )

        # Update published timestamp
        db.update_post(
            post_id=post_id,
            published_at=datetime.now(),
            linkedin_post_url="manual_publish"  # Indicator for manual publish
        )

        st.success("✅ Post marked as published!")
        st.balloons()

        time.sleep(2)

        # Clear state and redirect
        st.session_state.sources = []
        st.session_state.extracted_content = []
        st.session_state.generated_posts = []
        st.session_state.selected_post_index = None
        st.session_state.show_manual_publish = False

        # Redirect to main page
        st.session_state.show_success = "Post marked as published manually!"
        st.switch_page("main.py")

    except Exception as e:
        st.error(f"Error marking post as published: {str(e)}")


def render_post_actions():
    """Render actions for selected post - UPDATED WITH MANUAL PUBLISH"""
    st.markdown("---")
    st.markdown("## 🎬 Step 4: Finalize Your Post")

    selected_post = st.session_state.generated_posts[st.session_state.selected_post_index]

    # Check if we should show manual publish interface
    if st.session_state.get('show_manual_publish', False):
        # Get post metadata
        post_metadata = {
            'tone': selected_post.tone,
            'post_type': selected_post.post_type,
            'model': selected_post.model_used.split('-')[0] if selected_post.model_used else 'Unknown',
            'temperature': selected_post.metadata.get('temperature', config.LLM_TEMPERATURE)
        }

        edited_content = st.session_state.get('edited_content', selected_post.content)
        show_manual_publish_interface(edited_content, selected_post, post_metadata)
        return

    # Regular edit interface
    edited_content = st.text_area(
        "Edit your post (optional)",
        value=selected_post.content,
        height=200,
        help="Make any final adjustments to your post"
    )

    # Store edited content in session state
    st.session_state.edited_content = edited_content

    # Character count for edited version
    st.markdown(
        f"<div class='char-count'>{len(edited_content)}/{config.MAX_POST_LENGTH} characters</div>",
        unsafe_allow_html=True
    )

    # Action buttons
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("💾 Save as Draft", type="primary", use_container_width=True):
            save_post_as_draft(edited_content, selected_post)

    with col2:
        if st.button("📅 Schedule Post", use_container_width=True):
            save_post_and_redirect_to_schedule(edited_content, selected_post)

    with col3:
        if st.button("📤 Publish Manually", use_container_width=True, help="Get copy-paste ready content"):
            st.session_state.show_manual_publish = True
            st.rerun()

    with col4:
        if st.button("📋 Quick Copy", use_container_width=True):
            st.code(edited_content)
            st.info("Text ready to copy - press Ctrl+C (or Cmd+C)")


def save_post_as_draft(content: str, original_post):
    """Save post as draft in database - FINAL FIX"""
    try:
        # Extract hashtags from content
        hashtags = [tag for tag in content.split() if tag.startswith('#')]

        # Access GeneratedPost attributes safely
        post_type = getattr(original_post, 'post_type', 'informative')
        tone = getattr(original_post, 'tone', 'professional')
        sources_used = getattr(original_post, 'sources_used', [])
        model_used = getattr(original_post, 'model_used', None)

        # Get metadata safely
        metadata = getattr(original_post, 'metadata', {})
        temperature = metadata.get('temperature', config.LLM_TEMPERATURE) if isinstance(metadata, dict) else config.LLM_TEMPERATURE
        prompt_tokens = metadata.get('prompt_tokens', 0) if isinstance(metadata, dict) else 0
        completion_tokens = metadata.get('completion_tokens', 0) if isinstance(metadata, dict) else 0

        # Save to database - Now returns only ID
        post_id = db.create_post(
            content=content,
            post_type=post_type,
            tone=tone,
            sources=sources_used,
            model_used=model_used,
            generation_temperature=temperature,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            hashtags=hashtags,
            status='draft'
        )

        st.success(f"✅ Post saved as draft successfully! (ID: {post_id})")
        time.sleep(1)

        # Clear state and redirect
        st.session_state.sources = []
        st.session_state.extracted_content = []
        st.session_state.generated_posts = []
        st.session_state.selected_post_index = None

        # Set success message for main page
        st.session_state.show_success = "Post saved as draft!"
        st.switch_page("main.py")

    except Exception as e:
        st.error(f"Error saving post: {str(e)}")
        import traceback
        st.error(f"Traceback: {traceback.format_exc()}")


def save_post_and_redirect_to_schedule(content: str, original_post):
    """Save post and redirect to schedule page - FINAL FIX"""
    try:
        # Extract hashtags from content
        hashtags = [tag for tag in content.split() if tag.startswith('#')]

        # Access GeneratedPost attributes safely
        post_type = getattr(original_post, 'post_type', 'informative')
        tone = getattr(original_post, 'tone', 'professional')
        sources_used = getattr(original_post, 'sources_used', [])
        model_used = getattr(original_post, 'model_used', None)

        # Get metadata safely
        metadata = getattr(original_post, 'metadata', {})
        temperature = metadata.get('temperature', config.LLM_TEMPERATURE) if isinstance(metadata, dict) else config.LLM_TEMPERATURE
        prompt_tokens = metadata.get('prompt_tokens', 0) if isinstance(metadata, dict) else 0
        completion_tokens = metadata.get('completion_tokens', 0) if isinstance(metadata, dict) else 0

        # Save to database - Now returns only ID
        post_id = db.create_post(
            content=content,
            post_type=post_type,
            tone=tone,
            sources=sources_used,
            model_used=model_used,
            generation_temperature=temperature,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            hashtags=hashtags,
            status='draft'
        )

        # Store post ID for schedule page
        st.session_state.post_to_schedule = post_id

        # Clear generation state
        st.session_state.sources = []
        st.session_state.extracted_content = []
        st.session_state.generated_posts = []
        st.session_state.selected_post_index = None

        # Redirect to schedule page
        st.switch_page("pages/2_🚀_Schedule_&_Automation.py")

    except Exception as e:
        st.error(f"Error saving post: {str(e)}")
        import traceback
        st.error(f"Traceback: {traceback.format_exc()}")


def main():
    """Main function for create post page"""
    init_page_state()
    render_header()

    # Step 1: Source Input
    render_source_input()

    if not st.session_state.sources:
        st.info("👆 Add at least one content source to get started")
        return

    # Step 2: Generation Settings
    settings = render_generation_settings()

    if settings is None:  # No models available
        return

    # Generate button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(
            "🚀 Generate Posts",
            type="primary",
            use_container_width=True,
            disabled=st.session_state.generation_in_progress
        ):
            st.session_state.generation_in_progress = True

            # Extract content
            with st.spinner("📊 Extracting content from sources..."):
                if extract_all_content():
                    # Generate posts
                    with st.spinner(f"🤖 Generating {settings['num_variants']} post variants with {settings['model'].upper()}..."):
                        if generate_posts(settings):
                            st.success("✅ Posts generated successfully!")
                            st.session_state.generation_in_progress = False
                            st.rerun()
                        else:
                            st.session_state.generation_in_progress = False
                else:
                    st.error("Failed to extract content from sources")
                    st.session_state.generation_in_progress = False

    # Step 3: Display generated posts
    if st.session_state.generated_posts:
        render_generated_posts()


if __name__ == "__main__":
    main()