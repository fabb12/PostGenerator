"""
Create Post Page - Generate LinkedIn posts from various sources
"""

import streamlit as st
import asyncio
from datetime import datetime
from pathlib import Path
import sys
import time
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
            value=3,
            help="Number of post variations to generate"
        )
    
    with col4:
        model = st.selectbox(
            "AI Model",
            options=['claude', 'openai'],
            index=0 if config.ANTHROPIC_API_KEY else 1,
            help="Choose which AI model to use"
        )
    
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
    
    return {
        'tone': tone,
        'post_type': post_type,
        'num_variants': num_variants,
        'model': model,
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

                from src.content_extractor import ExtractedContent
                extracted = ExtractedContent(
                    source_type="web",
                    source=source['content'],
                    content=content,
                    title=soup.title.string if soup.title else "Web Content"
                )

                st.session_state.extracted_content.append(extracted)

            elif source['type'] == 'text':
                from src.content_extractor import ExtractedContent
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


def render_post_actions():
    """Render actions for selected post"""
    st.markdown("---")
    st.markdown("## 🎬 Step 4: Finalize Your Post")
    
    selected_post = st.session_state.generated_posts[st.session_state.selected_post_index]
    
    # Editable content
    edited_content = st.text_area(
        "Edit your post (optional)",
        value=selected_post.content,
        height=200,
        help="Make any final adjustments to your post"
    )
    
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
        if st.button("📤 Publish Now", use_container_width=True):
            st.warning("Direct publishing will be available soon!")
    
    with col4:
        if st.button("📋 Copy to Clipboard", use_container_width=True):
            st.code(edited_content)
            st.info("Text selected - press Ctrl+C (or Cmd+C) to copy")


def save_post_as_draft(content: str, original_post):
    """Save post as draft in database"""
    try:
        # Extract hashtags
        hashtags = [tag for tag in content.split() if tag.startswith('#')]
        
        # Save to database
        post = db.create_post(
            content=content,
            post_type=original_post.post_type,
            tone=original_post.tone,
            sources=original_post.sources_used,
            model_used=original_post.model_used,
            generation_temperature=original_post.metadata.get('temperature', config.LLM_TEMPERATURE),
            prompt_tokens=original_post.metadata.get('prompt_tokens', 0),
            completion_tokens=original_post.metadata.get('completion_tokens', 0),
            hashtags=hashtags,
            status='draft'
        )
        
        st.success("✅ Post saved as draft successfully!")
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


def save_post_and_redirect_to_schedule(content: str, original_post):
    """Save post and redirect to schedule page"""
    try:
        # Save as draft first
        hashtags = [tag for tag in content.split() if tag.startswith('#')]
        
        post = db.create_post(
            content=content,
            post_type=original_post.post_type,
            tone=original_post.tone,
            sources=original_post.sources_used,
            model_used=original_post.model_used,
            generation_temperature=original_post.metadata.get('temperature', config.LLM_TEMPERATURE),
            prompt_tokens=original_post.metadata.get('prompt_tokens', 0),
            completion_tokens=original_post.metadata.get('completion_tokens', 0),
            hashtags=hashtags,
            status='draft'
        )
        
        # Store post ID for schedule page
        st.session_state.post_to_schedule = post.id
        
        # Clear generation state
        st.session_state.sources = []
        st.session_state.extracted_content = []
        st.session_state.generated_posts = []
        st.session_state.selected_post_index = None
        
        # Redirect to schedule page
        st.switch_page("pages/2_📅_Schedule.py")
        
    except Exception as e:
        st.error(f"Error saving post: {str(e)}")


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
                    with st.spinner(f"🤖 Generating {settings['num_variants']} post variants..."):
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
