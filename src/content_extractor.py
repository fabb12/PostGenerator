"""
Content Extractor Module
Extracts and processes content from various sources:
- Web URLs
- LinkedIn posts/profiles
- PDF files
- Plain text
"""

import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Union
import re
from urllib.parse import urlparse
import PyPDF2
from io import BytesIO
import validators
from datetime import datetime
import aiohttp
import asyncio
from dataclasses import dataclass
from pathlib import Path

from config import config


@dataclass
class ExtractedContent:
    """Data class for extracted content"""
    source_type: str  # 'web', 'pdf', 'text', 'linkedin'
    source: str  # URL or identifier
    title: Optional[str] = None
    content: str = ""
    summary: Optional[str] = None
    author: Optional[str] = None
    date: Optional[datetime] = None
    keywords: List[str] = None
    metadata: Dict = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.metadata is None:
            self.metadata = {}

    @property
    def is_valid(self) -> bool:
        return bool(self.content) and self.error is None

    @property
    def word_count(self) -> int:
        return len(self.content.split()) if self.content else 0


class ContentExtractor:
    """Main class for extracting content from various sources"""

    def __init__(self):
        self.headers = {
            'User-Agent': config.USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        self.timeout = config.REQUEST_TIMEOUT

    async def extract(self, source: Union[str, Path, BytesIO]) -> ExtractedContent:
        """
        Main extraction method that determines source type and delegates

        Args:
            source: URL string, file path, or file-like object

        Returns:
            ExtractedContent object with extracted data
        """
        # Determine source type
        if isinstance(source, str):
            if validators.url(source):
                return await self.extract_from_url(source)
            elif source.endswith('.pdf'):
                return self.extract_from_pdf(Path(source))
            else:
                return self.extract_from_text(source)
        elif isinstance(source, Path):
            if source.suffix == '.pdf':
                return self.extract_from_pdf(source)
            else:
                return self.extract_from_text(source.read_text())
        elif isinstance(source, BytesIO):
            return self.extract_from_pdf(source)
        else:
            return ExtractedContent(
                source_type="unknown",
                source=str(source),
                error="Unsupported source type"
            )

    async def extract_from_url(self, url: str) -> ExtractedContent:
        """Extract content from a web URL"""
        try:
            # Determine if it's a LinkedIn URL
            if 'linkedin.com' in url:
                return await self._extract_linkedin(url)

            # Regular web extraction
            async with aiohttp.ClientSession() as session:
                async with session.get(
                        url,
                        headers=self.headers,
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    response.raise_for_status()
                    html = await response.text()

            # Parse with BeautifulSoup
            soup = BeautifulSoup(html, 'lxml')

            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer"]):
                script.decompose()

            # Extract metadata
            title = self._extract_title(soup)
            author = self._extract_author(soup)
            date = self._extract_date(soup)
            description = self._extract_description(soup)

            # Extract main content
            content = self._extract_main_content(soup)

            # Clean and process content
            content = self._clean_text(content)

            # Extract keywords
            keywords = self._extract_keywords(content)

            return ExtractedContent(
                source_type="web",
                source=url,
                title=title,
                content=content,
                summary=description,
                author=author,
                date=date,
                keywords=keywords,
                metadata={
                    "url": url,
                    "domain": urlparse(url).netloc
                }
            )

        except aiohttp.ClientTimeout:
            return ExtractedContent(
                source_type="web",
                source=url,
                error=f"Timeout while fetching {url}"
            )
        except Exception as e:
            return ExtractedContent(
                source_type="web",
                source=url,
                error=f"Error extracting from {url}: {str(e)}"
            )

    async def _extract_linkedin(self, url: str) -> ExtractedContent:
        """Special handling for LinkedIn URLs"""
        # Note: LinkedIn has anti-scraping measures
        # This is a simplified version - in production, you might need selenium
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                        url,
                        headers=self.headers,
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    html = await response.text()

            soup = BeautifulSoup(html, 'lxml')

            # Try to extract LinkedIn-specific elements
            content_elements = []

            # Look for post content
            post_content = soup.find('div', class_='feed-shared-text')
            if post_content:
                content_elements.append(post_content.get_text())

            # Look for article content
            article_content = soup.find('div', class_='article-content')
            if article_content:
                content_elements.append(article_content.get_text())

            content = ' '.join(content_elements)

            if not content:
                # Fallback to general extraction
                return await self.extract_from_url(url)

            return ExtractedContent(
                source_type="linkedin",
                source=url,
                content=self._clean_text(content),
                metadata={"platform": "linkedin"}
            )

        except Exception as e:
            # Fallback to treating as regular URL
            return await self.extract_from_url(url)

    def extract_from_text(self, text: str) -> ExtractedContent:
        """Extract content from plain text (e.g., pasted content)"""
        # Clean the text
        content = self._clean_text(text)

        # Try to extract structure from the text
        lines = content.split('\n')
        title = None

        # First non-empty line might be title
        for line in lines:
            if line.strip():
                title = line.strip()
                break

        # Extract hashtags if present
        hashtags = re.findall(r'#\w+', content)

        # Extract URLs if present
        urls = re.findall(r'https?://\S+', content)

        return ExtractedContent(
            source_type="text",
            source="pasted_text",
            title=title,
            content=content,
            keywords=hashtags,
            metadata={
                "urls_found": urls,
                "hashtags": hashtags
            }
        )

    def extract_from_pdf(self, source: Union[Path, BytesIO]) -> ExtractedContent:
        """Extract content from PDF file"""
        try:
            content_parts = []

            if isinstance(source, Path):
                pdf_reader = PyPDF2.PdfReader(str(source))
                source_name = source.name
            else:
                pdf_reader = PyPDF2.PdfReader(source)
                source_name = "uploaded_pdf"

            # Extract text from all pages
            for page_num, page in enumerate(pdf_reader.pages):
                text = page.extract_text()
                if text:
                    content_parts.append(text)

            content = '\n'.join(content_parts)
            content = self._clean_text(content)

            # Extract metadata
            metadata = {}
            if pdf_reader.metadata:
                metadata = {
                    'title': pdf_reader.metadata.get('/Title', ''),
                    'author': pdf_reader.metadata.get('/Author', ''),
                    'subject': pdf_reader.metadata.get('/Subject', ''),
                    'pages': len(pdf_reader.pages)
                }

            return ExtractedContent(
                source_type="pdf",
                source=source_name,
                title=metadata.get('title', source_name),
                content=content,
                author=metadata.get('author'),
                metadata=metadata
            )

        except Exception as e:
            return ExtractedContent(
                source_type="pdf",
                source=str(source),
                error=f"Error extracting PDF: {str(e)}"
            )

    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract title from HTML"""
        # Try multiple methods
        title = None

        # 1. <title> tag
        if soup.title:
            title = soup.title.string

        # 2. <h1> tag
        if not title and soup.h1:
            title = soup.h1.get_text()

        # 3. Meta property og:title
        if not title:
            meta_title = soup.find('meta', property='og:title')
            if meta_title:
                title = meta_title.get('content')

        return title.strip() if title else None

    def _extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract author from HTML"""
        # Try multiple methods
        author_meta = soup.find('meta', {'name': 'author'})
        if author_meta:
            return author_meta.get('content')

        # Look for schema.org author
        author_span = soup.find('span', {'itemprop': 'author'})
        if author_span:
            return author_span.get_text()

        return None

    def _extract_date(self, soup: BeautifulSoup) -> Optional[datetime]:
        """Extract publication date from HTML"""
        # Try multiple date formats
        date_meta = soup.find('meta', {'property': 'article:published_time'})
        if date_meta:
            try:
                return datetime.fromisoformat(date_meta.get('content').replace('Z', '+00:00'))
            except:
                pass

        return None

    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract description/summary from HTML"""
        # Try meta description
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc:
            return meta_desc.get('content')

        # Try og:description
        og_desc = soup.find('meta', {'property': 'og:description'})
        if og_desc:
            return og_desc.get('content')

        return None

    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract main content from HTML"""
        # Try to find main content area
        content_candidates = [
            soup.find('main'),
            soup.find('article'),
            soup.find('div', class_=re.compile('content|main|body|post')),
            soup.find('div', id=re.compile('content|main|body|post'))
        ]

        for candidate in content_candidates:
            if candidate:
                return candidate.get_text(separator=' ', strip=True)

        # Fallback to body
        if soup.body:
            return soup.body.get_text(separator=' ', strip=True)

        return soup.get_text(separator=' ', strip=True)

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove special characters but keep punctuation
        text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F-\x9F]', '', text)

        # Fix common encoding issues
        text = text.replace(''', "'").replace(''', "'")
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace('–', '-').replace('—', '-')

        # Remove leading/trailing whitespace
        text = text.strip()

        return text

    def _extract_keywords(self, text: str, top_n: int = 10) -> List[str]:
        """Extract keywords from text using simple frequency analysis"""
        # Common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'about', 'as', 'is', 'was', 'are', 'were',
            'been', 'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'should', 'could', 'may', 'might', 'must', 'can', 'this', 'that', 'these',
            'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'what', 'which'
        }

        # Extract words
        words = re.findall(r'\b[a-z]+\b', text.lower())

        # Count frequencies
        word_freq = {}
        for word in words:
            if len(word) > 3 and word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1

        # Get top keywords
        keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, _ in keywords[:top_n]]


# Convenience function for simple synchronous extraction
def extract_content(source: Union[str, Path, BytesIO]) -> ExtractedContent:
    """Synchronous wrapper for content extraction"""
    extractor = ContentExtractor()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(extractor.extract(source))
    loop.close()
    return result