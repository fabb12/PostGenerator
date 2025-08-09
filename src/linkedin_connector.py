# src/linkedin_connector.py
"""
LinkedIn Connector Module
Handles publishing posts to LinkedIn using the unofficial linkedin-api.
This file is a replacement for the blocked linkedin_client.py.
"""

import json
import traceback
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# Importazione robusta
try:
    from linkedin_api import Linkedin
    LINKEDIN_API_AVAILABLE = True
except ImportError:
    Linkedin = None
    LINKEDIN_API_AVAILABLE = False

# Local imports
from src.database import db
from src.encryption import decrypt_password


# --- DATA STRUCTURES ---
@dataclass
class PublishResult:
    """Result of a LinkedIn post publishing attempt."""
    success: bool
    post_id: Optional[str] = None
    post_url: Optional[str] = None
    error_message: Optional[str] = None
    method_used: Optional[str] = "unofficial_api"


# --- MAIN PUBLISHER CLASS ---
class LinkedInPublisher:
    """Main class for publishing to LinkedIn."""

    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self._linkedin_client = None
        self._authenticated = False
        self._auth_attempted = False

    def authenticate(self) -> bool:
        """Authenticates with LinkedIn using provided credentials."""
        if self._authenticated: return True
        if self._auth_attempted: return False
        self._auth_attempted = True

        if not LINKEDIN_API_AVAILABLE:
            self._authenticated = False
            return False
        if not self.email or not self.password:
            self._authenticated = False
            return False

        try:
            print(f"Authenticating with LinkedIn as {self.email}...")
            self._linkedin_client = Linkedin(username=self.email, password=self.password, debug=False)
            # A successful authentication should return profile data
            if self._linkedin_client.get_profile():
                self._authenticated = True
                print(f"✅ LinkedIn Authentication Successful for {self.email}.")
                print("\n--- DEBUG: AVAILABLE METHODS ON LINKEDIN CLIENT ---")
                print(dir(self._linkedin_client))
                print("---------------------------------------------------\n")
                return True
            else:
                # This case might happen if credentials are wrong but no exception is thrown
                raise Exception("Authentication succeeded but no profile data was returned.")
        except Exception as e:
            print(f"❌ LinkedIn Authentication Failed for {self.email}: {e}")
            self._authenticated = False
            return False

    def is_authenticated(self) -> bool:
        return self._authenticated

    async def publish_post(self, post_content: str, link_to_share: Optional[str] = None,
                           visibility: str = "PUBLIC") -> PublishResult:
        """Publishes a post to LinkedIn."""
        if not self.is_authenticated():
            if not self.authenticate():
                return PublishResult(success=False, error_message="Authentication failed.")

        if link_to_share:
            return await self._publish_link_share(post_content, link_to_share, visibility)
        return await self._publish_text_post(post_content, visibility)

    async def _publish_text_post(self, content: str, visibility: str) -> PublishResult:
        """
        Publishes a text-only post, dynamically finding the correct method.
        """
        try:
            # List of potential method names for a text post. 'create_ugc_post' is a common standard.
            text_post_method_names = ['create_ugc_post', 'submit_share', 'create_share', 'create_post']
            method_to_use = None
            found_method_name = ""

            # Find the first available method on the client object
            for method_name in text_post_method_names:
                if hasattr(self._linkedin_client, method_name):
                    method_to_use = getattr(self._linkedin_client, method_name)
                    found_method_name = method_name
                    print(f"DEBUG: Found available text posting method: '{found_method_name}'")
                    break

            if not method_to_use:
                error_msg = f"No valid method for text posting found. Your 'linkedin-api' version may be incompatible. Tried: {text_post_method_names}"
                return PublishResult(success=False, error_message=error_msg)

            # Try calling the method with different parameter names for the content
            response = None
            try:
                # First, try with the 'text' parameter, as it's a common choice for text-only posts
                response = method_to_use(text=content, visibility=visibility.upper())
            except TypeError:
                # If 'text' is not the right parameter name, it will likely raise a TypeError.
                # In that case, we try with 'commentary', which is used for link shares.
                print(f"DEBUG: Calling '{found_method_name}' with 'text' failed. Trying 'commentary'.")
                response = method_to_use(commentary=content, visibility=visibility.upper())

            return self._validate_and_build_result(response, found_method_name)

        except Exception as e:
            traceback.print_exc()
            return PublishResult(success=False, error_message=f"API error (text post, method '{found_method_name}'): {e}")

    async def _publish_link_share(self, commentary: str, link: str, visibility: str) -> PublishResult:
        """
        Publishes a post that shares a link, dynamically finding the correct method.
        """
        try:
            # Expanded list of potential method names to improve compatibility
            link_share_method_names = ['create_share', 'post_article', 'share_article', 'submit']
            method_to_use = None
            found_method_name = ""

            for method_name in link_share_method_names:
                if hasattr(self._linkedin_client, method_name):
                    method_to_use = getattr(self._linkedin_client, method_name)
                    found_method_name = method_name
                    print(f"DEBUG: Found available link sharing method: '{found_method_name}'")
                    break

            if not method_to_use:
                error_msg = f"No valid method for link sharing found. Your 'linkedin-api' version may be incompatible. Tried: {link_share_method_names}"
                return PublishResult(success=False, error_message=error_msg)

            response = method_to_use(
                commentary=commentary,
                link=link,
                visibility=visibility.upper()
            )
            return self._validate_and_build_result(response, found_method_name)

        except Exception as e:
            traceback.print_exc()
            return PublishResult(success=False, error_message=f"API error (link share): {e}")

    def _validate_and_build_result(self, response: Dict, method: str) -> PublishResult:
        """Validates the API response and builds a PublishResult object."""
        print(f"\n--- DEBUG: LinkedIn API Response (from {method}) ---")
        print(json.dumps(response, indent=2))
        print("---------------------------------------------------\n")

        if response and isinstance(response, dict) and ('activity' in response or 'id' in response):
            post_urn = response.get('activity') or response.get('id')
            if post_urn and 'urn:li:' in post_urn:
                post_url = f"https://www.linkedin.com/feed/update/{post_urn}/"
                return PublishResult(success=True, post_id=post_urn, post_url=post_url, method_used=method)

        error_msg = f"Publish failed. Invalid API response: {response}"
        return PublishResult(success=False, error_message=error_msg, method_used=method)


