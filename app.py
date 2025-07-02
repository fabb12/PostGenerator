# simple_generator.py - Script semplice per testare subito il generatore

import os
import requests
from bs4 import BeautifulSoup
import openai
from datetime import datetime
import json

# Configurazione (sostituisci con le tue credenziali)
OPENAI_API_KEY = "sk-tuachiaveapi"  # Inserisci la tua API key
openai.api_key = OPENAI_API_KEY


def scrape_web_content(url):
    """Estrae contenuto da un URL"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Rimuovi script e style
        for script in soup(["script", "style"]):
            script.decompose()

        title = soup.find('title').text if soup.find('title') else ''
        text = soup.get_text()

        # Pulisci il testo
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)[:1000]  # Limita a 1000 caratteri

        return {
            'url': url,
            'title': title.strip(),
            'content': text
        }
    except Exception as e:
        return {'error': str(e)}


def generate_linkedin_post(sources_data, company_style=None):
    """Genera un post LinkedIn usando GPT"""

    # Prepara il contenuto dalle fonti
    content_summary = []
    for source in sources_data:
        if 'error' not in source:
            content_summary.append(f"Fonte: {source.get('title', 'N/A')}")
            content_summary.append(f"Contenuto: {source.get('content', '')[:300]}...")
            content_summary.append("---")

    combined_content = '\n'.join(content_summary)

    # Prompt per GPT
    prompt = f"""
Sei un social media manager esperto per MC Trans SA, azienda di trasporti e logistica.
Crea un post LinkedIn professionale basandoti su questi contenuti:

{combined_content}

STILE AZIENDALE MC TRANS:
- Professionale ma accessibile
- Focus su innovazione e sostenibilità
- Evidenzia partnership internazionali
- Usa dati/statistiche quando disponibili
- Includi call-to-action per engagement

STRUTTURA:
1. Hook con emoji (1 riga)
2. Contenuto principale (3-4 righe)
3. 2-3 bullet points con insights
4. Call-to-action/domanda
5. 4-5 hashtag rilevanti

Mantieni il post sotto i 200 caratteri.
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Usa gpt-4 per risultati migliori
            messages=[
                {"role": "system", "content": "Sei un esperto social media manager per il settore logistics."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=400,
            temperature=0.7
        )

        return response.choices[0].message['content'].strip()

    except Exception as e:
        return f"Errore nella generazione: {str(e)}"


def save_post(post_content, filename=None):
    """Salva il post generato"""
    if filename is None:
        filename = f"post_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(post_content)
        f.write(f"\n\n--- Generato il {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")

    return filename


def main():
    print("🚀 LinkedIn Post Generator - MC Trans SA Style\n")

    # Input delle fonti
    print("Inserisci gli URL delle fonti (invio vuoto per terminare):")
    urls = []
    while True:
        url = input("URL: ").strip()
        if not url:
            break
        urls.append(url)

    if not urls:
        print("❌ Nessun URL inserito!")
        return

    # Scraping
    print("\n📊 Analizzando le fonti...")
    sources_data = []
    for url in urls:
        print(f"  Elaborando: {url}")
        data = scrape_web_content(url)
        if 'error' in data:
            print(f"  ⚠️  Errore: {data['error']}")
        else:
            print(f"  ✅ Estratto: {data['title']}")
            sources_data.append(data)

    if not sources_data:
        print("❌ Nessun contenuto estratto con successo!")
        return

    # Generazione post
    print("\n🤖 Generando post con AI...")
    post = generate_linkedin_post(sources_data)

    # Mostra risultato
    print("\n" + "=" * 50)
    print("📄 POST GENERATO:")
    print("=" * 50)
    print(post)
    print("=" * 50)

    # Salva?
    save_choice = input("\n💾 Vuoi salvare il post? (s/n): ").lower()
    if save_choice == 's':
        filename = save_post(post)
        print(f"✅ Post salvato in: {filename}")

    # Genera un altro?
    again = input("\n🔄 Vuoi generare un altro post? (s/n): ").lower()
    if again == 's':
        main()


if __name__ == "__main__":
    # Test rapido con URL di esempio
    if False:  # Cambia in True per test automatico
        test_urls = [
            "https://www.shippingitaly.it/",
            "https://www.transportonline.com/"
        ]

        print("TEST AUTOMATICO")
        sources = [scrape_web_content(url) for url in test_urls]
        post = generate_linkedin_post(sources)
        print(post)
    else:
        # Esecuzione interattiva
        main()

# ESEMPIO DI OUTPUT:
"""
🚢 Breaking: Significant shifts in Mediterranean shipping routes!

Container rates from China to Med ports surge 7%, while Northern Europe routes see unprecedented demand. At MC Trans SA, we're adapting our cross-border solutions to ensure seamless deliveries.

Key developments:
✅ Shanghai-Genoa rates up to €7,573/FEU
📈 Air cargo volumes +14.1% YoY 
🌱 Sustainable packaging reducing wood use by 98%

How is your supply chain adapting to these market dynamics?

#Logistics #Shipping #SupplyChain #MCTrans #Innovation
"""