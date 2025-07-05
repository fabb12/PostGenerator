"""
Helper Functions - VERSIONE CORRETTA
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
import logging

# Local imports
from config import config

# Setup logging
logger = logging.getLogger(__name__)


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

    try:
        formats = {
            'default': '%Y-%m-%d %H:%M:%S',
            'short': '%m/%d %H:%M',
            'time': '%H:%M',
            'date': '%Y-%m-%d',
            'friendly': '%B %d, %Y at %I:%M %p',
            'iso': '%Y-%m-%dT%H:%M:%S'
        }

        return dt.strftime(formats.get(format_type, formats['default']))
    except Exception as e:
        logger.error(f"Error formatting datetime {dt}: {str(e)}")
        return str(dt)


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

    try:
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

        seconds = int(abs(diff.total_seconds()))

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
    except Exception as e:
        logger.error(f"Error calculating time ago for {dt}: {str(e)}")
        return "Unknown"


def get_optimal_posting_times() -> List[str]:
    """
    Get optimal posting times based on configuration - VERSIONE CORRETTA

    Returns:
        List of optimal posting times in HH:MM format
    """
    # Default times that work for LinkedIn
    default_times = ["09:00", "10:00", "14:00", "15:00"]

    try:
        # Try to get from config
        if hasattr(config, 'OPTIMAL_POSTING_HOURS') and config.OPTIMAL_POSTING_HOURS:
            hours = config.OPTIMAL_POSTING_HOURS

            # Handle different input types
            if isinstance(hours, list):
                formatted_times = []
                for hour in hours:
                    try:
                        h = int(hour)
                        if 0 <= h <= 23:
                            formatted_times.append(f"{h:02d}:00")
                    except (ValueError, TypeError):
                        continue

                # Return formatted times if valid, otherwise default
                if formatted_times:
                    return formatted_times

            elif isinstance(hours, str):
                # Parse comma-separated string
                hour_list = []
                for h in hours.split(','):
                    try:
                        hour_int = int(h.strip())
                        if 0 <= hour_int <= 23:
                            hour_list.append(f"{hour_int:02d}:00")
                    except (ValueError, TypeError):
                        continue

                if hour_list:
                    return hour_list

        # Return default times if config is not available or invalid
        return default_times

    except Exception as e:
        logger.error(f"Error getting optimal posting times: {str(e)}")
        return default_times


def is_business_hours(dt: datetime) -> bool:
    """
    Check if datetime is during business hours

    Args:
        dt: Datetime to check

    Returns:
        True if during business hours
    """
    if not dt:
        return False

    try:
        # Business hours: Monday-Friday, 9 AM - 6 PM
        if dt.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False

        if dt.hour < 9 or dt.hour >= 18:
            return False

        return True
    except Exception as e:
        logger.error(f"Error checking business hours for {dt}: {str(e)}")
        return False


def get_business_hours_today() -> List[str]:
    """
    Get business hours for today in HH:MM format

    Returns:
        List of business hours
    """
    try:
        today = datetime.now()
        if today.weekday() >= 5:  # Weekend
            return []

        business_hours = []
        for hour in range(9, 18):  # 9 AM to 5 PM
            business_hours.append(f"{hour:02d}:00")

        return business_hours
    except Exception as e:
        logger.error(f"Error getting business hours: {str(e)}")
        return []


# ===== URL AND VALIDATION HELPERS =====

def validate_url(url: str) -> bool:
    """
    Validate if a string is a valid URL

    Args:
        url: URL string to validate

    Returns:
        True if valid URL
    """
    if not url or not isinstance(url, str):
        return False

    try:
        # Basic URL validation
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        return validators.url(url)
    except Exception as e:
        logger.debug(f"URL validation failed for {url}: {str(e)}")
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

    try:
        parsed = urlparse(url)
        return 'linkedin.com' in parsed.netloc.lower()
    except Exception as e:
        logger.debug(f"LinkedIn URL validation failed for {url}: {str(e)}")
        return False


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
    except Exception as e:
        logger.debug(f"Domain extraction failed for {url}: {str(e)}")
        return None


def clean_url(url: str) -> str:
    """
    Clean and normalize URL

    Args:
        url: URL to clean

    Returns:
        Cleaned URL
    """
    if not url or not isinstance(url, str):
        return url

    try:
        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        # Remove trailing slashes
        url = url.rstrip('/')

        # Remove common tracking parameters
        tracking_params = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term']

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
    except Exception as e:
        logger.debug(f"URL cleaning failed for {url}: {str(e)}")
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
    if not text or not isinstance(text, str):
        return ""

    try:
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)

        # Fix common encoding issues
        text = text.replace(''', "'").replace(''', "'")
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace('–', '-').replace('—', '-')

        # Remove control characters
        text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F-\x9F]', '', text)

        return text.strip()
    except Exception as e:
        logger.error(f"Text cleaning failed: {str(e)}")
        return str(text) if text else ""


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
    if not text or not isinstance(text, str):
        return text or ""

    try:
        if len(text) <= max_length:
            return text

        # Try to cut at word boundary
        truncated = text[:max_length - len(suffix)]
        last_space = truncated.rfind(' ')

        if last_space > max_length * 0.8:  # If we can find a good word boundary
            truncated = truncated[:last_space]

        return truncated + suffix
    except Exception as e:
        logger.error(f"Text truncation failed: {str(e)}")
        return text[:max_length] if len(text) > max_length else text


def extract_hashtags(text: str) -> List[str]:
    """
    Extract hashtags from text

    Args:
        text: Text to extract hashtags from

    Returns:
        List of hashtags
    """
    if not text or not isinstance(text, str):
        return []

    try:
        hashtags = re.findall(r'#\w+', text)
        return list(set(hashtags))  # Remove duplicates
    except Exception as e:
        logger.error(f"Hashtag extraction failed: {str(e)}")
        return []


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
    if not text or not isinstance(text, str):
        return []

    try:
        mentions = re.findall(r'@\w+', text)
        return list(set(mentions))  # Remove duplicates
    except Exception as e:
        logger.error(f"Mentions extraction failed: {str(e)}")
        return []


def estimate_read_time(text: str, wpm: int = 200) -> int:
    """
    Estimate reading time for text

    Args:
        text: Text to estimate reading time for
        wpm: Words per minute reading speed

    Returns:
        Estimated reading time in seconds
    """
    if not text or not isinstance(text, str):
        return 0

    try:
        word_count = len(text.split())
        minutes = word_count / wpm
        return max(int(minutes * 60), 5)  # Minimum 5 seconds
    except Exception as e:
        logger.error(f"Read time estimation failed: {str(e)}")
        return 5


def get_word_count(text: str) -> int:
    """
    Get word count for text

    Args:
        text: Text to count words in

    Returns:
        Number of words
    """
    if not text or not isinstance(text, str):
        return 0

    try:
        return len(text.split())
    except Exception as e:
        logger.error(f"Word count failed: {str(e)}")
        return 0


def get_char_count(text: str) -> int:
    """
    Get character count for text

    Args:
        text: Text to count characters in

    Returns:
        Number of characters
    """
    try:
        return len(text) if text else 0
    except Exception as e:
        logger.error(f"Character count failed: {str(e)}")
        return 0


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
    try:
        if not views or views == 0:
            return 0.0

        total_interactions = (likes or 0) + (comments or 0) + (shares or 0)
        return (total_interactions / views) * 100
    except Exception as e:
        logger.error(f"Engagement rate calculation failed: {str(e)}")
        return 0.0


def get_post_performance_category(engagement_rate: float) -> str:
    """
    Categorize post performance based on engagement rate

    Args:
        engagement_rate: Engagement rate percentage

    Returns:
        Performance category ('high', 'medium', 'low')
    """
    try:
        if engagement_rate >= 5.0:
            return 'high'
        elif engagement_rate >= 2.0:
            return 'medium'
        else:
            return 'low'
    except Exception as e:
        logger.error(f"Performance categorization failed: {str(e)}")
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
    try:
        if not previous or previous == 0:
            return 0.0 if not current else 100.0

        return ((current - previous) / previous) * 100
    except Exception as e:
        logger.error(f"Growth rate calculation failed: {str(e)}")
        return 0.0


# ===== DATA EXPORT HELPERS =====

def export_posts_to_csv(posts: List) -> str:
    """
    Export posts to CSV format

    Args:
        posts: List of Post objects

    Returns:
        CSV data as string
    """
    try:
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
                getattr(post, 'id', ''),
                getattr(post, 'content', ''),
                getattr(post, 'status', ''),
                getattr(post, 'post_type', ''),
                getattr(post, 'tone', ''),
                format_datetime(getattr(post, 'created_at', None), 'iso'),
                format_datetime(getattr(post, 'published_at', None), 'iso') if getattr(post, 'published_at', None) else '',
                format_datetime(getattr(post, 'scheduled_for', None), 'iso') if getattr(post, 'scheduled_for', None) else '',
                getattr(post, 'model_used', '') or '',
                getattr(post, 'views', 0) or 0,
                getattr(post, 'likes', 0) or 0,
                getattr(post, 'comments', 0) or 0,
                getattr(post, 'shares', 0) or 0,
                getattr(post, 'engagement_rate', 0) or 0,
                ' '.join(getattr(post, 'hashtags', []) or []),
                getattr(post, 'linkedin_post_url', '') or ''
            ])

        return output.getvalue()
    except Exception as e:
        logger.error(f"CSV export failed: {str(e)}")
        return ""


def export_analytics_to_json(analytics_data: Dict) -> str:
    """
    Export analytics data to JSON format

    Args:
        analytics_data: Analytics data dictionary

    Returns:
        JSON data as string
    """
    try:
        return json.dumps(analytics_data, indent=2, default=str)
    except Exception as e:
        logger.error(f"JSON export failed: {str(e)}")
        return "{}"


# ===== FILE HELPERS =====

def ensure_directory_exists(directory: Union[str, Path]) -> Path:
    """
    Ensure directory exists, create if not

    Args:
        directory: Directory path

    Returns:
        Path object
    """
    try:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        return path
    except Exception as e:
        logger.error(f"Directory creation failed for {directory}: {str(e)}")
        return Path(directory)


def get_file_size_mb(file_path: Union[str, Path]) -> float:
    """
    Get file size in MB

    Args:
        file_path: Path to file

    Returns:
        File size in MB
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return 0.0

        return path.stat().st_size / (1024 * 1024)
    except Exception as e:
        logger.error(f"File size calculation failed for {file_path}: {str(e)}")
        return 0.0


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
    try:
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
    except Exception as e:
        logger.error(f"Unique filename generation failed: {str(e)}")
        return f"{base_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{extension}"


