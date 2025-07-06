# src/post_generator.py

"""
Post Generator Module
Generates LinkedIn posts using AI models (Claude, OpenAI, or Google Gemini)
Supports multiple variants, tones, post types, and media context.
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import asyncio
import re
from enum import Enum

# AI Libraries
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    genai = None
    GEMINI_AVAILABLE = False

# Local imports
from config import config
from src.content_extractor import ExtractedContent

# --- ENUMERATIONS AND DATA CLASSES ---
class PostTone(Enum):
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    CASUAL = "casual"
    FORMAL = "formal"
    ENTHUSIASTIC = "enthusiastic"
    INFORMATIVE = "informative"
    INSPIRATIONAL = "inspirational"

class PostType(Enum):
    INFORMATIVE = "informative"
    NEWS_SHARING = "news_sharing"
    THOUGHT_LEADERSHIP = "thought_leadership"
    COMPANY_UPDATE = "company_update"
    INDUSTRY_INSIGHT = "industry_insight"
    SUCCESS_STORY = "success_story"
    TIPS_AND_TRICKS = "tips_and_tricks"

@dataclass
class GeneratedPost:
    content: str
    tone: str
    post_type: str
    model_used: str
    generation_time: datetime
    metadata: Dict[str, Any]
    sources_used: List[str]

    @property
    def char_count(self) -> int: return len(self.content)
    @property
    def word_count(self) -> int: return len(self.content.split())
    @property
    def hashtag_count(self) -> int: return len(re.findall(r'#\w+', self.content))

# --- MAIN GENERATOR CLASS ---
class PostGenerator:
    """Main class for generating LinkedIn posts using AI models."""

    def __init__(self):
        self._init_clients()
        self.temperature = config.LLM_TEMPERATURE
        self.max_tokens = config.MAX_TOKENS

    def _init_clients(self):
        self.claude_client, self.openai_client, self.gemini_client = None, None, None
        if config.ANTHROPIC_API_KEY:
            try: self.claude_client = AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
            except Exception as e: print(f"❌ Claude init failed: {e}")
        if config.OPENAI_API_KEY:
            try: self.openai_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
            except Exception as e: print(f"❌ OpenAI init failed: {e}")
        if config.GOOGLE_API_KEY and GEMINI_AVAILABLE:
            try:
                genai.configure(api_key=config.GOOGLE_API_KEY)
                self.gemini_client = genai.GenerativeModel(config.GEMINI_MODEL)
            except Exception as e: print(f"❌ Gemini init failed: {e}")

    def _load_prompts(self, model: str = "gemini") -> Dict[str, str]:
        system_prompt = config.SYSTEM_PROMPTS.get(model, "You are a helpful assistant.")
        user_template = """Sei un esperto di social media marketing specializzato in LinkedIn.
Il tuo compito è creare un post professionale e coinvolgente basato sulle seguenti informazioni.

**ISTRUZIONI GENERALI:**
- Tono: {tone}
- Tipo di Post: {post_type}
- Lingua: {language}
- Includi 3-5 hashtag pertinenti in {language}.
- Aggiungi 1-3 emoji appropriate.
- Il testo deve essere scorrevole, ben strutturato con paragrafi brevi e un "hook" iniziale che catturi l'attenzione.
- Termina sempre con una domanda o una call-to-action per stimolare la discussione.

**CONTESTO SPECIFICO PER QUESTO POST:**
{media_context}

**FONTENTI DI CONTENUTO DA CUI ISPIRARTI:**
{sources_summary}

**ISTRUZIONI AGGIUNTIVE DALL'UTENTE:**
{additional_context}

