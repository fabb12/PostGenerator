"""
Configuration file for LinkedIn Post Generator
Centralizes all app settings and environment variables
"""

import os
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ===== BASE PATHS =====
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# ===== APP SETTINGS =====
APP_NAME = os.getenv("APP_NAME", "LinkedIn Post Generator")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = os.getenv("DEBUG", "True").lower() == "true"
SECRET_KEY = os.getenv("SECRET_KEY", "default-secret-key-change-in-production")

# ===== API KEYS =====
# Anthropic Claude (primary)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-opus-20240229")

# OpenAI (fallback)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")

# ===== LINKEDIN CREDENTIALS =====
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD")
LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")

# ===== DATABASE =====
DATABASE_PATH = os.getenv("DATABASE_PATH", str(DATA_DIR / "posts.db"))
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# ===== LLM SETTINGS =====
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "500"))

# Model preferences (in order of preference)
LLM_MODELS = {
    "claude": {
        "api_key": ANTHROPIC_API_KEY,
        "model": CLAUDE_MODEL,
        "available": bool(ANTHROPIC_API_KEY)
    },
    "openai": {
        "api_key": OPENAI_API_KEY,
        "model": OPENAI_MODEL,
        "available": bool(OPENAI_API_KEY)
    }
}

# ===== CONTENT EXTRACTION =====
USER_AGENT = os.getenv(
    "USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
)
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "10"))

# ===== LINKEDIN SETTINGS =====
LINKEDIN_RATE_LIMIT_POSTS_PER_DAY = int(
    os.getenv("LINKEDIN_RATE_LIMIT_POSTS_PER_DAY", "10")
)
LINKEDIN_RATE_LIMIT_DELAY_SECONDS = int(
    os.getenv("LINKEDIN_RATE_LIMIT_DELAY_SECONDS", "30")
)

# ===== DEFAULT CONTENT SETTINGS =====
DEFAULT_HASHTAGS = os.getenv(
    "DEFAULT_HASHTAGS", 
    "#logistics,#innovation,#supplychain,#transportation"
).split(",")

MAX_POST_LENGTH = int(os.getenv("MAX_POST_LENGTH", "3000"))
DEFAULT_TONE = os.getenv("DEFAULT_TONE", "professional")
DEFAULT_POST_TYPE = os.getenv("DEFAULT_POST_TYPE", "informative")

# Tone options
TONE_OPTIONS = [
    "professional",
    "friendly",
    "casual",
    "formal",
    "enthusiastic",
    "informative",
    "inspirational"
]

# Post type options
POST_TYPE_OPTIONS = [
    "informative",
    "news_sharing",
    "thought_leadership",
    "company_update",
    "industry_insight",
    "success_story",
    "tips_and_tricks"
]

# ===== SCHEDULING =====
TIMEZONE = os.getenv("TIMEZONE", "Europe/Rome")
OPTIMAL_POSTING_HOURS = [
    int(hour) for hour in 
    os.getenv("OPTIMAL_POSTING_HOURS", "9,10,14,15").split(",")
]

# ===== LOGGING =====
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", str(LOGS_DIR / "app.log"))

