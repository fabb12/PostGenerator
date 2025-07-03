"""
Helper Functions
Utility functions used throughout the LinkedIn Post Generator application
"""

import re
import csv
import io
import hashlib
import json
from datetime import datetime, timedelta, time
from typing import List, Dict, Optional, Any, Union
from urllib.parse import urlparse
import validators
import pandas as pd
from pathlib import Path

# Local imports
from config import config


# ===== DATE AND TIME HELPERS =====

def format_datetime(dt: datetime, format_type: str = 'default') -> str:
    """
    Format datetime for display
    
    Args:
        dt: Datetime object to format
        format_type: Type of formatting ('default', 'short', 'time', 'date')
        
    Returns:
        Formatted datetime string
    """
    if not dt:
        return "N/A"
    
    formats = {
        'default': '%Y-%m-%d %H:%M:%S',
        'short': '%m/%d %H:%M',
        'time': '%H:%M',
        'date': '%Y-%m-%d',
        'friendly': '%B %d, %Y at %I:%M %p',
        'iso': '%Y-%m-%dT%H:%M:%S'
    }
    
    return dt.strftime(formats.get(format_type, formats['default']))


def get_time_ago(dt: datetime, future: bool = False) -> str:
    """
    Get human-readable time difference
    
    Args:
        dt: Datetime to compare
        future: Whether the datetime is in the future
        
    Returns:
        Human-readable time difference string
    """
    if not dt:
        return "Unknown"
    
    now = datetime.now()
    
    if future:
        diff = dt - now
        prefix = "in "
        suffix = ""
    else:
        diff = now - dt
        prefix = ""
        suffix = " ago"
    
    if diff.total_seconds() < 0:
        return "just now"
    
    seconds = int(diff.total_seconds())
    
    if seconds < 60:
        return f"{prefix}{seconds} seconds{suffix}"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{prefix}{minutes} minute{'s' if minutes != 1 else ''}{suffix}"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{prefix}{hours} hour{'s' if hours != 1 else ''}{suffix}"
    else:
        days = seconds // 86400
        return f"{prefix}{days} day{'s' if days != 1 else ''}{suffix}"


def get_optimal_posting_times() -> List[str]:
    """
    Get optimal posting times based on configuration
    
    Returns:
        List of optimal posting times in HH:MM format
    """
    return [f"{hour:02d}:00" for hour in config.OPTIMAL_POSTING_HOURS]


def is_business_hours(dt: datetime) -> bool:
    """
    Check if datetime is during business hours
    
    Args:
        dt: Datetime to check
        
    Returns:
        True if during business hours
    """
    # Business hours: Monday-Friday, 9 AM - 6 PM
    if dt.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False
    
    if dt.hour < 9 or dt.hour >= 18:
        return False
    
    return True


# ===== URL AND VALIDATION HELPERS =====

def validate_url(url: str) -> bool:
    """
    Validate if a string is a valid URL
    
    Args:
        url: URL string to validate
        
    Returns:
        True if valid URL
    """
    if not url:
        return False
    
    try:
        return validators.url(url)
    except:
        return False


def validate_linkedin_url(url: str) -> bool:
    """
    Validate if URL is a LinkedIn URL
    
    Args:
        url: URL to validate
        
    Returns:
        True if valid LinkedIn URL
    """
    if not validate_url(url):
        return False
    
    parsed = urlparse(url)
    return 'linkedin.com' in parsed.netloc.lower()


def extract_domain(url: str) -> Optional[str]:
    """
    Extract domain from URL
    
    Args:
        url: URL to extract domain from
        
    Returns:
        Domain string or None
    """
    if not validate_url(url):
        return None
    
    try:
        parsed = urlparse(url)
        return parsed.netloc
    except:
        return None


def clean_url(url: str) -> str:
    """
    Clean and normalize URL
    
    Args:
        url: URL to clean
        
    Returns:
        Cleaned URL
    """
    if not url:
        return url
    
    # Add protocol if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Remove trailing slashes
    url = url.rstrip('/')
    
    # Remove common tracking parameters
    tracking_params = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term']
    
    try:
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        # Remove tracking parameters
        for param in tracking_params:
            query_params.pop(param, None)
        
        # Rebuild URL
        new_query = urlencode(query_params, doseq=True)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, 
                          parsed.params, new_query, parsed.fragment))
    except:
        return url


# ===== TEXT PROCESSING HELPERS =====

