"""
Prompt Templates for AI Post Generation
Contains structured prompts for different post types and scenarios
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class PromptTemplate:
    """Structure for prompt templates"""
    name: str
    system_prompt: str
    user_prompt: str
    description: str
    example_output: Optional[str] = None
    
    def format(self, **kwargs) -> Dict[str, str]:
        """Format the prompts with provided variables"""
        return {
            'system': self.system_prompt,
            'user': self.user_prompt.format(**kwargs)
        }


class PromptLibrary:
    """Collection of prompt templates for different scenarios"""
    
    # System prompts for different AI models
    SYSTEM_PROMPTS = {
        'claude': """You are an expert LinkedIn content strategist with deep knowledge of B2B marketing 
and professional networking. You create engaging, valuable content that resonates with business 
professionals while maintaining authenticity and professionalism. You understand LinkedIn's 
algorithm favors posts that spark meaningful conversations and provide genuine value.

Your writing style is:
- Clear and concise, avoiding jargon unless necessary
- Engaging without being clickbait
- Professional yet personable
- Data-driven when possible
- Always ending with engagement-driving elements""",

        'openai': """You are a professional LinkedIn content creator specializing in B2B communications. 
Your goal is to create posts that provide value, build thought leadership, and encourage 
professional engagement. You write in a clear, professional tone that resonates with business 
audiences while remaining approachable and authentic.""",

        'general': """You are a skilled social media content creator focused on LinkedIn. 
Create professional, engaging posts that provide value to business professionals and 
encourage meaningful discussions."""
    }
    
    # Base template for all post types
    BASE_TEMPLATE = """Create a LinkedIn post based on the following information:

CONTENT SOURCES:
{sources_summary}

POST REQUIREMENTS:
- Tone: {tone}
- Type: {post_type}
- Length: {min_length}-{max_length} characters
- Target Audience: {target_audience}

FORMATTING GUIDELINES:
- Start with an attention-grabbing hook
- Use short paragraphs for readability
- Include 1-3 relevant emojis
- Add 3-5 relevant hashtags at the end
- Use line breaks for visual appeal
- Include a call-to-action or question

ADDITIONAL CONTEXT:
{additional_context}

{type_specific_instructions}

Please generate an engaging LinkedIn post that will resonate with professionals."""

    # Post type specific templates
    POST_TYPE_TEMPLATES = {
        'informative': {
            'instructions': """INFORMATIVE POST GUIDELINES:
- Share valuable insights or knowledge
- Use data or statistics when available
- Break down complex topics simply
- Provide actionable takeaways
- Position as educational content""",
            'example_structure': """
Hook: Did you know that [surprising fact]?

Context: [Brief background]

Key Points:
• [Point 1]
• [Point 2]
• [Point 3]

Takeaway: [Main lesson]

Question: [Engagement question]

#Hashtags
"""
        },
        
        'news_sharing': {
            'instructions': """NEWS SHARING GUIDELINES:
- Summarize the key news clearly
- Add your unique perspective
- Explain why it matters to your audience
- Connect to broader industry trends
- Cite the source appropriately""",
            'example_structure': """
📰 Breaking: [News headline]

What happened: [Brief summary]

Why it matters: [Your analysis]

My take: [Personal perspective]

What's your view on this development?

Source: [Link]
#Hashtags
"""
        },
        
        'thought_leadership': {
            'instructions': """THOUGHT LEADERSHIP GUIDELINES:
- Share a unique perspective or insight
- Challenge conventional thinking
- Back up claims with experience or data
- Be bold but respectful
- Invite discussion and debate""",
            'example_structure': """
[Contrarian or bold statement]

Here's what I've learned: [Personal insight]

[Supporting evidence or experience]

The bigger picture: [Industry implications]

But here's the real question: [Thought-provoking question]

#ThoughtLeadership #Hashtags
"""
        },
        
        'company_update': {
            'instructions': """COMPANY UPDATE GUIDELINES:
- Lead with the human element
- Show impact, not just activity
- Include specific achievements
- Thank team members when relevant
- Connect to company mission/values""",
            'example_structure': """
🎉 Exciting news from [Company]!

[Main announcement]

What this means: [Impact/Benefits]

Proud of: [Team/Achievement highlight]