# ===== STREAMLIT SETTINGS =====
STREAMLIT_CONFIG = {
    "page_title": APP_NAME,
    "page_icon": "🚀",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

# ===== PROMPT TEMPLATES =====
# System prompts for different LLMs
SYSTEM_PROMPTS = {
    "claude": """You are an expert LinkedIn content creator specializing in creating 
engaging, professional posts for the logistics and transportation industry. 
You understand LinkedIn's best practices and create content that drives engagement.""",
    
    "openai": """You are a professional social media manager specialized in LinkedIn 
content creation for B2B companies in logistics and transportation. Create engaging 
posts that provide value and encourage professional discussion."""
}

# ===== VALIDATION =====
def validate_config():
    """Validate that essential configuration is present"""
    errors = []
    
    # Check for at least one LLM API key
    if not any(model["available"] for model in LLM_MODELS.values()):
        errors.append(
            "No LLM API key found. Please set ANTHROPIC_API_KEY or OPENAI_API_KEY"
        )
    
    # Check LinkedIn credentials
    if not (LINKEDIN_EMAIL and LINKEDIN_PASSWORD):
        if not (LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET):
            errors.append(
                "No LinkedIn credentials found. Please set email/password or OAuth credentials"
            )
    
    return errors

# ===== HELPER FUNCTIONS =====
def get_available_llm():
    """Get the first available LLM configuration"""
    for name, config in LLM_MODELS.items():
        if config["available"]:
            return name, config
    return None, None

def get_llm_config(preferred="claude"):
    """Get LLM configuration with fallback"""
    if LLM_MODELS.get(preferred, {}).get("available"):
        return preferred, LLM_MODELS[preferred]
    return get_available_llm()

# ===== EXPORT CONFIG =====
class Config:
    """Configuration class for easy access"""

    # App
    APP_NAME = APP_NAME
    ENVIRONMENT = ENVIRONMENT
    DEBUG = DEBUG
    SECRET_KEY = SECRET_KEY

    # Paths
    BASE_DIR = BASE_DIR
    DATA_DIR = DATA_DIR
    LOGS_DIR = LOGS_DIR
    DATABASE_PATH = DATABASE_PATH
    DATABASE_URL = DATABASE_URL

    # APIs
    ANTHROPIC_API_KEY = ANTHROPIC_API_KEY
    OPENAI_API_KEY = OPENAI_API_KEY
    CLAUDE_MODEL = CLAUDE_MODEL
    OPENAI_MODEL = OPENAI_MODEL

    # LinkedIn
    LINKEDIN_EMAIL = LINKEDIN_EMAIL
    LINKEDIN_PASSWORD = LINKEDIN_PASSWORD
    LINKEDIN_CLIENT_ID = LINKEDIN_CLIENT_ID
    LINKEDIN_CLIENT_SECRET = LINKEDIN_CLIENT_SECRET

    # LLM
    LLM_TEMPERATURE = LLM_TEMPERATURE
    MAX_TOKENS = MAX_TOKENS
    LLM_MODELS = LLM_MODELS

    # Content Extraction
    USER_AGENT = USER_AGENT
    REQUEST_TIMEOUT = REQUEST_TIMEOUT

    # LinkedIn Settings
    LINKEDIN_RATE_LIMIT_POSTS_PER_DAY = LINKEDIN_RATE_LIMIT_POSTS_PER_DAY
    LINKEDIN_RATE_LIMIT_DELAY_SECONDS = LINKEDIN_RATE_LIMIT_DELAY_SECONDS

    # Content
    DEFAULT_HASHTAGS = DEFAULT_HASHTAGS
    MAX_POST_LENGTH = MAX_POST_LENGTH
    DEFAULT_TONE = DEFAULT_TONE
    DEFAULT_POST_TYPE = DEFAULT_POST_TYPE

    # Scheduling
    TIMEZONE = TIMEZONE
    OPTIMAL_POSTING_HOURS = OPTIMAL_POSTING_HOURS

    # Logging
    LOG_LEVEL = LOG_LEVEL
    LOG_FILE = LOG_FILE

    # Options
    TONE_OPTIONS = TONE_OPTIONS
    POST_TYPE_OPTIONS = POST_TYPE_OPTIONS

    # Streamlit
    STREAMLIT_CONFIG = STREAMLIT_CONFIG

    # Prompts
    SYSTEM_PROMPTS = SYSTEM_PROMPTS

    # Methods
    @staticmethod
    def validate():
        return validate_config()

    @staticmethod
    def get_llm_config(preferred="claude"):
        return get_llm_config(preferred)
# Create singleton instance
config = Config()

# Validate on import (only show warnings in development)
if ENVIRONMENT == "development":
    validation_errors = validate_config()
    if validation_errors:
        print("⚠️  Configuration warnings:")
        for error in validation_errors:
            print(f"   - {error}")
