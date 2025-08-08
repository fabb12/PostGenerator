# PostGenerator/pages/2_🚀_Schedule_&_Automation.py
"""
Unified page for Scheduling, Automation, and Publishing.
This page combines all post-creation workflows into a single,
streamlined interface with tabs.
"""

import streamlit as st
import pandas as pd
import asyncio
from datetime import datetime, time, timedelta
import pytz

from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config import config
from src.database import db
from src.linkedin_connector import LinkedInScheduler
from src.automation_manager import AutomationManager
from utils.helpers import format_datetime, validate_url, get_optimal_posting_times

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Schedule & Automation",
    page_icon="🚀",
    layout="wide"
)

# --- CUSTOM CSS (preso dal tuo esempio) ---
st.markdown("""
<style>
    .automation-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        margin-bottom: 1rem;
    }
    .source-item {
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .status-active { color: #28a745; font-weight: bold; }
    .status-inactive { color: #dc3545; font-weight: bold; }
</style>
""", unsafe_allow_html=True)


# --- SESSION STATE INITIALIZATION ---
def init_session_state():
    # Per lo scheduling manuale
    if 'selected_post_id_for_scheduling' not in st.session_state:
        st.session_state.selected_post_id_for_scheduling = None
    if 'schedule_date' not in st.session_state:
        st.session_state.schedule_date = datetime.now().date() + timedelta(days=1)
    if 'schedule_time' not in st.session_state:
        st.session_state.schedule_time = time(9, 0)
    # Per l'automazione
    if 'automation_enabled' not in st.session_state:
        # Qui potresti leggere un valore salvato nel DB o in un file di config
        st.session_state.automation_enabled = False
    if 'auto_publish' not in st.session_state:
        st.session_state.auto_publish = False


init_session_state()

# --- PAGE HEADER ---
st.title("🚀 Schedule & Automation")
st.markdown(
    "Gestisci la tua pipeline di contenuti: dalle bozze alla programmazione, fino all'automazione e pubblicazione.")

# --- TABS FOR DIFFERENT ACTIONS ---
tab1, tab2, tab3 = st.tabs(["📅 Scheduling", "🤖 Automation", "▶️ Publishing Queue"])

# ==============================================================================
# TAB 1: SCHEDULING - Gestione bozze e programmazione manuale
# ==============================================================================
with tab1:
    st.header("📅 Scheduling: Programma le tue Bozze")


    def render_scheduling_interface(post_id):
        post = db.get_post(post_id)
        if not post:
            st.error("Post non trovato.");
            st.session_state.selected_post_id_for_scheduling = None;
            st.rerun()
            return

        st.markdown(f"### 📝 Programmazione per Post ID: {post.id}")
        st.text_area("Contenuto", value=post.content, height=150, disabled=True)

        col1, col2 = st.columns(2)
        with col1:
            schedule_date = st.date_input("Data", value=st.session_state.schedule_date, min_value=datetime.now().date(),
                                          key="sched_date")
            schedule_time = st.time_input("Ora", value=st.session_state.schedule_time, key="sched_time")

        with col2:
            st.markdown("💡 **Orari Suggeriti**")
            for t in get_optimal_posting_times():
                if st.button(f"🕐 {t}", key=f"time_{t}"):
                    h, m = map(int, t.split(':'));
                    st.session_state.schedule_time = time(h, m);
                    st.rerun()

        scheduled_dt_naive = datetime.combine(schedule_date, st.session_state.schedule_time)
        tz = pytz.timezone(config.TIMEZONE)
        scheduled_dt_aware = tz.localize(scheduled_dt_naive)

        if scheduled_dt_aware > datetime.now(tz):
            st.success(f"Programmato per: {format_datetime(scheduled_dt_aware)}")
            if st.button("🚀 Conferma Programmazione", type="primary", use_container_width=True):
                utc_dt = scheduled_dt_aware.astimezone(pytz.utc).replace(tzinfo=None)
                db.schedule_post(post.id, utc_dt)
                st.success("✅ Post programmato!");
                st.session_state.selected_post_id_for_scheduling = None;
                st.rerun()
        else:
            st.error("⚠️ L'orario di programmazione non può essere nel passato.")

        if st.button("❌ Annulla"): st.session_state.selected_post_id_for_scheduling = None; st.rerun()


    draft_posts = db.get_posts(status='draft')
    if st.session_state.selected_post_id_for_scheduling:
        render_scheduling_interface(st.session_state.selected_post_id_for_scheduling)
    elif not draft_posts:
        st.info("Non ci sono bozze da programmare. Creane una dalla pagina 'Create Post'.")
    else:
        st.markdown("Seleziona una bozza da programmare:")
        for post in draft_posts:
            with st.container(border=True):
                col1, col2 = st.columns([4, 1])
                col1.text(post.content[:150] + "...")
                if col2.button("📅 Programma", key=f"sched_{post.id}", use_container_width=True):
                    st.session_state.selected_post_id_for_scheduling = post.id;
                    st.rerun()