Next steps: [What's coming]

[Question or invitation to connect]

#CompanyNews #Hashtags
"""
        },
        
        'industry_insight': {
            'instructions': """INDUSTRY INSIGHT GUIDELINES:
- Identify a trend or pattern
- Provide specific examples
- Offer analysis, not just observation
- Include data when possible
- Project future implications""",
            'example_structure': """
🔍 Spotted an interesting trend in [industry]:

[Observation]

Evidence:
→ [Example 1]
→ [Example 2]

What's driving this: [Analysis]

Where we're heading: [Future prediction]

Are you seeing this too?

#IndustryTrends #Hashtags
"""
        },
        
        'success_story': {
            'instructions': """SUCCESS STORY GUIDELINES:
- Start with the outcome
- Include specific challenges faced
- Detail the solution or approach
- Share lessons learned
- Make it relatable to others""",
            'example_structure': """
🚀 [Impressive outcome achieved]

The challenge: [What we faced]

Our approach:
1. [Step 1]
2. [Step 2]
3. [Step 3]

Key lesson: [What we learned]

What challenges are you tackling?

#SuccessStory #Hashtags
"""
        },
        
        'tips_and_tricks': {
            'instructions': """TIPS AND TRICKS GUIDELINES:
- Provide immediately actionable advice
- Use numbered or bulleted lists
- Include specific examples
- Keep tips concise and clear
- Save the best tip for last""",
            'example_structure': """
💡 [Number] [Topic] tips that [benefit]:

1️⃣ [Tip 1]
   → [Quick explanation]

2️⃣ [Tip 2]
   → [Quick explanation]

3️⃣ [Tip 3]
   → [Quick explanation]

Bonus tip: [Extra valuable tip]

Which tip will you try first?

#ProfessionalTips #Hashtags
"""
        }
    }
    
    # Tone modifiers
    TONE_MODIFIERS = {
        'professional': "Maintain a polished, business-appropriate tone while being approachable.",
        'friendly': "Use a warm, conversational tone as if talking to a colleague over coffee.",
        'casual': "Keep it relaxed and informal while still being respectful and professional.",
        'formal': "Use formal business language appropriate for executive-level communication.",
        'enthusiastic': "Show genuine excitement and energy while maintaining professionalism.",
        'informative': "Focus on educating and providing value with a neutral, expert tone.",
        'inspirational': "Use motivational language to inspire and encourage your audience."
    }
    
    # Hashtag suggestions by industry
    HASHTAG_SUGGESTIONS = {
        'logistics': ['#Logistics', '#SupplyChain', '#Transportation', '#Freight', '#Shipping'],
        'technology': ['#Tech', '#Innovation', '#DigitalTransformation', '#AI', '#Technology'],
        'general': ['#Business', '#Leadership', '#ProfessionalDevelopment', '#Industry', '#Growth'],
        'sustainability': ['#Sustainability', '#ESG', '#GreenBusiness', '#CircularEconomy', '#NetZero']
    }
    
    @classmethod
    def get_prompt(
        cls,
        sources_summary: str,
        tone: str = 'professional',
        post_type: str = 'informative',
        target_audience: str = 'business professionals',
        min_length: int = 200,
        max_length: int = 3000,
        additional_context: str = "",
        model: str = 'claude'
    ) -> Dict[str, str]:
        """
        Get formatted prompt for post generation
        
        Returns:
            Dict with 'system' and 'user' prompts
        """
        # Get system prompt
        system_prompt = cls.SYSTEM_PROMPTS.get(model, cls.SYSTEM_PROMPTS['general'])
        
        # Add tone modifier to system prompt
        if tone in cls.TONE_MODIFIERS:
            system_prompt += f"\n\nTone guidance: {cls.TONE_MODIFIERS[tone]}"
        
        # Get type-specific instructions
        type_info = cls.POST_TYPE_TEMPLATES.get(post_type, cls.POST_TYPE_TEMPLATES['informative'])
        type_specific_instructions = type_info['instructions']
        
        # Add example structure to additional context
        if additional_context:
            additional_context += f"\n\nExample Structure:\n{type_info['example_structure']}"
        else:
            additional_context = f"Example Structure:\n{type_info['example_structure']}"
        
        # Format user prompt
        user_prompt = cls.BASE_TEMPLATE.format(
            sources_summary=sources_summary,
            tone=tone,
            post_type=post_type,
            min_length=min_length,
            max_length=max_length,
            target_audience=target_audience,
            additional_context=additional_context,
            type_specific_instructions=type_specific_instructions
        )
        
        return {
            'system': system_prompt,
            'user': user_prompt
        }
    
    @classmethod
    def get_refinement_prompt(cls, original_post: str, feedback: str) -> str:
        """Get prompt for refining an existing post based on feedback"""
        return f"""Please refine this LinkedIn post based on the feedback provided:

ORIGINAL POST:
{original_post}

FEEDBACK:
{feedback}

Please generate an improved version that addresses the feedback while maintaining 
the core message and professional tone. Ensure the refined post:
- Addresses all feedback points
- Maintains LinkedIn best practices
- Keeps the same general length
- Preserves any important information from the original
"""

    @classmethod
    def get_hashtag_prompt(cls, post_content: str, industry: str = 'general') -> str:
        """Get prompt for generating relevant hashtags"""
        suggestions = cls.HASHTAG_SUGGESTIONS.get(industry, cls.HASHTAG_SUGGESTIONS['general'])
        
        return f"""Suggest 5 relevant hashtags for this LinkedIn post:

POST:
{post_content}

INDUSTRY: {industry}

Consider these popular hashtags: {', '.join(suggestions)}

Provide 5 hashtags that are:
- Relevant to the content
- Mix of broad and specific
- Likely to increase visibility
- Professional and appropriate

Format: Return only the hashtags, separated by spaces."""


# Pre-configured templates for common scenarios
QUICK_TEMPLATES = {
    'announcement': PromptTemplate(
        name="Company Announcement",
        system_prompt=PromptLibrary.SYSTEM_PROMPTS['claude'],
        user_prompt="""Create an exciting company announcement post:

NEWS: {announcement}
TONE: Enthusiastic but professional
LENGTH: 200-300 words

Include:
- Attention-grabbing opening
- Key details
- Impact/benefits
- Call-to-action
- 3-5 relevant hashtags""",
        description="For major company announcements",
        example_output="""🎉 Big news! [Company] is thrilled to announce...

[Details of announcement]

This means [impact/benefits for audience]

We're excited about [future possibilities]

Learn more: [CTA]

#CompanyNews #Innovation #Growth"""
    ),
    
    'weekly_insight': PromptTemplate(
        name="Weekly Industry Insight",
        system_prompt=PromptLibrary.SYSTEM_PROMPTS['claude'],
        user_prompt="""Create a weekly industry insight post:

TOPIC: {topic}
DATA/TRENDS: {data}
TONE: Informative and engaging

Structure:
- Hook with surprising stat or question
- 3 key insights
- Practical takeaway
- Discussion question
- Relevant hashtags""",
        description="For regular industry insight posts",
        example_output="""📊 This week's logistics insight...

[Hook]

3 things worth noting:
1. [Insight 1]
2. [Insight 2]  
3. [Insight 3]

The takeaway: [Action item]

What trends are you seeing?

#WeeklyInsight #Logistics #IndustryTrends"""
    ),
    
    'quick_tip': PromptTemplate(
        name="Quick Professional Tip",
        system_prompt=PromptLibrary.SYSTEM_PROMPTS['claude'],
        user_prompt="""Create a quick tip post:

TIP TOPIC: {topic}
BENEFIT: {benefit}

Keep it:
- Under 150 words
- Immediately actionable
- With specific example
- Engaging opener
- Clear value prop""",
        description="For short, valuable tip posts",
        example_output="""💡 Quick tip for [audience]:

[Problem/Pain point]

Try this: [Solution]

Example: [Specific implementation]

Takes 5 minutes, saves hours.

What's your favorite [topic] hack?

#QuickTip #Productivity #ProfessionalDevelopment"""
    )
}


def get_custom_prompt(
    template_name: str,
    **kwargs
) -> Dict[str, str]:
    """
    Get a pre-configured template with custom values
    
    Args:
        template_name: Name of the template from QUICK_TEMPLATES
        **kwargs: Variables to fill in the template
        
    Returns:
        Dict with formatted system and user prompts
    """
    if template_name not in QUICK_TEMPLATES:
        raise ValueError(f"Template '{template_name}' not found")
    
    template = QUICK_TEMPLATES[template_name]
    return template.format(**kwargs)