def clean_text(text: str) -> str:
    """
    Clean and normalize text content
    
    Args:
        text: Text to clean
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Fix common encoding issues
    text = text.replace(''', "'").replace(''', "'")
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace('–', '-').replace('—', '-')
    
    # Remove control characters
    text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F-\x9F]', '', text)
    
    return text.strip()


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to maximum length
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if not text or len(text) <= max_length:
        return text
    
    # Try to cut at word boundary
    truncated = text[:max_length - len(suffix)]
    last_space = truncated.rfind(' ')
    
    if last_space > max_length * 0.8:  # If we can find a good word boundary
        truncated = truncated[:last_space]
    
    return truncated + suffix


def extract_hashtags(text: str) -> List[str]:
    """
    Extract hashtags from text
    
    Args:
        text: Text to extract hashtags from
        
    Returns:
        List of hashtags
    """
    if not text:
        return []
    
    hashtags = re.findall(r'#\w+', text)
    return list(set(hashtags))  # Remove duplicates


def count_hashtags(text: str) -> int:
    """
    Count hashtags in text
    
    Args:
        text: Text to count hashtags in
        
    Returns:
        Number of hashtags
    """
    return len(extract_hashtags(text))


def extract_mentions(text: str) -> List[str]:
    """
    Extract @mentions from text
    
    Args:
        text: Text to extract mentions from
        
    Returns:
        List of mentions
    """
    if not text:
        return []
    
    mentions = re.findall(r'@\w+', text)
    return list(set(mentions))  # Remove duplicates


def estimate_read_time(text: str, wpm: int = 200) -> int:
    """
    Estimate reading time for text
    
    Args:
        text: Text to estimate reading time for
        wpm: Words per minute reading speed
        
    Returns:
        Estimated reading time in seconds
    """
    if not text:
        return 0
    
    word_count = len(text.split())
    minutes = word_count / wpm
    return max(int(minutes * 60), 5)  # Minimum 5 seconds


def get_word_count(text: str) -> int:
    """
    Get word count for text
    
    Args:
        text: Text to count words in
        
    Returns:
        Number of words
    """
    if not text:
        return 0
    
    return len(text.split())


def get_char_count(text: str) -> int:
    """
    Get character count for text
    
    Args:
        text: Text to count characters in
        
    Returns:
        Number of characters
    """
    return len(text) if text else 0


# ===== ANALYTICS HELPERS =====

def calculate_engagement_rate(views: int, likes: int, comments: int, shares: int) -> float:
    """
    Calculate engagement rate
    
    Args:
        views: Number of views
        likes: Number of likes
        comments: Number of comments
        shares: Number of shares
        
    Returns:
        Engagement rate as percentage
    """
    if not views or views == 0:
        return 0.0
    
    total_interactions = (likes or 0) + (comments or 0) + (shares or 0)
    return (total_interactions / views) * 100


def get_post_performance_category(engagement_rate: float) -> str:
    """
    Categorize post performance based on engagement rate
    
    Args:
        engagement_rate: Engagement rate percentage
        
    Returns:
        Performance category ('high', 'medium', 'low')
    """
    if engagement_rate >= 5.0:
        return 'high'
    elif engagement_rate >= 2.0:
        return 'medium'
    else:
        return 'low'


def calculate_growth_rate(current: float, previous: float) -> float:
    """
    Calculate growth rate between two values
    
    Args:
        current: Current value
        previous: Previous value
        
    Returns:
        Growth rate as percentage
    """
    if not previous or previous == 0:
        return 0.0 if not current else 100.0
    
    return ((current - previous) / previous) * 100


# ===== DATA EXPORT HELPERS =====

def export_posts_to_csv(posts: List) -> str:
    """
    Export posts to CSV format
    
    Args:
        posts: List of Post objects
        
    Returns:
        CSV data as string
    """
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'ID', 'Content', 'Status', 'Post Type', 'Tone', 'Created At',
        'Published At', 'Scheduled For', 'Model Used', 'Views', 'Likes',
        'Comments', 'Shares', 'Engagement Rate', 'Hashtags', 'LinkedIn URL'
    ])
    
    # Data rows
    for post in posts:
        writer.writerow([
            post.id,
            post.content,
            post.status,
            post.post_type,
            post.tone,
            format_datetime(post.created_at, 'iso'),
            format_datetime(post.published_at, 'iso') if post.published_at else '',
            format_datetime(post.scheduled_for, 'iso') if post.scheduled_for else '',
            post.model_used or '',
            post.views or 0,
            post.likes or 0,
            post.comments or 0,
            post.shares or 0,
            post.engagement_rate or 0,
            ' '.join(post.hashtags) if post.hashtags else '',
            post.linkedin_post_url or ''
        ])
    
    return output.getvalue()


def export_analytics_to_json(analytics_data: Dict) -> str:
    """
    Export analytics data to JSON format
    
    Args:
        analytics_data: Analytics data dictionary
        
    Returns:
        JSON data as string
    """
    return json.dumps(analytics_data, indent=2, default=str)


# ===== FILE HELPERS =====

def ensure_directory_exists(directory: Union[str, Path]) -> Path:
    """
    Ensure directory exists, create if not
    
    Args:
        directory: Directory path
        
    Returns:
        Path object
    """
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_file_size_mb(file_path: Union[str, Path]) -> float:
    """
    Get file size in MB
    
    Args:
        file_path: Path to file
        
    Returns:
        File size in MB
    """
    path = Path(file_path)
    if not path.exists():
        return 0.0
    
    return path.stat().st_size / (1024 * 1024)


def generate_unique_filename(base_name: str, extension: str = '', directory: Union[str, Path] = None) -> str:
    """
    Generate unique filename
    
    Args:
        base_name: Base filename
        extension: File extension
        directory: Directory to check for existing files
        
    Returns:
        Unique filename
    """
    if directory:
        directory = Path(directory)
    else:
        directory = Path.cwd()
    
    counter = 1
    original_name = f"{base_name}{extension}"
    filename = original_name
    
    while (directory / filename).exists():
        filename = f"{base_name}_{counter}{extension}"
        counter += 1
    
    return filename


# ===== SECURITY HELPERS =====

def generate_hash(text: str) -> str:
    """
    Generate SHA-256 hash of text
    
    Args:
        text: Text to hash
        
    Returns:
        Hexadecimal hash string
    """
    if not text:
        return ""
    
    return hashlib.sha256(text.encode()).hexdigest()


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe file system use
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove or replace problematic characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove leading/trailing dots and spaces
    filename = filename.strip(' .')
    
    # Ensure not empty
    if not filename:
        filename = 'untitled'
    
    return filename


# ===== FORMATTING HELPERS =====

def format_number(number: Union[int, float], compact: bool = False) -> str:
    """
    Format number for display
    
    Args:
        number: Number to format
        compact: Whether to use compact notation (1K, 1M)
        
    Returns:
        Formatted number string
    """
    if not isinstance(number, (int, float)):
        return str(number)
    
    if compact:
        if number >= 1_000_000:
            return f"{number/1_000_000:.1f}M"
        elif number >= 1_000:
            return f"{number/1_000:.1f}K"
    
    return f"{number:,}"


def format_percentage(value: float, decimal_places: int = 1) -> str:
    """
    Format percentage for display
    
    Args:
        value: Percentage value
        decimal_places: Number of decimal places
        
    Returns:
        Formatted percentage string
    """
    if not isinstance(value, (int, float)):
        return "0%"
    
    return f"{value:.{decimal_places}f}%"


def format_duration(seconds: int) -> str:
    """
    Format duration in seconds to human-readable format
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds}s"
    else:
        hours = seconds // 3600
        remaining_minutes = (seconds % 3600) // 60
        return f"{hours}h {remaining_minutes}m"