# --- SCHEDULER CLASS ---
class LinkedInScheduler:
    """Handles scheduled posting to LinkedIn."""

    def __init__(self):
        self.publisher = None
        self._setup_publisher()

    def _setup_publisher(self):
        """Initializes the publisher with the active account's credentials."""
        active_account = db.get_active_linkedin_account()
        if active_account:
            try:
                password = decrypt_password(active_account.encrypted_password)
                self.publisher = LinkedInPublisher(email=active_account.email, password=password)
            except Exception as e:
                print(f"Scheduler: Failed to decrypt password for {active_account.email}. Error: {e}")
                self.publisher = None
        else:
            print("Scheduler: No active LinkedIn account found.")
            self.publisher = None

    async def process_scheduled_posts(self) -> List[Dict[str, Any]]:
        results = []
        posts_to_publish = db.get_posts_to_publish()

        if not posts_to_publish:
            return results

        # Ensure publisher is set up and authenticated
        if not self.publisher:
            print("Scheduler: Cannot process queue, publisher not initialized.")
            self._setup_publisher()
            if not self.publisher:
                print("Scheduler: Failed to initialize publisher on second attempt.")
                return results

        if not self.publisher.authenticate():
            print("Scheduler: Cannot process queue, LinkedIn authentication failed.")
            return results

        for post in posts_to_publish:
            try:
                link_to_share = None
                if post.sources and isinstance(post.sources, list) and len(post.sources) > 0:
                    first_source = post.sources[0]
                    if isinstance(first_source, dict) and first_source.get('type') == 'url':
                        link_to_share = first_source.get('content')
                    elif isinstance(first_source, str) and first_source.startswith('http'):
                        link_to_share = first_source

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
