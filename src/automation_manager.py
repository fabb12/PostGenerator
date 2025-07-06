# src/automation_manager.py

"""
Automation Manager
Handles the automated process of fetching content, generating, and scheduling posts.
"""

from datetime import datetime, timedelta, time
import logging
from typing import Dict, Any

from config import config
from src.database import db, Post
from src.content_extractor import ContentExtractor
from src.post_generator import PostGenerator, PostTone, PostType

logger = logging.getLogger(__name__)


class AutomationManager:
    """Manages the automated post generation and scheduling workflow."""

    def __init__(self):
        self.db = db
        self.extractor = ContentExtractor()
        self.generator = PostGenerator()

    def _find_next_available_slot(self) -> datetime:
        """Finds the next optimal time to schedule a post."""
        latest_scheduled_posts = self.db.get_posts(status='scheduled', order_by='scheduled_for_desc', limit=1)

        start_date = datetime.utcnow().date()
        if latest_scheduled_posts and latest_scheduled_posts[0].scheduled_for:
            latest_date = latest_scheduled_posts[0].scheduled_for.date()
            start_date = max(start_date, latest_date)

        next_date = start_date + timedelta(days=config.AUTOMATION_MIN_DAYS_BETWEEN_POSTS)

        # Find an available time slot on that day
        # For simplicity, we use the first hour defined in config.
        # A more complex logic could cycle through hours.
        schedule_hour = config.AUTOMATION_SCHEDULING_HOURS[0]
        next_slot = datetime.combine(next_date, time(hour=schedule_hour, minute=0))

        logger.info(f"Next available auto-schedule slot found: {next_slot}")
        return next_slot

    def run(self, force_run: bool = False) -> Dict[str, Any]:
        """
        Executes one cycle of the automation process.
        It generates posts from sources and schedules them automatically.
        """
        logger.info("Starting automation run...")
        sources_to_process = self.db.get_active_automation_sources()

        created_count = 0
        skipped_count = 0
        failed_count = 0
        results = []

        for source in sources_to_process:
            if not force_run and source.last_checked_at and (datetime.utcnow() - source.last_checked_at) < timedelta(
                    hours=24):
                skipped_count += 1
                continue

            try:
                logger.info(f"Processing source: {source.url}")
                extracted_content = self.extractor.extract_sync(source.url)
                if not extracted_content or not extracted_content.is_valid:
                    raise ValueError(f"Failed to extract content: {extracted_content.error}")

                posts = self.generator.generate_sync(
                    sources=[extracted_content],
                    tone=PostTone(config.AUTOMATION_DEFAULT_TONE),
                    post_type=PostType(config.AUTOMATION_DEFAULT_POST_TYPE),
                    num_variants=1
                )
                if not posts:
                    raise ValueError("Post generation returned no results.")

                generated_post = posts[0]

                # Create the post as a draft first
                post_id = self.db.create_post(
                    content=generated_post.content,
                    post_type=generated_post.post_type,
                    tone=generated_post.tone,
                    model_used=generated_post.model_used,
                    sources=[{'url': source.url, 'title': extracted_content.title}],
                    status='draft',
                    notes=f"Generated automatically from {source.url}"
                )

                # Now schedule it
                schedule_time = self._find_next_available_slot()
                self.db.schedule_post(post_id, schedule_time)

                self.db.update_automation_source(source.id, last_checked_at=datetime.utcnow())

                created_count += 1
                action_taken = f"✅ Scheduled post (ID: {post_id}) for {schedule_time.strftime('%Y-%m-%d %H:%M')} from {source.url}"
                results.append(action_taken)
                logger.info(action_taken)

            except Exception as e:
                failed_count += 1
                error_message = f"❌ Failed to process {source.url}: {str(e)}"
                results.append(error_message)
                logger.error(error_message)

        summary = {
            "total_sources": len(sources_to_process),
            "processed": created_count + failed_count,
            "scheduled": created_count,
            "skipped": skipped_count,
            "failed": failed_count,
            "results": results,
            "finished_at": datetime.now().isoformat()
        }

        logger.info(f"Automation run finished. Summary: {summary}")
        return summary