# ===== CONFIGURATION HELPERS =====

def get_app_version() -> str:
    """
    Get application version
    
    Returns:
        Version string
    """
    # This could read from a version file or package metadata
    return "1.0.0"


def is_development_mode() -> bool:
    """
    Check if running in development mode
    
    Returns:
        True if in development mode
    """
    return config.ENVIRONMENT == 'development'


def get_timezone_list() -> List[str]:
    """
    Get list of common timezones
    
    Returns:
        List of timezone strings
    """
    return [
        'UTC',
        'Europe/Rome',
        'Europe/London',
        'Europe/Paris',
        'Europe/Berlin',
        'America/New_York',
        'America/Los_Angeles',
        'America/Chicago',
        'America/Toronto',
        'Asia/Tokyo',
        'Asia/Shanghai',
        'Asia/Dubai',
        'Australia/Sydney'
    ]


# ===== ERROR HANDLING HELPERS =====

def safe_divide(numerator: Union[int, float], denominator: Union[int, float], default: float = 0.0) -> float:
    """
    Safely divide two numbers, avoiding division by zero
    
    Args:
        numerator: Numerator
        denominator: Denominator
        default: Default value if division by zero
        
    Returns:
        Division result or default
    """
    try:
        if denominator == 0:
            return default
        return numerator / denominator
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """
    Safely convert value to integer
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Integer value or default
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """
    Safely convert value to float
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Float value or default
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
