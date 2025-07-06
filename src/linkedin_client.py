# src/linkedin_client.py
"""
LinkedIn Client Module
Handles publishing posts to LinkedIn using the unofficial linkedin-api.
Includes a smart "router" for text-only vs. link-sharing posts.
"""

import time
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import traceback

# LinkedIn API (unofficial) with graceful import
try:
    from linkedin_api import Linkedin
    from linkedin_api.utils import get_id_from_urn
    LINKEDIN_API_AVAILABLE = True
except ImportError:
    Linkedin, get_id_from_urn = None, None
    LINKEDIN_API_AVAILABLE = False

# Local imports
from config import config
from src.database import db

# --- DATA STRUCTURES ---
@dataclass
class PublishResult:
    """Result of a LinkedIn post publishing attempt."""
    success: bool
    post_id: Optional[str] = None
    post_url: Optional[str] = None
    error_message: Optional[str] = None
    method_used: Optional[str] = "unofficial_api"

@dataclass
class LinkedInPost:
    """Structure for LinkedIn post data."""
    content: str
    visibility: str = "PUBLIC"

# --- MAIN PUBLISHER CLASS ---
class LinkedInPublisher:
    """Main class for publishing to LinkedIn."""

    def __init__(self):
        self.email = config.LINKEDIN_EMAIL
        self.password = config.LINKEDIN_PASSWORD
        self._linkedin_client = None
        self._authenticated = False

    def authenticate(self) -> bool:
        """Authenticates with LinkedIn using stored credentials."""
        if not LINKEDIN_API_AVAILABLE:
            print("ERROR: linkedin-api library not installed.")
            return False
        if not self.email or not self.password:
            print("ERROR: LinkedIn credentials not configured.")
            return False
        if self._authenticated:
            return True

        try:
            print("Authenticating with LinkedIn...")
            self._linkedin_client = Linkedin(username=self.email, password=self.password, debug=False)
            if self._linkedin_client.get_profile():
                self._authenticated = True
                print("✅ LinkedIn Authentication Successful.")
                return True
            raise Exception("Profile data not returned.")
        except Exception as e:
            print(f"❌ LinkedIn Authentication Failed: {e}")
            self._authenticated = False
            return False

    def is_authenticated(self) -> bool:
        return self.is_authenticated()

    # --- PUBLISHING ROUTER (METODO PRINCIPALE) ---
    async def publish_post(self, post_content: str, link_to_share: Optional[str] = None, visibility: str = "PUBLIC") -> PublishResult:
        """
        Publishes a post to LinkedIn.
        If a 'link_to_share' is provided, it creates an article share.
        Otherwise, it creates a simple text post.
        """
        if not self.is_authenticated() and not self.authenticate():
            return PublishResult(success=False, error_message="Authentication failed.")

        if link_to_share:
            print(f"Attempting to publish as a link share: {link_to_share}")
            return await self._publish_link_share(post_content, link_to_share, visibility)

        print("Attempting to publish as a text-only post.")
        return await self._publish_text_post(post_content, visibility)

    # --- METODI HELPER PRIVATI PER CIASCUN TIPO DI POST ---
    async def _publish_text_post(self, content: str, visibility: str) -> PublishResult:
        """Publishes a text-only post."""
        try:
            response = self._linkedin_client.create_post(text=content, visibility=visibility.upper())
            return self._validate_and_build_result(response)
        except Exception as e:
            traceback.print_exc()
            return PublishResult(success=False, error_message=f"API error (text post): {e}")

    async def _publish_link_share(self, commentary: str, link: str, visibility: str) -> PublishResult:
        """Publishes a post that shares a link (article)."""
        try:
            # La libreria usa metodi diversi per testo e articoli
            response = self._linkedin_client.post_article(commentary=commentary, link=link, visibility=visibility.upper())
            return self._validate_and_build_result(response)
        except Exception as e:
            traceback.print_exc()
            return PublishResult(success=False, error_message=f"API error (link share): {e}")

    def _validate_and_build_result(self, response: Dict) -> PublishResult:
        """Validates the API response and builds a PublishResult object."""
        print("\n--- DEBUG: LinkedIn API Response ---")
        print(json.dumps(response, indent=2))
        print("------------------------------------\n")

        if response and isinstance(response, dict) and ('activity' in response or 'id' in response):
            post_urn = response.get('activity') or response.get('id')
            if post_urn and 'urn:li:' in post_urn:
                post_url = f"https://www.linkedin.com/feed/update/{post_urn}/"
                return PublishResult(success=True, post_id=post_urn, post_url=post_url)

        error_msg = f"Publish failed. Invalid API response: {response}"
        return PublishResult(success=False, error_message=error_msg)


# --- SCHEDULER CLASS ---
class LinkedInScheduler:
    """Handles scheduled posting to LinkedIn."""

    def __init__(self):
        self.publisher = LinkedInPublisher()

    async def process_scheduled_posts(self) -> List[Dict[str, Any]]:
        """Process all posts scheduled for now."""
        results = []
        posts_to_publish = db.get_posts_to_publish()

        for post in posts_to_publish:
            try:
                # Determina se c'è un link da condividere
                link_to_share = None
                if post.sources and isinstance(post.sources, list) and post.sources[0].get('url'):
                    link_to_share = post.sources[0]['url']

                result = await self.publisher.publish_post(
                    post_content=post.content,
                    link_to_share=link_to_share
                )

                if result.success:
                    db.mark_post_published(post.id, result.post_id, result.post_url)
                    results.append({'post_id': post.id, 'status': 'published'})
                else:
                    db.update_post(post.id, status='failed', notes=f"Publishing failed: {result.error_message}")
                    results.append({'post_id': post.id, 'status': 'failed', 'error': result.error_message})
            except Exception as e:
                db.update_post(post.id, status='failed', notes=f"Unexpected error: {e}")
                results.append({'post_id': post.id, 'status': 'error', 'error': str(e)})

        return results

# --- HELPER FUNCTION ---
def check_linkedin_connection() -> Dict[str, Any]:
    """Checks LinkedIn connection status."""
    if not LINKEDIN_API_AVAILABLE:
        return {'authenticated': False, 'error': "Libreria 'linkedin-api' non installata."}

    publisher = LinkedInPublisher()
    is_authed = publisher.authenticate()
    return {
        'authenticated': is_authed,
        'error': None if is_authed else "Autenticazione fallita. Controlla credenziali e 2FA."
    }