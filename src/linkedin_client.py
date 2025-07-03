"""
LinkedIn Client Module
Handles publishing posts to LinkedIn using various methods:
- linkedin-api (unofficial but functional)
- LinkedIn Official API (OAuth-based)
- Manual workflow support
"""

import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import requests
import re
from urllib.parse import urlencode

# LinkedIn API (unofficial)
try:
    from linkedin_api import Linkedin
except ImportError:
    Linkedin = None

# Local imports
from config import config
from src.database import db, Post


@dataclass
class PublishResult:
    """Result of a LinkedIn post publishing attempt"""
    success: bool
    post_id: Optional[str] = None
    post_url: Optional[str] = None
    error_message: Optional[str] = None
    response_data: Optional[Dict] = None
    method_used: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return {
            'success': self.success,
            'post_id': self.post_id,
            'post_url': self.post_url,
            'error_message': self.error_message,
            'method_used': self.method_used,
            'timestamp': datetime.now().isoformat()
        }


@dataclass
class LinkedInPost:
    """Structure for LinkedIn post data"""
    content: str
    visibility: str = "PUBLIC"
    media_urls: List[str] = None
    hashtags: List[str] = None
    
    def __post_init__(self):
        if self.media_urls is None:
            self.media_urls = []
        if self.hashtags is None:
            self.hashtags = []
    
    @property
    def content_with_hashtags(self) -> str:
        """Get content with hashtags appended"""
        content = self.content
        if self.hashtags:
            content += "\n\n" + " ".join(self.hashtags)
        return content


