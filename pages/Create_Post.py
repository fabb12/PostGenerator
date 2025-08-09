# pages/1_📝_Create_Post.py
"""
Create Post Page - Generate LinkedIn posts from various sources
UPDATED with AUTOMATIC link/image handling and direct publishing.
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
from src.content_extractor import ExtractedContent, extract_content
from src.post_generator import PostGenerator, PostTone, PostType
from src.database import db
from utils.helpers import validate_url
from src.linkedin_connector import LinkedInPublisher
from src.encryption import decrypt_password

# Page config
st.set_page_config(
    page_title="Create Post - LinkedIn Generator",
    page_icon="📝",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    /* ... (il tuo CSS rimane invariato) ... */
</style>
""", unsafe_allow_html=True)


def init_page_state():
    """Initialize page-specific session state."""
    defaults = {
        'sources': [], 'extracted_content': [], 'generated_posts': [],
        'selected_post_index': None, 'generation_in_progress': False,
        'edited_content': "", 'url_input': ""
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_header():
    """Render page header."""
    st.title("📝 Create New Post")
    st.markdown("Genera contenuti LinkedIn coinvolgenti e pubblicali direttamente.")


def render_source_input():
    """Render source input section."""
    st.markdown("## 📥 Step 1: Aggiungi Fonti di Contenuto")

    with st.expander("📚 Oppure, scegli da una Fonte Salvata"):
        try:
            saved_sources = db.get_active_automation_sources()
        except Exception as e:
            st.error(f"Impossibile caricare fonti: {e}");
            saved_sources = []

        if not saved_sources:
            st.info("Nessuna fonte salvata. Aggiungine una in 'Schedule & Automation'.")
        else:
            cols = st.columns(3)
            for i, source in enumerate(saved_sources):
                if cols[i % 3].button(source.url, key=f"src_{source.id}", use_container_width=True):
                    st.session_state.url_input = source.url;
                    st.rerun()

    tab1, tab2, tab3 = st.tabs(["🌐 Web URL", "📄 Testo", "📑 PDF Upload"])
    with tab1:
        render_url_input()
    with tab2:
        render_text_input()
    with tab3:
        render_pdf_input()

    if st.session_state.sources: render_source_list()


def render_url_input():
    """Render single URL input."""
    url_value = st.text_input("Inserisci URL", key="url_input_widget", value=st.session_state.url_input)
    if st.button("➕ Aggiungi URL", type="primary"):
        if url_value and validate_url(url_value):
            st.session_state.sources.append({'type': 'url', 'content': url_value})
            st.session_state.url_input = ""
            st.rerun()
        else:
            st.error("❌ URL non valido.")


def render_text_input():
    """Render text input."""
    text_content = st.text_area("Incolla testo", height=200, key="text_widget")
    if st.button("➕ Aggiungi Testo", type="primary"):
        if text_content.strip():
            st.session_state.sources.append({'type': 'text', 'content': text_content})
            st.rerun()
        else:
            st.error("❌ Testo vuoto.")


def render_pdf_input():
    """Render PDF upload input."""
    uploaded_file = st.file_uploader("Scegli un file PDF", type=['pdf'], key="pdf_widget")
    if uploaded_file and st.button("➕ Aggiungi PDF", type="primary"):
        temp_dir = Path("temp_uploads");
        temp_dir.mkdir(exist_ok=True)
        temp_path = temp_dir / uploaded_file.name
        with open(temp_path, 'wb') as f: f.write(uploaded_file.getbuffer())
        st.session_state.sources.append({'type': 'pdf', 'content': str(temp_path), 'filename': uploaded_file.name})
        st.rerun()


def render_source_list():
    """Render list of added sources."""
    st.markdown("### 📋 Fonti per Questo Post")
    for i, source in enumerate(st.session_state.sources):
        with st.container(border=True):
            type_map = {'url': '🌐 URL', 'text': '📄 Testo', 'pdf': '📑 PDF'}
            display_text = source.get('filename') or source.get('content', '')
            st.markdown(f"**{type_map.get(source['type'], 'Fonte')}**: `{display_text[:80]}...`")
            if st.button("🗑️ Rimuovi", key=f"remove_{i}"):
                st.session_state.sources.pop(i)
                st.rerun()


def render_generation_settings():
    """Render post generation settings."""
    st.markdown("## ⚙️ Step 2: Configura la Generazione")
    col1, col2, col3, col4 = st.columns(4)
    with col1: tone = st.selectbox("Tono", [t.value for t in PostTone], format_func=str.title)
    with col2: post_type = st.selectbox("Tipo Post", [p.value for p in PostType],
                                        format_func=lambda x: x.replace('_', ' ').title())
    with col3: num_variants = st.number_input("Varianti", 1, 5, 1)
    with col4:
        available = [name for name, conf in config.LLM_MODELS.items() if conf['available']]
        if not available:
            st.error("Nessun modello AI configurato!")
            return None
        model_choice = st.selectbox("Modello AI", available, format_func=str.title)

    with st.expander("🎯 Impostazioni Avanzate"):
        target_audience = st.text_input("Pubblico", placeholder="Es. Manager della logistica")
        additional_instructions = st.text_area("Istruzioni", placeholder="Enfatizza la sostenibilità...")

    return {
        'tone': tone, 'post_type': post_type, 'num_variants': num_variants, 'model': model_choice,
        'target_audience': target_audience, 'additional_instructions': additional_instructions
    }


def run_generation_process(settings: Dict):
    """Handles the full content extraction and post generation process."""
    st.session_state.generation_in_progress = True

    with st.spinner("Estrazione contenuto e generazione post..."):
        st.session_state.extracted_content = [extract_content(s['content']) for s in st.session_state.sources]
        if not any(c.is_valid for c in st.session_state.extracted_content):
            st.error("Estrazione del contenuto fallita. Controlla le fonti.")
            st.session_state.generation_in_progress = False
            return

        link_source = next((c for c in st.session_state.extracted_content if c.source_type == 'web' and c.is_valid),
                           None)
        link_url = link_source.source if link_source else None
        image_description = f"un'immagine di anteprima relativa a: '{link_source.title}'" if (
                    link_source and link_source.image_url) else None

        generator = PostGenerator()
        try:
            posts = generator.generate_sync(
                sources=[c for c in st.session_state.extracted_content if c.is_valid],
                tone=PostTone(settings['tone']),
                post_type=PostType(settings['post_type']),
                num_variants=settings['num_variants'],
                additional_context=f"Audience: {settings['target_audience']}\nInstructions: {settings['additional_instructions']}",
                preferred_model=settings['model'],
                link_url=link_url,
                image_description=image_description
            )
            st.session_state.generated_posts = posts
            st.session_state.selected_post_index = None
            st.success("✅ Post generati!")
        except Exception as e:
            st.error(f"Errore durante la generazione: {e}")
            import traceback;
            traceback.print_exc()

    st.session_state.generation_in_progress = False


def render_generated_posts():
    """Render generated posts for selection."""
    st.markdown("## 🎯 Step 3: Scegli la Versione Migliore")
    for idx, post in enumerate(st.session_state.generated_posts):
        is_selected = (st.session_state.selected_post_index == idx)
        with st.container(border=True):
            st.text_area(
                label=f"Variante {idx + 1} ({post.model_used})",
                value=post.content,
                height=150,
                disabled=True,
                key=f"post_content_{idx}",
                label_visibility="collapsed"
            )
            if st.button("✅ Scegli questa", key=f"select_{idx}", type="primary" if not is_selected else "secondary"):
                st.session_state.selected_post_index = idx
                st.session_state.edited_content = post.content


def render_post_actions():
    """Render final actions for the selected post."""
    st.markdown("---")
    st.markdown("### 🎬 Step 4: Finalizza e Pubblica")

    selected_post = st.session_state.generated_posts[st.session_state.selected_post_index]

    with st.container(border=True):
        st.markdown("#### Anteprima Media da Condividere")
        link_source = next((c for c in st.session_state.extracted_content if c.source_type == 'web' and c.is_valid), None)
        if link_source:
            st.markdown(f"**Link:** `{link_source.source}`")
            if link_source.image_url:
                st.markdown("**Immagine di Anteprima:**")
                st.image(link_source.image_url, width=300, caption="Questa immagine verrà usata da LinkedIn per l'anteprima.")
            else:
                st.info("Nessuna immagine di anteprima trovata. LinkedIn potrebbe sceglierne una automaticamente.")
        else:
            st.info("Nessun link da condividere. Verrà pubblicato un post di solo testo.")

    edited_content = st.text_area(
        "Modifica il testo del post finale",
        value=st.session_state.edited_content,
        height=200, key="final_editor"
    )
    st.session_state.edited_content = edited_content
    st.caption(f"Caratteri: {len(edited_content)}/{config.MAX_POST_LENGTH}")

    # --- Account Selection ---
    accounts = db.get_linkedin_accounts()
    if not accounts:
        st.error("Nessun account LinkedIn configurato. Vai su Impostazioni per aggiungerne uno.")
        return

    account_options = {acc.id: acc.email for acc in accounts}
    active_account = db.get_active_linkedin_account()
    default_index = list(account_options.keys()).index(active_account.id) if active_account else 0

    selected_account_id = st.selectbox(
        "Pubblica con l'account:",
        options=list(account_options.keys()),
        format_func=lambda x: account_options[x],
        index=default_index
    )

    # --- Action Buttons ---
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("💾 Salva Bozza", use_container_width=True):
            save_post_action(edited_content, selected_post, 'draft')
    with col2:
        if st.button("📅 Programma", use_container_width=True):
            save_post_action(edited_content, selected_post, 'schedule')
    with col3:
        if st.button("🚀 Pubblica Ora", type="primary", use_container_width=True):
            publish_post_action(edited_content, selected_post, selected_account_id)


def save_post_action(content: str, original_post, action_type: str):
    """Save post as draft or for scheduling."""
    if not content.strip(): st.error("Il contenuto non può essere vuoto."); return
    try:
        post_id = db.create_post(
            content=content, post_type=original_post.post_type, tone=original_post.tone,
            sources=[s.source for s in st.session_state.extracted_content],
            model_used=original_post.model_used, status='draft'
        )
        if action_type == 'draft':
            st.success("✅ Post salvato come bozza!");
            time.sleep(1);
            st.rerun()
        elif action_type == 'schedule':
            st.session_state.post_to_schedule = post_id
            st.success("✅ Post pronto per la schedulazione...");
            time.sleep(1)
            st.switch_page("pages/2_🚀_Schedule_&_Automation.py")
    except Exception as e:
        st.error(f"Errore nel salvataggio: {e}")


def publish_post_action(content: str, original_post, account_id: int):
    """Handles the direct publishing logic."""
    if not content.strip():
        st.error("Il contenuto non può essere vuoto.")
        return

    account = db.get_linkedin_account(account_id)
    if not account:
        st.error(f"Account con ID {account_id} non trovato.")
        return

    link_source = next((c for c in st.session_state.extracted_content if c.source_type == 'web' and c.is_valid), None)
    link_to_share = link_source.source if link_source else None

    with st.spinner(f"Pubblicazione su LinkedIn con l'account {account.email}..."):
        try:
            password = decrypt_password(account.encrypted_password)
            publisher = LinkedInPublisher(email=account.email, password=password)

            result = asyncio.run(publisher.publish_post(post_content=content, link_to_share=link_to_share))

            if result.success:
                save_published_post(content, original_post, result)
                st.success("✅ Post pubblicato con successo!")
                if result.post_url:
                    st.link_button("Visualizza su LinkedIn", result.post_url)
                st.balloons()
                time.sleep(2)
                init_page_state()
                st.rerun()
            else:
                st.error(f"❌ Pubblicazione fallita: {result.error_message}")
        except Exception as e:
            st.error(f"Errore imprevisto durante la pubblicazione: {e}")
            import traceback
            traceback.print_exc()


def save_published_post(content, original_post, result):
    """Saves the details of a successfully published post to the database."""
    # ### <<< MODIFICA CHIAVE 3: Salvataggio corretto delle fonti ###
    # Salva le fonti in un formato strutturato, non solo una lista di stringhe
    sources_to_save = [
        {'type': s.source_type, 'source': s.source, 'title': s.title}
        for s in st.session_state.extracted_content if s.is_valid
    ]
    db.create_post(
        content=content,
        status='published',
        published_at=datetime.utcnow(),
        post_type=original_post.post_type,
        tone=original_post.tone,
        model_used=original_post.model_used,
        linkedin_post_id=result.post_id,
        linkedin_post_url=result.post_url,
        sources=sources_to_save
    )


def main():
    """Main function for the create post page."""
    init_page_state()
    render_header()
    render_source_input()

    if not st.session_state.sources:
        st.info("👆 Aggiungi almeno una fonte di contenuto per iniziare.");
        return

    settings = render_generation_settings()
    if settings is None: return

    if st.button("🚀 Genera Post", type="primary", use_container_width=True,
                 disabled=st.session_state.generation_in_progress):
        run_generation_process(settings)

    if st.session_state.generated_posts:
        render_generated_posts()
        if st.session_state.selected_post_index is not None:
            render_post_actions()


if __name__ == "__main__":
    main()