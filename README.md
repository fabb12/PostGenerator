# Struttura Semplificata - LinkedIn Post Generator

## 📁 Struttura Minima e Funzionale

```
linkedin-post-generator/
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
├── config.py
├── main.py                    # Entry point Streamlit
│
├── src/
│   ├── __init__.py
│   ├── content_extractor.py   # Estrae contenuti da URL/testo
│   ├── post_generator.py      # Genera post con Claude/OpenAI
│   ├── linkedin_client.py     # Pubblica su LinkedIn
│   └── database.py            # Salva post (SQLite)
│
├── pages/                     # Pagine Streamlit
│   ├── 1_📝_Create_Post.py
│   ├── 2_📅_Schedule.py
│   └── 3_📊_History.py
│
├── utils/
│   ├── __init__.py
│   └── helpers.py             # Funzioni utility
│
├── templates/                 # Template prompt
│   └── prompts.py
│
└── data/
    └── posts.db              # Database SQLite
```

## 📋 Lista dei File da Implementare (15 file totali)

### 1. **File di Configurazione** (5 file)
- `.env.example` - Variabili d'ambiente esempio
- `.gitignore` - File da ignorare
- `requirements.txt` - Dipendenze Python
- `config.py` - Configurazione app
- `README.md` - Documentazione

### 2. **Core Functionality** (4 file)
- `src/content_extractor.py` - Estrae contenuti da URL e testo
- `src/post_generator.py` - Genera post con LLM
- `src/linkedin_client.py` - Pubblica su LinkedIn
- `src/database.py` - Gestione database SQLite

### 3. **UI Streamlit** (4 file)
- `main.py` - App principale
- `pages/1_📝_Create_Post.py` - Crea post
- `pages/2_📅_Schedule.py` - Schedula post
- `pages/3_📊_History.py` - Storico post

### 4. **Utilities** (2 file)
- `utils/helpers.py` - Funzioni di supporto
- `templates/prompts.py` - Template per i prompt

## 🚀 Funzionalità Base

1. **Input Fonti**:
   - URL di articoli web
   - Testo copiato da LinkedIn
   - Upload file PDF/TXT

2. **Generazione Post**:
   - Usa Claude API (o OpenAI come fallback)
   - 3 varianti di post tra cui scegliere
   - Personalizzazione tono e stile

3. **Preview e Modifica**:
   - Anteprima del post
   - Modifica manuale
   - Conteggio caratteri

4. **Pubblicazione**:
   - Pubblica subito su LinkedIn
   - Salva come bozza
   - Schedulazione semplice

5. **Storico**:
   - Lista post pubblicati
   - Bozze salvate
   - Possibilità di riutilizzare

## 🔧 Stack Tecnologico Semplificato

- **Frontend**: Streamlit (semplice e veloce)
- **LLM**: Claude API (Anthropic) o OpenAI
- **Database**: SQLite (nessuna configurazione)
- **LinkedIn**: linkedin-api (non ufficiale ma funzionale)
- **Scraping**: BeautifulSoup + Requests

## 📝 Ordine di Implementazione

1. **Setup Base** (3 file):
   - `.env.example`
   - `requirements.txt`
   - `config.py`

2. **Core Functions** (4 file):
   - `src/content_extractor.py`
   - `src/post_generator.py`
   - `templates/prompts.py`
   - `src/database.py`

3. **UI Base** (2 file):
   - `main.py`
   - `pages/1_📝_Create_Post.py`

4. **Features Aggiuntive** (4 file):
   - `src/linkedin_client.py`
   - `pages/2_📅_Schedule.py`
   - `pages/3_📊_History.py`
   - `utils/helpers.py`

5. **Docs** (2 file):
   - `.gitignore`
   - `README.md`

**Totale: 15 file** - Molto più gestibile e focalizzato sulle funzionalità essenziali!