class LinkedInPublisher:
    """Main class for publishing to LinkedIn"""
    
    def __init__(self):
        self.email = config.LINKEDIN_EMAIL
        self.password = config.LINKEDIN_PASSWORD
        self.client_id = config.LINKEDIN_CLIENT_ID
        self.client_secret = config.LINKEDIN_CLIENT_SECRET
        
        # Rate limiting
        self.last_post_time = None
        self.posts_today = 0
        self.daily_limit = config.LINKEDIN_RATE_LIMIT_POSTS_PER_DAY
        self.delay_between_posts = config.LINKEDIN_RATE_LIMIT_DELAY_SECONDS
        
        # LinkedIn API client (unofficial)
        self._linkedin_client = None
        self._authenticated = False
    
    def authenticate(self) -> bool:
        """
        Authenticate with LinkedIn using available credentials
        
        Returns:
            True if authentication successful
        """
        if not self.email or not self.password:
            return False
        
        try:
            if Linkedin is None:
                raise ImportError("linkedin-api not installed")
            
            # Initialize unofficial LinkedIn client
            self._linkedin_client = Linkedin(
                username=self.email,
                password=self.password
            )
            
            # Test authentication by getting profile
            profile = self._linkedin_client.get_profile()
            if profile:
                self._authenticated = True
                return True
            
        except Exception as e:
            print(f"LinkedIn authentication failed: {str(e)}")
            self._authenticated = False
        
        return False
    
    def is_authenticated(self) -> bool:
        """Check if client is authenticated"""
        return self._authenticated
    
    def can_post_now(self) -> Tuple[bool, str]:
        """
        Check if we can post now based on rate limits
        
        Returns:
            Tuple of (can_post, reason_if_not)
        """
        # Check daily limit
        if self.posts_today >= self.daily_limit:
            return False, f"Daily limit reached ({self.daily_limit} posts)"
        
        # Check time delay between posts
        if self.last_post_time:
            time_since_last = datetime.now() - self.last_post_time
            if time_since_last.total_seconds() < self.delay_between_posts:
                wait_time = self.delay_between_posts - time_since_last.total_seconds()
                return False, f"Must wait {wait_time:.0f} seconds between posts"
        
        return True, ""
    
    async def publish_post(
        self,
        post_content: str,
        media_urls: List[str] = None,
        hashtags: List[str] = None,
        visibility: str = "PUBLIC"
    ) -> PublishResult:
        """
        Publish a post to LinkedIn
        
        Args:
            post_content: Text content of the post
            media_urls: Optional list of media URLs
            hashtags: Optional list of hashtags
            visibility: Post visibility (PUBLIC, CONNECTIONS)
            
        Returns:
            PublishResult with success status and details
        """
        # Create LinkedIn post object
        linkedin_post = LinkedInPost(
            content=post_content,
            visibility=visibility,
            media_urls=media_urls or [],
            hashtags=hashtags or []
        )
        
        # Check rate limits
        can_post, reason = self.can_post_now()
        if not can_post:
            return PublishResult(
                success=False,
                error_message=f"Rate limit: {reason}",
                method_used="rate_limit_check"
            )
        
        # Try different publishing methods in order
        methods = [
            self._publish_with_unofficial_api,
            self._publish_with_official_api,
            self._prepare_manual_workflow
        ]
        
        for method in methods:
            try:
                result = await method(linkedin_post)
                if result.success:
                    # Update rate limiting
                    self.last_post_time = datetime.now()
                    self.posts_today += 1
                    return result
            except Exception as e:
                continue
        
        return PublishResult(
            success=False,
            error_message="All publishing methods failed",
            method_used="all_methods"
        )
    
    async def _publish_with_unofficial_api(self, post: LinkedInPost) -> PublishResult:
        """Publish using unofficial linkedin-api"""
        if not self._authenticated:
            if not self.authenticate():
                return PublishResult(
                    success=False,
                    error_message="Authentication failed",
                    method_used="unofficial_api"
                )
        
        try:
            # Prepare content
            content = post.content_with_hashtags
            
            # Post to LinkedIn
            response = self._linkedin_client.post_update(
                text=content,
                visibility=post.visibility
            )
            
            # Extract post ID and URL from response
            post_id = self._extract_post_id_from_response(response)
            post_url = self._build_post_url(post_id) if post_id else None
            
            return PublishResult(
                success=True,
                post_id=post_id,
                post_url=post_url,
                response_data=response,
                method_used="unofficial_api"
            )
            
        except Exception as e:
            return PublishResult(
                success=False,
                error_message=f"Unofficial API error: {str(e)}",
                method_used="unofficial_api"
            )
    
    async def _publish_with_official_api(self, post: LinkedInPost) -> PublishResult:
        """Publish using official LinkedIn API (OAuth)"""
        if not self.client_id or not self.client_secret:
            return PublishResult(
                success=False,
                error_message="OAuth credentials not configured",
                method_used="official_api"
            )
        
        # This would require OAuth flow implementation
        # For now, return as not implemented
        return PublishResult(
            success=False,
            error_message="Official API not yet implemented - requires OAuth setup",
            method_used="official_api"
        )
    
    async def _prepare_manual_workflow(self, post: LinkedInPost) -> PublishResult:
        """Prepare content for manual posting"""
        # This creates a formatted post for manual copy-paste
        formatted_content = self._format_for_manual_posting(post)
        
        return PublishResult(
            success=True,
            post_id="manual_" + str(int(time.time())),
            post_url=None,
            response_data={"formatted_content": formatted_content},
            method_used="manual_workflow"
        )
    
    def _extract_post_id_from_response(self, response: Dict) -> Optional[str]:
        """Extract post ID from LinkedIn API response"""
        if not response:
            return None
        
        # Try different possible locations for post ID
        post_id_fields = ['id', 'activityId', 'shareId', 'updateKey']
        
        for field in post_id_fields:
            if field in response:
                return str(response[field])
        
        # Try nested fields
        if 'updateInfo' in response and 'updateKey' in response['updateInfo']:
            return response['updateInfo']['updateKey']
        
        return None
    
    def _build_post_url(self, post_id: str) -> str:
        """Build LinkedIn post URL from post ID"""
        if not post_id:
            return None
        
        # LinkedIn post URL format
        return f"https://www.linkedin.com/feed/update/{post_id}/"
    
    def _format_for_manual_posting(self, post: LinkedInPost) -> str:
        """Format post content for manual posting"""
        content = post.content_with_hashtags
        
        # Add formatting instructions
        formatted = f"""
=== LINKEDIN POST - READY TO COPY ===

{content}

=== POSTING INSTRUCTIONS ===
1. Copy the content above
2. Go to LinkedIn.com
3. Click "Start a post"
4. Paste the content
5. Add any media if needed
6. Click "Post"

=== POST METADATA ===
- Visibility: {post.visibility}
- Character count: {len(content)}
- Hashtag count: {len(post.hashtags)}
- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return formatted
    
    def get_posting_stats(self) -> Dict[str, Any]:
        """Get current posting statistics"""
        return {
            'posts_today': self.posts_today,
            'daily_limit': self.daily_limit,
            'posts_remaining': max(0, self.daily_limit - self.posts_today),
            'last_post_time': self.last_post_time.isoformat() if self.last_post_time else None,
            'can_post_now': self.can_post_now()[0],
            'authenticated': self._authenticated
        }
    
    def reset_daily_stats(self):
        """Reset daily posting statistics"""
        self.posts_today = 0
        self.last_post_time = None


class LinkedInScheduler:
    """Handles scheduled posting to LinkedIn"""
    
    def __init__(self):
        self.publisher = LinkedInPublisher()
    
    async def process_scheduled_posts(self) -> List[Dict[str, Any]]:
        """
        Process all posts scheduled for now
        
        Returns:
            List of processing results
        """
        results = []
        
        # Get posts that should be published now
        posts_to_publish = db.get_posts_to_publish()
        
        for post in posts_to_publish:
            try:
                # Extract hashtags from content or database
                hashtags = self._extract_hashtags(post)
                
                # Publish the post
                result = await self.publisher.publish_post(
                    post_content=post.content,
                    hashtags=hashtags
                )
                
                if result.success:
                    # Update post as published
                    db.mark_post_published(
                        post_id=post.id,
                        linkedin_post_id=result.post_id,
                        linkedin_post_url=result.post_url
                    )
                    
                    results.append({
                        'post_id': post.id,
                        'status': 'published',
                        'linkedin_post_id': result.post_id,
                        'message': 'Successfully published'
                    })
                else:
                    # Mark as failed
                    db.update_post(
                        post_id=post.id,
                        status='failed',
                        notes=f"Publishing failed: {result.error_message}"
                    )
                    
                    results.append({
                        'post_id': post.id,
                        'status': 'failed',
                        'error': result.error_message
                    })
                
            except Exception as e:
                # Handle unexpected errors
                db.update_post(
                    post_id=post.id,
                    status='failed',
                    notes=f"Unexpected error: {str(e)}"
                )
                
                results.append({
                    'post_id': post.id,
                    'status': 'error',
                    'error': str(e)
                })
        
        return results
    
    def _extract_hashtags(self, post: Post) -> List[str]:
        """Extract hashtags from post"""
        hashtags = []
        
        # From database field
        if post.hashtags:
            hashtags.extend(post.hashtags)
        
        # From content
        import re
        content_hashtags = re.findall(r'#\w+', post.content)
        hashtags.extend(content_hashtags)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_hashtags = []
        for tag in hashtags:
            if tag not in seen:
                seen.add(tag)
                unique_hashtags.append(tag)
        
        return unique_hashtags


# Convenience functions
async def publish_post_to_linkedin(
    content: str,
    hashtags: List[str] = None,
    **kwargs
) -> PublishResult:
    """
    Quick function to publish a post to LinkedIn
    
    Args:
        content: Post content
        hashtags: List of hashtags
        **kwargs: Additional arguments
        
    Returns:
        PublishResult
    """
    publisher = LinkedInPublisher()
    return await publisher.publish_post(
        post_content=content,
        hashtags=hashtags,
        **kwargs
    )


def get_manual_posting_format(content: str, hashtags: List[str] = None) -> str:
    """
    Get manually formatted content for copy-paste posting
    
    Args:
        content: Post content
        hashtags: List of hashtags
        
    Returns:
        Formatted content ready for manual posting
    """
    post = LinkedInPost(content=content, hashtags=hashtags or [])
    publisher = LinkedInPublisher()
    return publisher._format_for_manual_posting(post)


def check_linkedin_connection() -> Dict[str, Any]:
    """
    Check LinkedIn connection status
    
    Returns:
        Connection status and details
    """
    publisher = LinkedInPublisher()
    
    status = {
        'has_credentials': bool(publisher.email and publisher.password),
        'authenticated': False,
        'error': None
    }
    
    if status['has_credentials']:
        try:
            status['authenticated'] = publisher.authenticate()
            if not status['authenticated']:
                status['error'] = "Authentication failed - check credentials"
        except Exception as e:
            status['error'] = str(e)
    else:
        status['error'] = "No LinkedIn credentials configured"
    
    return status