# ===== SECURITY HELPERS =====

def generate_hash(text: str) -> str:
    """
    Generate SHA-256 hash of text

    Args:
        text: Text to hash

    Returns:
        Hexadecimal hash string
    """
    try:
        if not text:
            return ""

        return hashlib.sha256(str(text).encode()).hexdigest()
    except Exception as e:
        logger.error(f"Hash generation failed: {str(e)}")
        return ""


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe file system use

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    try:
        if not filename:
            return 'untitled'

        # Remove or replace problematic characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)

        # Remove leading/trailing dots and spaces
        filename = filename.strip(' .')

        # Ensure not empty
        if not filename:
            filename = 'untitled'

        return filename
    except Exception as e:
        logger.error(f"Filename sanitization failed: {str(e)}")
        return 'untitled'


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
    try:
        if not isinstance(number, (int, float)):
            return str(number)

        if compact:
            if number >= 1_000_000:
                return f"{number/1_000_000:.1f}M"
            elif number >= 1_000:
                return f"{number/1_000:.1f}K"

        return f"{number:,}"
    except Exception as e:
        logger.error(f"Number formatting failed: {str(e)}")
        return str(number)


def format_percentage(value: float, decimal_places: int = 1) -> str:
    """
    Format percentage for display

    Args:
        value: Percentage value
        decimal_places: Number of decimal places

    Returns:
        Formatted percentage string
    """
    try:
        if not isinstance(value, (int, float)):
            return "0%"

        return f"{value:.{decimal_places}f}%"
    except Exception as e:
        logger.error(f"Percentage formatting failed: {str(e)}")
        return "0%"


