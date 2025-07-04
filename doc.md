# 🚀 LinkedIn Post Generator

**Genera contenuti LinkedIn professionali in pochi secondi usando l'intelligenza artificiale.**

Trasforma articoli, URL e testi in post LinkedIn coinvolgenti con Claude (Anthropic) o ChatGPT. Pianifica la pubblicazione, analizza le performance e gestisci i tuoi contenuti tutto da un'interfaccia semplice.

![LinkedIn Post Generator](https://img.shields.io/badge/LinkedIn-Post_Generator-0A66C2?style=for-the-badge&logo=linkedin)
![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit)

---

## 🎯 **Cosa Fa Questa App**

### Per Professionisti
- ✅ **Genera post LinkedIn** da articoli e contenuti web
- ✅ **Crea varianti** per scegliere la versione migliore
- ✅ **Pianifica pubblicazioni** nei momenti ottimali
- ✅ **Analizza performance** per migliorare l'engagement

### Per Aziende
- ✅ **Mantiene la brand voice** aziendale
- ✅ **Risparmia tempo** nella creazione contenuti
- ✅ **Aumenta la presenza** su LinkedIn
- ✅ **Traccia risultati** con analytics integrate

---

## 🚀 **Setup Rapido (5 minuti)**

### Prerequisiti
- **Python 3.8+** ([Download qui](https://python.org))
- **Account Anthropic** (Claude) OPPURE **OpenAI** (ChatGPT)
- **Account LinkedIn**

### 1. Installazione
```bash
# Clona il progetto
git clone https://github.com/tuousername/linkedin-post-generator.git
cd linkedin-post-generator

# Installa dipendenze
pip install -r requirements.txt
```

### 2. Configurazione
```bash
# Copia il template
copy .env.example .env

# Modifica .env con le tue credenziali (vedi sotto)
```

### 3. API Keys (OBBLIGATORIO)
Aggiungi almeno UNA di queste API keys nel file `.env`:

#### **Claude (Raccomandato)**
1. Vai su [console.anthropic.com](https://console.anthropic.com)
2. Crea account → **API Keys** → **Create Key**
3. Copia in `.env`: `ANTHROPIC_API_KEY=sk-ant-api03-il-tuo-key`

#### **OpenAI (Alternativa)**
1. Vai su [platform.openai.com](https://platform.openai.com)
2. Crea account → **API Keys** → **Create new secret key**
3. Copia in `.env`: `OPENAI_API_KEY=sk-il-tuo-key`

### 4. LinkedIn (Opzionale)
Per pubblicazione automatica:
```env
LINKEDIN_EMAIL=tua-email@example.com
LINKEDIN_PASSWORD=tua-password
```

### 5. Avvio
```bash
streamlit run main.py
```

**🎉 L'app si aprirà su [http://localhost:8501](http://localhost:8501)**

---

## 📚 **Come Usare l'App**

### 🏠 **Homepage**
- **Quick Actions**: Bottoni per accesso rapido alle funzioni
- **Recent Posts**: I tuoi ultimi contenuti
- **Analytics**: Overview delle performance

### 📝 **1. Creare un Post**

#### **Step 1: Aggiungi Contenuti**
1. Vai su **📝 Create Post**
2. Scegli la fonte:
   - **🌐 Web URL**: Incolla link di articoli/notizie
   - **📄 Text**: Copia-incolla contenuto
   - **📑 PDF**: Carica documenti
   - **🔗 Multiple URLs**: Più link insieme

**Esempi di URL che funzionano bene:**
- Articoli di settore
- Notizie aziendali
- Blog post
- Report di ricerca
- Post LinkedIn di altri

#### **Step 2: Configura Generazione**
- **Tone**: Professional, Friendly, Casual, Formal...
- **Post Type**: Informative, News Sharing, Thought Leadership...
- **Variants**: Quante versioni generare (1-5)
- **Target Audience**: Es. "Supply chain managers"

#### **Step 3: Genera e Scegli**
1. Click **🚀 Generate Posts**
2. Aspetta 10-30 secondi
3. Vedi le varianti generate
4. Scegli quella che preferisci
5. Modifica se necessario

#### **Step 4: Pubblica**
- **💾 Save as Draft**: Salva per dopo
- **📅 Schedule Post**: Programma pubblicazione
- **📋 Copy**: Copia per incollare manualmente

### 📅 **2. Pianificare Post**

#### **Schedulazione Singola**
1. Vai su **📅 Schedule**
2. Seleziona un draft
3. Scegli **data e ora**
4. Usa gli **orari suggeriti** (9-10 AM, 2-3 PM)
5. Click **🚀 Schedule Post**

#### **Schedulazione di Massa**
1. Sezione **📦 Bulk Schedule**
2. Seleziona **più post**
3. Imposta **frequenza** (giornaliera, settimanale)
4. Il sistema li distribuisce automaticamente

#### **Orari Ottimali**
L'app suggerisce i momenti migliori basandosi su:
- Dati di engagement LinkedIn
- Fuso orario configurato
- Giorni lavorativi

### 📊 **3. Analizzare Performance**

#### **Dashboard Analytics**
- **Engagement Trend**: Andamento nel tempo
- **Post Type Performance**: Quale tipo funziona meglio
- **Best Posting Times**: Quando postare
- **Top Performing Posts**: I tuoi migliori

#### **Metriche Disponibili**
- **Views**: Visualizzazioni
- **Likes**: Mi piace
- **Comments**: Commenti
- **Shares**: Condivisioni
- **Engagement Rate**: Percentuale di coinvolgimento

#### **Export Dati**
- **📊 CSV**: Per Excel/Google Sheets
- **📝 JSON**: Per analisi avanzate
- **📈 Report**: Summary automatico

---

## 🎨 **Personalizzazione**

### **Toni Disponibili**
- **Professional**: Linguaggio business formale
- **Friendly**: Cordiale e accessibile
- **Casual**: Informale ma rispettoso
- **Enthusiastic**: Energico e motivazionale
- **Inspirational**: Che ispira e motiva

### **Tipi di Post**
- **Informative**: Condivisione di conoscenze
- **News Sharing**: Commento su notizie
- **Thought Leadership**: Opinion e insights
- **Company Update**: Aggiornamenti aziendali
- **Success Story**: Case study e successi
- **Tips & Tricks**: Consigli pratici

### **Hashtag Automatici**
L'app aggiunge automaticamente hashtag rilevanti:
- Basati sul contenuto
- Specifici per il settore
- Mix di popolari e di nicchia

---

## 🔧 **Risoluzione Problemi**

### **App Non Si Avvia**
```bash
# Verifica Python
python --version  # Deve essere 3.8+

# Reinstalla dipendenze
pip install --upgrade pip
pip install -r requirements.txt

# Riavvia
streamlit run main.py
```

### **Errori di Generazione**
- ✅ Verifica che API key sia corretta nel `.env`
- ✅ Controlla connessione internet
- ✅ Prova con contenuto più breve
- ✅ Cambia modello AI nelle impostazioni

### **Problemi LinkedIn**
- ✅ Verifica email/password corrette
- ✅ Disabilita 2FA temporaneamente
- ✅ Usa l'opzione "Copy" e incolla manualmente

### **Content Extraction Fallisce**
- ✅ Verifica che l'URL sia accessibile
- ✅ Prova con articoli diversi
- ✅ Usa l'opzione "Text" e incolla il contenuto

---

## 💡 **Best Practices**

### **Per Contenuti Migliori**
1. **Usa fonti di qualità**: Siti autorevoli e aggiornati
2. **Varia i toni**: Alterna professional e friendly
3. **Testa varianti**: Prova diverse versioni
4. **Personalizza**: Modifica sempre il contenuto generato
5. **Aggiungi valore**: Non limitarti a condividere, commenta

### **Per Engagement Migliore**
1. **Posta negli orari ottimali**: 9-10 AM, 2-3 PM giorni lavorativi
2. **Usa call-to-action**: Termina con domande
3. **Includi emoji**: 1-3 per post (già incluse dall'AI)
4. **Hashtag strategici**: 3-5 hashtag rilevanti
5. **Monitora e rispondi**: Rispondi ai commenti rapidamente

### **Per Aziende**
1. **Mantieni consistenza**: Usa sempre lo stesso tone
2. **Pianifica in anticipo**: Schedula una settimana prima
3. **Diversifica contenuti**: Alterna tipi di post
4. **Traccia performance**: Usa analytics per migliorare
5. **Brand voice**: Personalizza i prompt per il tuo settore

---

## 🎯 **Casi d'Uso**

### **Professionista/Consulente**
- Condividi articoli di settore con tue opinioni
- Crea thought leadership sui tuoi temi
- Documenta successi e case study
- Costruisci personal brand

### **Azienda B2B**
- Condividi company update e novità
- Commenta trend di settore
- Mostra expertise e competenze
- Genera lead con contenuti di valore

### **Marketing Team**
- Scala la produzione di contenuti
- Mantieni presenza costante
- Testa messaggi diversi
- Analizza performance per ottimizzare

### **Sales Professional**
- Condividi insights sui clienti
- Posizionati come esperto
- Commenta su successi e sfide
- Costruisci relazioni con prospect

---

## 📈 **Risultati Attesi**

### **Dopo 1 Settimana**
- ✅ 5-10 post di qualità generati
- ✅ Familiarità con l'interfaccia
- ✅ Prime analytics disponibili

### **Dopo 1 Mese**
- ✅ 20-40 post pubblicati
- ✅ Aumento follower LinkedIn
- ✅ Maggiore engagement sui post
- ✅ Workflow di pubblicazione ottimizzato

### **Dopo 3 Mesi**
- ✅ Brand presence consolidata
- ✅ Lead generation da LinkedIn
- ✅ Authority nel tuo settore
- ✅ ROI misurabile dall'attività

---

## 🔐 **Privacy e Sicurezza**

### **I Tuoi Dati**
- ✅ **Tutto in locale**: Database SQLite sul tuo computer
- ✅ **No cloud storage**: Nessun dato inviato a server esterni
- ✅ **API sicure**: Comunicazione criptata con AI providers
- ✅ **Credenziali protette**: Stored in environment variables

### **API Usage**
- ✅ **Costi controllati**: Pochi centesimi per post
- ✅ **No data training**: I tuoi contenuti non allenano i modelli
- ✅ **Rate limiting**: Protezione da uso eccessivo

---

## 💰 **Costi**

### **App**
- ✅ **Completamente gratuita**
- ✅ **Open source**
- ✅ **No abbonamenti**

### **API AI** (Pay-per-use)
- **Claude**: ~$0.01-0.05 per post
- **OpenAI**: ~$0.01-0.03 per post
- **Budget mensile**: $5-20 per uso normale

### **Deployment Cloud** (Opzionale)
- **Render.com**: Gratis (sleep dopo 15min) o $7/mese
- **Heroku**: $7/mese
- **VPS**: $5-20/mese

---

## 🆘 **Supporto**

### **Problemi Tecnici**
- 📧 **GitHub Issues**: [Repository Issues](https://github.com/tuousername/linkedin-post-generator/issues)
- 📚 **Documentation**: Questa guida
- 🔍 **Debug**: Controlla i log in `logs/app.log`

### **Feature Requests**
- 💡 **Suggestions**: Apri una Issue su GitHub
- 🗳️ **Voting**: Supporta feature richieste da altri
- 🤝 **Contribute**: Contribuisci al codice

### **Community**
- 💬 **Discussions**: GitHub Discussions
- 🐦 **Updates**: Segui gli aggiornamenti

---

## 🚧 **Roadmap**

### **Prossime Feature**
- [ ] **LinkedIn API ufficiale** per pubblicazione diretta
- [ ] **Analytics avanzate** con AI insights
- [ ] **Template personalizzati** per settori specifici
- [ ] **Collaborazione team** e approval workflow
- [ ] **Integrazione CRM** (HubSpot, Salesforce)
- [ ] **Mobile app** companion
- [ ] **Multi-language** support
- [ ] **Video content** generation

### **Miglioramenti**
- [ ] **UI/UX** più intuitiva
- [ ] **Performance** optimization
- [ ] **Error handling** migliorato
- [ ] **Onboarding** guidato
- [ ] **Documentation** estesa

---

## 🎉 **Quick Start Summary**

```bash
# 1. Install
git clone <repo> && cd linkedin-post-generator
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Add your ANTHROPIC_API_KEY or OPENAI_API_KEY

# 3. Run
streamlit run main.py

# 4. Use
# → Add URL → Generate → Choose variant → Schedule/Publish
```

---

## 🏆 **Conclusione**

Questa app trasforma il modo in cui crei contenuti LinkedIn:

- ⚡ **Da ore a minuti**: Genera post in 30 secondi
- 🎯 **Qualità consistente**: AI addestrata su best practice
- 📊 **Data-driven**: Decisioni basate su analytics
- 🚀 **Scalabile**: Da 1 a 100 post al mese

**Inizia ora e trasforma la tua presenza LinkedIn!** 🚀

---

*Made with ❤️ for the LinkedIn community*

**⭐ Se ti piace, lascia una stella su GitHub!**