Ora, genera SOLO il testo per il post di LinkedIn.
"""
        return {'system': system_prompt, 'user_template': user_template}

    def _prepare_prompt(
        self,
        sources_summary: str,
        tone: str,
        post_type: str,
        additional_context: Optional[str],
        language: str,
        link_url: Optional[str] = None,
        image_description: Optional[str] = None
    ) -> str:
        """Prepare the final prompt for the AI model, including media context."""
        prompts = self._load_prompts()
        media_context_parts = []

        if link_url:
            media_context_parts.append(
                f"Il post deve includere il seguente link: {link_url}. "
                "Il tuo testo deve commentare o introdurre questo link, aggiungendo valore e una prospettiva unica. "
                "NON ripetere il titolo dell'articolo del link nel tuo testo."
            )

        if image_description:
            media_context_parts.append(
                f"Il post sarà accompagnato da un'immagine descritta come: '{image_description}'. "
                "Fai riferimento a questa immagine nel testo (es. 'Come mostra questo grafico...', 'In questa foto...')."
            )

        if not media_context_parts:
            media_context_parts.append("Questo è un post di solo testo. Assicurati che sia completo e coinvolgente di per sé.")

        return prompts['user_template'].format(
            sources_summary=sources_summary,
            tone=tone,
            post_type=post_type,
            language=language,
            media_context='\n'.join(media_context_parts),
            additional_context=additional_context or "Nessuna istruzione aggiuntiva."
        )

    async def generate(
        self,
        sources: List[ExtractedContent],
        tone: PostTone = PostTone.PROFESSIONAL,
        post_type: PostType = PostType.INFORMATIVE,
        num_variants: int = 1,
        additional_context: Optional[str] = None,
        preferred_model: str = "gemini",
        language: str = "Italian",
        link_url: Optional[str] = None,
        image_description: Optional[str] = None
    ) -> List[GeneratedPost]:

        sources_summary = self._prepare_sources_summary(sources)
        prompt = self._prepare_prompt(
            sources_summary=sources_summary,
            tone=tone.value,
            post_type=post_type.value,
            additional_context=additional_context,
            language=language,
            link_url=link_url,
            image_description=image_description
        )

        tasks = []
        for _ in range(num_variants):
            if preferred_model == "claude" and self.claude_client:
                tasks.append(self._generate_with_claude(prompt, self.temperature))
            elif preferred_model == "openai" and self.openai_client:
                tasks.append(self._generate_with_openai(prompt, self.temperature))
            elif preferred_model == "gemini" and self.gemini_client:
                tasks.append(self._generate_with_gemini(prompt, self.temperature))
            else: # Fallback al primo disponibile
                if self.gemini_client: tasks.append(self._generate_with_gemini(prompt, self.temperature))
                elif self.claude_client: tasks.append(self._generate_with_claude(prompt, self.temperature))
                elif self.openai_client: tasks.append(self._generate_with_openai(prompt, self.temperature))

        if not tasks: raise ValueError("Nessun client AI configurato o disponibile.")

        results = await asyncio.gather(*tasks, return_exceptions=True)

        posts = []
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                print(f"Errore nella generazione della variante {i+1}: {res}")
                continue

            posts.append(GeneratedPost(
                content=res['content'],
                tone=tone.value, post_type=post_type.value, model_used=res['model'],
                generation_time=datetime.now(),
                metadata={'variant': i + 1, 'temperature': self.temperature},
                sources_used=[s.source for s in sources]
            ))

        if not posts: raise ValueError("Tutti i tentativi di generazione sono falliti.")
        return posts

    def _prepare_sources_summary(self, sources: List[ExtractedContent]) -> str:
        if not sources or not any(s.is_valid for s in sources):
            return "Nessuna fonte di contenuto fornita."
        summary_lines = []
        for i, source in enumerate(filter(lambda s: s.is_valid, sources), 1):
            title = f"Fonte {i} Titolo: {source.title}" if source.title else f"Fonte {i}"
            content_preview = source.content[:1500] + "..." if len(source.content) > 1500 else source.content
            summary_lines.append(f"{title}\nContenuto: {content_preview}")
        return '\n\n'.join(summary_lines)

    def _process_generated_content(self, content: str) -> str:
        content = re.sub(r'<[^>]+>', '', content)
        content = content.replace('**', '').replace('*', '').replace('```', '')
        return content.strip()

    async def _generate_with_claude(self, prompt: str, temperature: float) -> Dict:
        prompts = self._load_prompts("claude")
        response = await self.claude_client.messages.create(
            model=config.CLAUDE_MODEL, max_tokens=self.max_tokens, temperature=temperature,
            system=prompts['system'], messages=[{"role": "user", "content": prompt}]
        )
        return {'content': self._process_generated_content(response.content[0].text), 'model': config.CLAUDE_MODEL}

    async def _generate_with_openai(self, prompt: str, temperature: float) -> Dict:
        prompts = self._load_prompts("openai")
        response = await self.openai_client.chat.completions.create(
            model=config.OPENAI_MODEL, max_tokens=self.max_tokens, temperature=temperature,
            messages=[{"role": "system", "content": prompts['system']}, {"role": "user", "content": prompt}]
        )
        return {'content': self._process_generated_content(response.choices[0].message.content), 'model': config.OPENAI_MODEL}

    async def _generate_with_gemini(self, prompt: str, temperature: float) -> Dict:
        prompts = self._load_prompts("gemini")
        full_prompt = f"{prompts['system']}\n\n{prompt}"
        response = await self.gemini_client.generate_content_async(full_prompt, generation_config={'temperature': temperature})
        return {'content': self._process_generated_content(response.text), 'model': config.GEMINI_MODEL}

    def generate_sync(self, **kwargs) -> List[GeneratedPost]:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.generate(**kwargs))

# --- CONVENIENCE FUNCTIONS ---
def generate_post(**kwargs) -> List[GeneratedPost]:
    generator = PostGenerator()
    return generator.generate_sync(**kwargs)

def get_model_info() -> Dict[str, Any]:
    return {
        "claude": {"available": bool(config.ANTHROPIC_API_KEY), "model": config.CLAUDE_MODEL},
        "openai": {"available": bool(config.OPENAI_API_KEY), "model": config.OPENAI_MODEL},
        "gemini": {"available": bool(config.GOOGLE_API_KEY and GEMINI_AVAILABLE), "model": config.GEMINI_MODEL}
    }