def format_duration(seconds: int) -> str:
    """
    Format duration in seconds to human-readable format

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string
    """
    try:
        if not isinstance(seconds, (int, float)):
            return "0s"

        seconds = int(seconds)

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
    except Exception as e:
        logger.error(f"Duration formatting failed: {str(e)}")
        return "0s"


# ===== CONFIGURATION HELPERS =====

def get_app_version() -> str:
    """
    Get application version

    Returns:
        Version string
    """
    try:
        # This could read from a version file or package metadata
        return "1.0.0"
    except Exception as e:
        logger.error(f"Version retrieval failed: {str(e)}")
        return "1.0.0"


def is_development_mode() -> bool:
    """
    Check if running in development mode

    Returns:
        True if in development mode
    """
    try:
        return getattr(config, 'ENVIRONMENT', 'production') == 'development'
    except Exception as e:
        logger.error(f"Development mode check failed: {str(e)}")
        return False


def get_timezone_list() -> List[str]:
    """
    Get list of common timezones

    Returns:
        List of timezone strings
    """
    try:
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
    except Exception as e:
        logger.error(f"Timezone list retrieval failed: {str(e)}")
        return ['UTC', 'Europe/Rome']


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
    except (TypeError, ValueError, ZeroDivisionError):
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


def safe_str(value: Any, default: str = "") -> str:
    """
    Safely convert value to string

    Args:
        value: Value to convert
        default: Default value if conversion fails

    Returns:
        String value or default
    """
    try:
        return str(value) if value is not None else default
    except Exception:
        return default