# ==============================================================================
# TAB 2: AUTOMATION - Gestione completa dell'automazione
# ==============================================================================
with tab2:
    st.header("🤖 Automation: Generazione Automatica di Post")

    # --- Dashboard di Controllo Automazione ---
    with st.container():
        st.markdown('<div class="automation-card">', unsafe_allow_html=True)
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("### 🚀 Automazione Giornaliera")
            st.markdown(
                "- **Controlla** le fonti per nuovo contenuto.\n- **Genera** nuovi post con AI.\n- **Programma** i post negli orari ottimali.")
        with col2:
            st.session_state.automation_enabled = st.toggle("Abilita Automazione",
                                                            value=st.session_state.automation_enabled)
            st.session_state.auto_publish = st.toggle("Pubblica Automaticamente", value=st.session_state.auto_publish,
                                                      disabled=not st.session_state.automation_enabled)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- Impostazioni di Automazione (in un expander) ---
    with st.expander("⚙️ Impostazioni Dettagliate Automazione"):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Programmazione")
            st.multiselect("Orari di controllo fonti", options=["06:00", "09:00", "12:00", "15:00"], default=["09:00"],
                           help="Quando controllare le fonti per nuovo contenuto.")
            st.selectbox("Frequenza pubblicazione", options=["Ogni giorno", "Ogni 2 giorni", "2 volte a settimana"],
                         index=1)
        with col2:
            st.markdown("#### Configurazione Post")
            st.selectbox("Tone predefinito", options=config.TONE_OPTIONS,
                         index=config.TONE_OPTIONS.index(config.AUTOMATION_DEFAULT_TONE))
            st.selectbox("Tipo post predefinito", options=config.POST_TYPE_OPTIONS,
                         index=config.POST_TYPE_OPTIONS.index(config.AUTOMATION_DEFAULT_POST_TYPE))
        if st.button("💾 Salva Impostazioni"):
            st.success("Impostazioni salvate! (Funzionalità in sviluppo)")

    # --- Gestione Fonti ---
    st.subheader("📥 Fonti per Automazione")
    with st.form("add_source_form_auto"):
        new_source_url = st.text_input("Aggiungi URL fonte (blog, feed, ecc.)", placeholder="https://example.com/blog")
        if st.form_submit_button("➕ Aggiungi Fonte"):
            if validate_url(new_source_url):
                if db.add_automation_source(url=new_source_url):
                    st.success(f"Fonte aggiunta: {new_source_url}")
                else:
                    st.error("Fonte già esistente.")
            else:
                st.error("URL non valido.")

    sources = db.get_active_automation_sources()
    if not sources:
        st.info("Nessuna fonte configurata. Aggiungine una per iniziare.")
    else:
        for source in sources:
            with st.container(border=True):
                col1, col2, col3 = st.columns([4, 2, 1])
                col1.markdown(f"**{source.url}**")
                col2.caption(
                    f"Ultimo check: {format_datetime(source.last_checked_at, 'short') if source.last_checked_at else 'Mai'}")
                if col3.button("🗑️", key=f"del_auto_{source.id}"): db.delete_automation_source(source.id); st.rerun()

    # --- Controlli Manuali ---
    st.subheader("🎮 Controlli Manuali")
    force_run = st.checkbox("Forza il controllo su tutte le fonti (ignora l'intervallo di 24h)", key="force_run_auto")
    if st.button("🔄 Esegui Automazione Ora", type="primary", use_container_width=True):
        if not st.session_state.automation_enabled:
            st.warning("L'automazione è disabilitata. Abilitala dal pannello di controllo qui sopra per procedere.")
        else:
            with st.spinner("Avvio dell'automazione..."):
                manager = AutomationManager()
                summary = manager.run(force_run=force_run)
                st.success("Automazione completata!")
                st.metric("Nuovi Post Programmati", summary.get('scheduled', 0))
                with st.expander("Visualizza Log"): st.json(summary)

# ==============================================================================
# TAB 3: PUBLISHING QUEUE - Coda di pubblicazione
# ==============================================================================
with tab3:
    st.header("▶️ Publishing Queue: Post Pronti per la Pubblicazione")

    st.subheader("📬 Post in Coda")
    posts_to_publish = db.get_posts_to_publish()
    if not posts_to_publish:
        st.info("La coda di pubblicazione è vuota.")
    else:
        st.warning(f"**{len(posts_to_publish)} post** pronti per essere pubblicati!")
        for post in posts_to_publish: st.markdown(
            f"- **ID {post.id}**: Programmato per {format_datetime(post.scheduled_for)}")

    if st.button("🚀 Processa Coda di Pubblicazione", type="primary", use_container_width=True,
                 disabled=not posts_to_publish):
        with st.spinner("Pubblicazione dei post..."):
            scheduler = LinkedInScheduler()
            results = asyncio.run(scheduler.process_scheduled_posts())
            st.success("Processo terminato!")
            for result in results:
                if result.get('status') == 'published':
                    st.success(f"✅ Pubblicato post ID {result.get('post_id')}.")
                else:
                    st.error(f"❌ Fallito post ID {result.get('post_id')}: {result.get('error')}")
            st.rerun()