"""
Post Generator Module
Generates LinkedIn posts using AI models (Claude or OpenAI)
Supports multiple variants, tones, and post types
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import asyncio
import json
from enum import Enum

# AI Libraries
from anthropic import Anthropic, AsyncAnthropic
from openai import OpenAI, AsyncOpenAI

# Local imports
from config import config
from src.content_extractor import ExtractedContent


class PostTone(Enum):
    """Available post tones"""
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly" 
    CASUAL = "casual"
    FORMAL = "formal"
    ENTHUSIASTIC = "enthusiastic"
    INFORMATIVE = "informative"
    INSPIRATIONAL = "inspirational"


class PostType(Enum):
    """Types of LinkedIn posts"""
    INFORMATIVE = "informative"
    NEWS_SHARING = "news_sharing"
    THOUGHT_LEADERSHIP = "thought_leadership"
    COMPANY_UPDATE = "company_update"
    INDUSTRY_INSIGHT = "industry_insight"
    SUCCESS_STORY = "success_story"
    TIPS_AND_TRICKS = "tips_and_tricks"


@dataclass
class GeneratedPost:
    """Data class for generated posts"""
    content: str
    tone: str
    post_type: str
    model_used: str
    generation_time: datetime
    metadata: Dict[str, Any]
    sources_used: List[str]
    
    @property
    def char_count(self) -> int:
        return len(self.content)
    
    @property
    def word_count(self) -> int:
        return len(self.content.split())
    
    @property
    def hashtag_count(self) -> int:
        import re
        return len(re.findall(r'#\w+', self.content))
    
    @property
    def has_emoji(self) -> bool:
        # Simple check for emojis
        return any(ord(c) > 127000 for c in self.content)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return {
            'content': self.content,
            'tone': self.tone,
            'post_type': self.post_type,
            'model_used': self.model_used,
            'generation_time': self.generation_time.isoformat(),
            'metadata': self.metadata,
            'sources_used': self.sources_used,
            'stats': {
                'char_count': self.char_count,
                'word_count': self.word_count,
                'hashtag_count': self.hashtag_count,
                'has_emoji': self.has_emoji
            }
        }


class PostGenerator:
    """Main class for generating LinkedIn posts using AI"""
    
    def __init__(self):
        # Initialize AI clients
        self._init_clients()
        
        # Load prompt templates
        self.prompts = self._load_prompts()
        
        # Default settings
        self.temperature = config.LLM_TEMPERATURE
        self.max_tokens = config.MAX_TOKENS
    
    def _init_clients(self):
        """Initialize AI clients based on available API keys"""
        self.claude_client = None
        self.openai_client = None
        
        # Initialize Claude
        if config.ANTHROPIC_API_KEY:
            self.claude_client = AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
        
        # Initialize OpenAI
        if config.OPENAI_API_KEY:
            self.openai_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    
    def _load_prompts(self) -> Dict[str, str]:
        """Load prompt templates"""
        # These will be loaded from templates/prompts.py later
        # For now, using inline templates
        return {
            'system': """You are an expert LinkedIn content creator specializing in creating 
engaging, professional posts for B2B companies. You understand LinkedIn's best practices 
and create content that drives engagement while maintaining professionalism.""",
            
            'user_template': """Create a LinkedIn post based on the following information:

CONTENT SOURCES:
{sources_summary}

REQUIREMENTS:
- Tone: {tone}
- Post Type: {post_type}
- Maximum Length: {max_length} characters
- Include relevant hashtags (3-5)
- Add 1-3 emojis where appropriate
- Make it engaging and shareable

ADDITIONAL CONTEXT:
{additional_context}

STRUCTURE GUIDELINES:
1. Start with a compelling hook
2. Provide value in the main content
3. End with a call-to-action or thought-provoking question
4. Add relevant hashtags at the end