# ===== LINKEDIN SPECIFIC HELPERS =====

def get_linkedin_best_practices() -> Dict[str, Any]:
    """
    Get LinkedIn best practices and recommendations

    Returns:
        Dictionary with best practices
    """
    return {
        'optimal_post_length': {
            'min': 50,
            'max': 1300,
            'recommended': 150
        },
        'optimal_posting_times': get_optimal_posting_times(),
        'hashtag_recommendations': {
            'min': 1,
            'max': 5,
            'recommended': 3
        },
        'engagement_tips': [
            'Ask questions to encourage comments',
            'Use relevant hashtags',
            'Post during business hours',
            'Include visual content when possible',
            'Engage with comments quickly'
        ],
        'content_types': [
            'Industry insights',
            'Personal experiences',
            'Company updates',
            'Thought leadership',
            'Educational content'
        ]
    }


def validate_linkedin_post(content: str) -> Dict[str, Any]:
    """
    Validate LinkedIn post content

    Args:
        content: Post content to validate

    Returns:
        Validation results
    """
    try:
        results = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'stats': {
                'length': len(content),
                'words': get_word_count(content),
                'hashtags': count_hashtags(content),
                'mentions': len(extract_mentions(content))
            }
        }

        # Check length
        if len(content) < 10:
            results['errors'].append('Post too short (minimum 10 characters)')
            results['valid'] = False
        elif len(content) > 3000:
            results['errors'].append('Post too long (maximum 3000 characters)')
            results['valid'] = False
        elif len(content) > 1300:
            results['warnings'].append('Post might be too long for optimal engagement')

        # Check hashtags
        hashtag_count = count_hashtags(content)
        if hashtag_count > 10:
            results['warnings'].append('Too many hashtags (recommended: 3-5)')
        elif hashtag_count == 0:
            results['warnings'].append('Consider adding relevant hashtags')

        return results
    except Exception as e:
        logger.error(f"LinkedIn post validation failed: {str(e)}")
        return {
            'valid': False,
            'warnings': [],
            'errors': [f'Validation error: {str(e)}'],
            'stats': {'length': 0, 'words': 0, 'hashtags': 0, 'mentions': 0}
        }


# ===== TESTING HELPERS =====

def run_helper_tests() -> Dict[str, bool]:
    """
    Run basic tests on helper functions

    Returns:
        Dictionary with test results
    """
    tests = {}

    try:
        # Test time functions
        tests['get_optimal_posting_times'] = len(get_optimal_posting_times()) > 0
        tests['format_datetime'] = format_datetime(datetime.now()) != "N/A"

        # Test text functions
        tests['clean_text'] = clean_text("  test  ") == "test"
        tests['extract_hashtags'] = len(extract_hashtags("#test #hashtag")) == 2

        # Test validation functions
        tests['validate_url'] = validate_url("https://example.com") == True
        tests['validate_linkedin_url'] = validate_linkedin_url("https://linkedin.com/in/test") == True

        # Test safe functions
        tests['safe_divide'] = safe_divide(10, 2) == 5.0
        tests['safe_int'] = safe_int("10") == 10

        logger.info(f"Helper tests completed: {sum(tests.values())}/{len(tests)} passed")
        return tests

    except Exception as e:
        logger.error(f"Helper tests failed: {str(e)}")
        return {'error': False}


# Run tests on import if in development mode
if __name__ == "__main__":
    print("Running helper function tests...")
    results = run_helper_tests()
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")