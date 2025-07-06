# src/content_extractor.py
"""
Content Extractor Module
Extracts and processes content from various sources:
- Web URLs (including main preview image)
- LinkedIn posts/profiles
- PDF files
- Plain text
"""

import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Union
import re
from urllib.parse import urlparse, urljoin
import PyPDF2
from io import BytesIO
import validators
from datetime import datetime
import aiohttp
import asyncio
from dataclasses import dataclass, field
from pathlib import Path

from config import config

# --- DATA STRUCTURE ---
@dataclass
class ExtractedContent:
    """Data class for extracted content, now with image_url."""
    source_type: str
    source: str
    title: Optional[str] = None
    content: str = ""
    summary: Optional[str] = None
    author: Optional[str] = None
    date: Optional[datetime] = None
    keywords: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    error: Optional[str] = None
    image_url: Optional[str] = None  # <-- CAMPO CHIAVE PER L'IMMAGINE

    @property
    def is_valid(self) -> bool:
        return bool(self.content) and self.error is None

    @property
    def word_count(self) -> int:
        return len(self.content.split()) if self.content else 0

# --- MAIN EXTRACTOR CLASS ---
class ContentExtractor:
    """Main class for extracting content from various sources."""

    def __init__(self):
        self.headers = {'User-Agent': config.USER_AGENT}
        self.timeout = config.REQUEST_TIMEOUT

    async def extract(self, source: Union[str, Path, BytesIO]) -> ExtractedContent:
        """Main extraction method that determines source type and delegates."""
        try:
            if isinstance(source, str):
                if validators.url(source):
                    return await self.extract_from_url(source)
                return self.extract_from_text(source)
            elif isinstance(source, Path):
                if source.suffix.lower() == '.pdf':
                    return self.extract_from_pdf(source)
                return self.extract_from_text(source.read_text(encoding='utf-8', errors='ignore'))
            return ExtractedContent(source_type="unknown", source=str(source), error="Unsupported source type")
        except Exception as e:
            return ExtractedContent(source_type="error", source=str(source), error=f"Extraction failed: {e}")

    async def extract_from_url(self, url: str) -> ExtractedContent:
        """Extract content and main preview image from a web URL."""
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url, timeout=self.timeout) as response:
                    response.raise_for_status()
                    html = await response.text()

            soup = BeautifulSoup(html, 'lxml')

            # Rimuovi elementi non necessari per l'analisi del contenuto
            for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
                tag.decompose()

            # Estrai i metadati e il contenuto
            title = self._extract_title(soup)
            description = self._extract_description(soup)
            content = self._extract_main_content(soup)

            # --- LOGICA DI ESTRAZIONE IMMAGINE POTENZIATA ---
            image_url = self._extract_main_image_url(soup, url)

            return ExtractedContent(
                source_type="web",
                source=url,
                title=title,
                content=self._clean_text(content),
                summary=description,
                image_url=image_url,  # <-- Assegna l'URL dell'immagine trovato
                keywords=self._extract_keywords(content),
                metadata={"domain": urlparse(url).netloc}
            )

        except asyncio.TimeoutError:
            return ExtractedContent(source_type="web", source=url, error=f"Timeout ({self.timeout}s) for {url}")
        except Exception as e:
            return ExtractedContent(source_type="web", source=url, error=f"Error extracting from {url}: {e}")

    def extract_from_text(self, text: str) -> ExtractedContent:
        """Extract content from plain text."""
        cleaned_content = self._clean_text(text)
        title = cleaned_content.split('\n', 1)[0][:70] # Titolo è la prima riga o i primi 70 caratteri
        return ExtractedContent(
            source_type="text",
            source="pasted_text",
            title=title,
            content=cleaned_content
        )

    def extract_from_pdf(self, source: Union[Path, BytesIO]) -> ExtractedContent:
        """Extract content from a PDF file."""
        try:
            pdf_reader = PyPDF2.PdfReader(source)
            content = " ".join(page.extract_text() for page in pdf_reader.pages if page.extract_text())
            source_name = source.name if isinstance(source, Path) else "uploaded.pdf"
            metadata = pdf_reader.metadata or {}
            title = metadata.get('/Title', source_name)
            return ExtractedContent(
                source_type="pdf",
                source=source_name,
                title=str(title) if title else source_name,
                content=self._clean_text(content)
            )
        except Exception as e:
            return ExtractedContent(source_type="pdf", source=str(source), error=f"Error reading PDF: {e}")

    # --- METODI HELPER PER L'ESTRAZIONE ---
    def _extract_main_image_url(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """Extracts the main image URL, prioritizing Open Graph tags."""
        # Cerca i tag meta per l'immagine nell'ordine di priorità
        selectors = [
            {'property': 'og:image'},
            {'name': 'twitter:image'},
            {'itemprop': 'image'}
        ]
        for selector in selectors:
            tag = soup.find('meta', attrs=selector)
            if tag and tag.get('content'):
                # urljoin garantisce che l'URL sia assoluto (es. trasforma /img.png in https://sito.com/img.png)
                return urljoin(base_url, tag['content'])

        # Fallback: cerca un link rel="image_src"
        link_tag = soup.find('link', rel='image_src')
        if link_tag and link_tag.get('href'):
            return urljoin(base_url, link_tag['href'])

        return None

    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extracts title, prioritizing social media tags."""
        selectors = [
            {'property': 'og:title'},
            {'name': 'twitter:title'},
        ]
        for selector in selectors:
            tag = soup.find('meta', attrs=selector)
            if tag and tag.get('content'):
                return tag['content'].strip()

        # Fallback su h1 e title
        if soup.h1: return soup.h1.get_text(strip=True)
        if soup.title: return soup.title.string.strip()
        return None

    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extracts description, prioritizing social media tags."""
        selectors = [
            {'property': 'og:description'},
            {'name': 'twitter:description'},
            {'name': 'description'}
        ]
        for selector in selectors:
            tag = soup.find('meta', attrs=selector)
            if tag and tag.get('content'):
                return tag['content'].strip()
        return None

    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Heuristically extracts the main content of a page."""
        main_content_selectors = [
            'article', 'main',
            'div[class*="post-content"]', 'div[class*="entry-content"]',
            'div[id*="main-content"]', 'div[id*="content"]'
        ]
        for selector in main_content_selectors:
            tag = soup.select_one(selector)
            if tag:
                return tag.get_text(separator=' ', strip=True)

        return soup.body.get_text(separator=' ', strip=True) if soup.body else ""

    def _clean_text(self, text: str) -> str:
        """Cleans and normalizes text."""
        if not text: return ""
        text = re.sub(r'\s+', ' ', text)  # Collapse whitespace
        text = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', text)  # Remove control characters
        return text.strip()

    def _extract_keywords(self, text: str, top_n: int = 5) -> List[str]:
        """Simple keyword extraction based on frequency."""
        words = re.findall(r'\b[a-zA-Z]{4,15}\b', text.lower())
        stop_words = {'this', 'that', 'with', 'from', 'your', 'about', 'just', 'more', 'have', 'been'}
        word_freq = {}
        for word in words:
            if word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1

        sorted_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, _ in sorted_keywords[:top_n]]

# --- SYNCHRONOUS WRAPPER ---
def extract_content(source: Union[str, Path, BytesIO]) -> ExtractedContent:
    """Synchronous wrapper for content extraction."""
    extractor = ContentExtractor()
    try:
        # Get or create an event loop for the current thread
        loop = asyncio.get_event_loop()
        if loop.is_running():
             # Se c'è già un loop in esecuzione (come in Streamlit), crea un task
             return asyncio.run_coroutine_threadsafe(extractor.extract(source), loop).result()
        else:
             return loop.run_until_complete(extractor.extract(source))
    except RuntimeError:
        # Se non c'è un loop, creane uno nuovo
        return asyncio.run(extractor.extract(source))