Generate a LinkedIn post that will resonate with professionals in the industry."""
        }
    
    async def generate(
        self,
        sources: List[ExtractedContent],
        tone: PostTone = PostTone.PROFESSIONAL,
        post_type: PostType = PostType.INFORMATIVE,
        num_variants: int = 1,
        additional_context: Optional[str] = None,
        preferred_model: str = "claude"
    ) -> List[GeneratedPost]:
        """
        Generate LinkedIn posts from extracted content
        
        Args:
            sources: List of ExtractedContent objects
            tone: Desired tone of the post
            post_type: Type of post to generate
            num_variants: Number of variations to generate
            additional_context: Additional instructions or context
            preferred_model: Preferred AI model ('claude' or 'openai')
            
        Returns:
            List of GeneratedPost objects
        """
        # Prepare sources summary
        sources_summary = self._prepare_sources_summary(sources)
        
        # Prepare prompt
        prompt = self._prepare_prompt(
            sources_summary=sources_summary,
            tone=tone.value,
            post_type=post_type.value,
            additional_context=additional_context
        )
        
        # Generate variants
        posts = []
        for i in range(num_variants):
            # Vary temperature slightly for diversity
            temp = self.temperature + (i * 0.1)
            
            try:
                # Try preferred model first
                if preferred_model == "claude" and self.claude_client:
                    post = await self._generate_with_claude(prompt, temp)
                elif preferred_model == "openai" and self.openai_client:
                    post = await self._generate_with_openai(prompt, temp)
                else:
                    # Fallback to available model
                    if self.claude_client:
                        post = await self._generate_with_claude(prompt, temp)
                    elif self.openai_client:
                        post = await self._generate_with_openai(prompt, temp)
                    else:
                        raise ValueError("No AI client available")
                
                # Create GeneratedPost object
                generated_post = GeneratedPost(
                    content=post['content'],
                    tone=tone.value,
                    post_type=post_type.value,
                    model_used=post['model'],
                    generation_time=datetime.now(),
                    metadata={
                        'variant_number': i + 1,
                        'temperature': temp,
                        'prompt_tokens': post.get('prompt_tokens', 0),
                        'completion_tokens': post.get('completion_tokens', 0)
                    },
                    sources_used=[s.source for s in sources]
                )
                
                posts.append(generated_post)
                
            except Exception as e:
                print(f"Error generating variant {i+1}: {str(e)}")
                continue
        
        if not posts:
            raise ValueError("Failed to generate any posts")
        
        return posts
    
    async def _generate_with_claude(self, prompt: str, temperature: float) -> Dict:
        """Generate post using Claude"""
        try:
            response = await self.claude_client.messages.create(
                model=config.CLAUDE_MODEL,
                max_tokens=self.max_tokens,
                temperature=temperature,
                system=self.prompts['system'],
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            content = response.content[0].text
            
            # Process and clean the content
            content = self._process_generated_content(content)
            
            return {
                'content': content,
                'model': config.CLAUDE_MODEL,
                'prompt_tokens': response.usage.input_tokens,
                'completion_tokens': response.usage.output_tokens
            }
            
        except Exception as e:
            raise Exception(f"Claude generation failed: {str(e)}")
    
    async def _generate_with_openai(self, prompt: str, temperature: float) -> Dict:
        """Generate post using OpenAI"""
        try:
            response = await self.openai_client.chat.completions.create(
                model=config.OPENAI_MODEL,
                max_tokens=self.max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": self.prompts['system']},
                    {"role": "user", "content": prompt}
                ]
            )
            
            content = response.choices[0].message.content
            
            # Process and clean the content
            content = self._process_generated_content(content)
            
            return {
                'content': content,
                'model': config.OPENAI_MODEL,
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens
            }
            
        except Exception as e:
            raise Exception(f"OpenAI generation failed: {str(e)}")
    
    def _prepare_sources_summary(self, sources: List[ExtractedContent]) -> str:
        """Prepare a summary of all content sources for the prompt"""
        summaries = []
        
        for i, source in enumerate(sources, 1):
            summary_parts = [f"SOURCE {i}:"]
            
            if source.title:
                summary_parts.append(f"Title: {source.title}")
            
            if source.source_type:
                summary_parts.append(f"Type: {source.source_type}")
            
            # Truncate content to reasonable length for prompt
            content_preview = source.content[:1000] + "..." if len(source.content) > 1000 else source.content
            summary_parts.append(f"Content: {content_preview}")
            
            if source.keywords:
                summary_parts.append(f"Keywords: {', '.join(source.keywords[:10])}")
            
            summaries.append('\n'.join(summary_parts))
        
        return '\n\n'.join(summaries)
    
    def _prepare_prompt(
        self,
        sources_summary: str,
        tone: str,
        post_type: str,
        additional_context: Optional[str] = None
    ) -> str:
        """Prepare the final prompt for the AI model"""
        # Add default hashtags to context
        context_parts = []
        if config.DEFAULT_HASHTAGS:
            context_parts.append(f"Suggested hashtags: {' '.join(config.DEFAULT_HASHTAGS)}")
        
        if additional_context:
            context_parts.append(additional_context)
        
        final_context = '\n'.join(context_parts) if context_parts else "No additional context"
        
        # Format the prompt
        prompt = self.prompts['user_template'].format(
            sources_summary=sources_summary,
            tone=tone,
            post_type=post_type,
            max_length=config.MAX_POST_LENGTH,
            additional_context=final_context
        )
        
        return prompt
    
    def _process_generated_content(self, content: str) -> str:
        """Process and clean generated content"""
        # Remove any markdown formatting
        content = content.replace('**', '').replace('*', '').replace('```', '')
        
        # Ensure content doesn't exceed max length
        if len(content) > config.MAX_POST_LENGTH:
            # Try to cut at a sentence boundary
            sentences = content.split('. ')
            truncated = ""
            for sentence in sentences:
                if len(truncated) + len(sentence) + 2 <= config.MAX_POST_LENGTH - 50:  # Leave room for "..."
                    truncated += sentence + ". "
                else:
                    break
            content = truncated.strip() + "..."
        
        # Ensure hashtags are properly formatted
        import re
        content = re.sub(r'#\s+(\w+)', r'#\1', content)  # Remove spaces after #
        
        return content.strip()
    
    def generate_sync(
        self,
        sources: List[ExtractedContent],
        tone: PostTone = PostTone.PROFESSIONAL,
        post_type: PostType = PostType.INFORMATIVE,
        num_variants: int = 1,
        additional_context: Optional[str] = None,
        preferred_model: str = "claude"
    ) -> List[GeneratedPost]:
        """Synchronous wrapper for generate method"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            self.generate(
                sources=sources,
                tone=tone,
                post_type=post_type,
                num_variants=num_variants,
                additional_context=additional_context,
                preferred_model=preferred_model
            )
        )
        loop.close()
        return result


# Quick generation function
def generate_post(
    sources: List[ExtractedContent],
    tone: str = "professional",
    post_type: str = "informative",
    num_variants: int = 1
) -> List[GeneratedPost]:
    """
    Quick function to generate posts
    
    Args:
        sources: List of extracted content
        tone: Tone of the post
        post_type: Type of post
        num_variants: Number of variants to generate
        
    Returns:
        List of generated posts
    """
    generator = PostGenerator()
    
    # Convert string to enum
    tone_enum = PostTone(tone)
    type_enum = PostType(post_type)
    
    return generator.generate_sync(
        sources=sources,
        tone=tone_enum,
        post_type=type_enum,
        num_variants=num_variants
    )
