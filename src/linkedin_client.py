# src/linkedin_client.py test

"""
LinkedIn Client Module
Handles publishing posts to LinkedIn using the unofficial linkedin-api.
Includes a DEFINITIVE, dynamic method hunter to ensure compatibility
with multiple library versions.
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


# --- MAIN PUBLISHER CLASS ---
class LinkedInPublisher:
    """Main class for publishing to LinkedIn."""

    def __init__(self):
        self.email = config.LINKEDIN_EMAIL
        self.password = config.LINKEDIN_PASSWORD
        self._linkedin_client = None
        self._authenticated = False
        self._auth_attempted = False

    def authenticate(self) -> bool:
        """Authenticates with LinkedIn using stored credentials."""
        if self._authenticated: return True
        if self._auth_attempted: return False
        self._auth_attempted = True

        if not LINKEDIN_API_AVAILABLE:
            return False
        if not self.email or not self.password:
            return False

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
        return self._authenticated

    async def publish_post(self, post_content: str, link_to_share: Optional[str] = None,
                           visibility: str = "PUBLIC") -> PublishResult:
        """Publishes a post to LinkedIn."""
        if not self.is_authenticated() and not self.authenticate():
            return PublishResult(success=False, error_message="Authentication failed.")

        if link_to_share:
            return await self._publish_link_share(post_content, link_to_share, visibility)
        return await self._publish_text_post(post_content, visibility)

    async def _publish_text_post(self, content: str, visibility: str) -> PublishResult:
        """Publishes a text-only post."""
        try:
            response = self._linkedin_client.create_post(text=content, visibility=visibility.upper())
            return self._validate_and_build_result(response, "create_post")
        except Exception as e:
            traceback.print_exc()
            return PublishResult(success=False, error_message=f"API error (text post): {e}")

    async def _publish_link_share(self, commentary: str, link: str, visibility: str) -> PublishResult:
        """
        Publishes a post that shares a link, dynamically finding the correct method.
        """
        try:
            # ### <<< SOLUZIONE DEFINITIVA: IL CACCIATORE DI METODI >>> ###
            # Lista dei possibili nomi di metodi per condividere un link, in ordine di preferenza.
            link_share_method_names = ['create_share', 'post_article']

            method_to_use = None
            found_method_name = ""

            # Cerca il primo metodo disponibile nell'oggetto client
            for method_name in link_share_method_names:
                if hasattr(self._linkedin_client, method_name):
                    method_to_use = getattr(self._linkedin_client, method_name)
                    found_method_name = method_name
                    print(f"DEBUG: Found available link sharing method: '{found_method_name}'")
                    break

            # Se nessun metodo è stato trovato, la versione è troppo vecchia o non supportata.
            if not method_to_use:
                error_msg = f"Nessun metodo valido per la condivisione di link trovato. La tua versione di 'linkedin-api' potrebbe essere incompatibile. Metodi provati: {link_share_method_names}"
                return PublishResult(success=False, error_message=error_msg)

            # Esegui il metodo che abbiamo trovato
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
        self.publisher = LinkedInPublisher()

    async def process_scheduled_posts(self) -> List[Dict[str, Any]]:
        # ... (Questa classe non necessita di modifiche)
        results = []
        posts_to_publish = db.get_posts_to_publish()

        if not posts_to_publish: return results
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


# --- HELPER FUNCTION ---
def check_linkedin_connection() -> Dict[str, Any]:
    """Checks LinkedIn connection status."""
    try:
        from linkedin_api import Linkedin
        publisher = LinkedInPublisher()
        is_authed = publisher.authenticate()
        return {'authenticated': is_authed, 'error': None if is_authed else "Autenticazione fallita."}
    except ImportError:

        return {'authenticated': False, 'error': "Libreria 'linkedin-api' non installata."}
