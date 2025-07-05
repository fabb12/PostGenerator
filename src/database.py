"""
Database Module - VERSIONE COMPLETA RISCRITTA
Handles all database operations for storing posts, drafts, and analytics
Uses SQLAlchemy with SQLite - FIXED DetachedInstanceError
"""

from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer, Float, Boolean, JSON, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import contextmanager
import json
from pathlib import Path
import logging

from config import config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create base class for models
Base = declarative_base()


class Post(Base):
    """Post model for storing LinkedIn posts"""
    __tablename__ = 'posts'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Content
    content = Column(Text, nullable=False)

    # Metadata
    status = Column(String(50), default='draft')  # draft, scheduled, published, failed
    post_type = Column(String(50))  # informative, news_sharing, etc.
    tone = Column(String(50))  # professional, friendly, etc.

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    scheduled_for = Column(DateTime, nullable=True)
    published_at = Column(DateTime, nullable=True)

    # Generation details
    model_used = Column(String(100))  # claude-3-opus, gpt-4, etc.
    generation_temperature = Column(Float)
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)

    # Source information
    sources = Column(JSON)  # List of source URLs/files
    sources_summary = Column(Text)  # Extracted content summary

    # Analytics (updated after publishing)
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    engagement_rate = Column(Float, default=0.0)

    # LinkedIn specific
    linkedin_post_id = Column(String(200), nullable=True)
    linkedin_post_url = Column(String(500), nullable=True)

    # Additional metadata
    hashtags = Column(JSON)  # List of hashtags used
    has_media = Column(Boolean, default=False)
    media_urls = Column(JSON)  # List of media URLs if any

    # User notes
    notes = Column(Text, nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert post to dictionary"""
        return {
            'id': self.id,
            'content': self.content,
            'status': self.status,
            'post_type': self.post_type,
            'tone': self.tone,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'scheduled_for': self.scheduled_for.isoformat() if self.scheduled_for else None,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'model_used': self.model_used,
            'sources': self.sources,
            'analytics': {
                'views': self.views,
                'likes': self.likes,
                'comments': self.comments,
                'shares': self.shares,
                'engagement_rate': self.engagement_rate
            },
            'linkedin_post_url': self.linkedin_post_url,
            'hashtags': self.hashtags,
            'notes': self.notes
        }


class ContentSource(Base):
    """Store extracted content sources for reuse"""
    __tablename__ = 'content_sources'

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_type = Column(String(50))  # web, pdf, linkedin, text
    source_url = Column(String(500))
    title = Column(String(500))
    content = Column(Text)
    summary = Column(Text)
    keywords = Column(JSON)
    extracted_at = Column(DateTime, default=datetime.utcnow)
    extra_data = Column(JSON)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'source_type': self.source_type,
            'source_url': self.source_url,
            'title': self.title,
            'content': self.content[:500] + '...' if self.content else None,
            'summary': self.summary,
            'keywords': self.keywords,
            'extracted_at': self.extracted_at.isoformat() if self.extracted_at else None
        }


class ScheduledPost(Base):
    """Track scheduled posts"""
    __tablename__ = 'scheduled_posts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, nullable=False)
    scheduled_time = Column(DateTime, nullable=False)
    status = Column(String(50), default='pending')  # pending, published, failed, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'post_id': self.post_id,
            'scheduled_time': self.scheduled_time.isoformat(),
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'error_message': self.error_message,
            'retry_count': self.retry_count
        }


class Database:
    """Main database handler class - FIXED for DetachedInstanceError"""

    def __init__(self, database_url: Optional[str] = None):
        """Initialize database connection"""
        self.database_url = database_url or config.DATABASE_URL
        logger.info(f"Initializing database: {self.database_url}")

        # Ensure database directory exists
        if 'sqlite' in self.database_url:
            db_path = self.database_url.replace('sqlite:///', '')
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Create engine and session
        self.engine = create_engine(
            self.database_url,
            connect_args={'check_same_thread': False} if 'sqlite' in self.database_url else {},
            echo=False  # Set to True for SQL debugging
        )

        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)

        # Create session factory
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        logger.info("Database initialized successfully")

    @contextmanager
    def get_session(self) -> Session:
        """Get database session with automatic cleanup"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {str(e)}")
            raise
        finally:
            session.close()

    def _load_all_attributes(self, obj: Any) -> None:
        """Force load all attributes to prevent DetachedInstanceError"""
        if isinstance(obj, Post):
            # Force load all Post attributes
            _ = obj.id
            _ = obj.content
            _ = obj.status
            _ = obj.post_type
            _ = obj.tone
            _ = obj.created_at
            _ = obj.updated_at
            _ = obj.scheduled_for
            _ = obj.published_at
            _ = obj.model_used
            _ = obj.generation_temperature
            _ = obj.prompt_tokens
            _ = obj.completion_tokens
            _ = obj.sources
            _ = obj.sources_summary
            _ = obj.views
            _ = obj.likes
            _ = obj.comments
            _ = obj.shares
            _ = obj.engagement_rate
            _ = obj.linkedin_post_id
            _ = obj.linkedin_post_url
            _ = obj.hashtags
            _ = obj.has_media
            _ = obj.media_urls
            _ = obj.notes
        elif isinstance(obj, ContentSource):
            # Force load all ContentSource attributes
            _ = obj.id
            _ = obj.source_type
            _ = obj.source_url
            _ = obj.title
            _ = obj.content
            _ = obj.summary
            _ = obj.keywords
            _ = obj.extracted_at
            _ = obj.extra_data
        elif isinstance(obj, ScheduledPost):
            # Force load all ScheduledPost attributes
            _ = obj.id
            _ = obj.post_id
            _ = obj.scheduled_time
            _ = obj.status
            _ = obj.created_at
            _ = obj.published_at
            _ = obj.error_message
            _ = obj.retry_count

    # === Post Operations ===

    def create_post(
            self,
            content: str,
            post_type: str = 'informative',
            tone: str = 'professional',
            sources: List[Dict] = None,
            model_used: str = None,
            generation_temperature: float = None,
            prompt_tokens: int = None,
            completion_tokens: int = None,
            hashtags: List[str] = None,
            status: str = 'draft',
            **kwargs
    ) -> int:
        """Create a new post - RETURNS INTEGER ID ONLY"""
        try:
            with self.get_session() as session:
                post = Post(
                    content=content,
                    post_type=post_type,
                    tone=tone,
                    sources=sources or [],
                    model_used=model_used,
                    generation_temperature=generation_temperature,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    hashtags=hashtags or [],
                    status=status
                )
                session.add(post)
                session.commit()
                session.refresh(post)

                # Get the ID before closing session
                post_id = int(post.id)
                logger.info(f"Created post with ID: {post_id}")
                return post_id
        except Exception as e:
            logger.error(f"Error creating post: {str(e)}")
            raise

    def get_post(self, post_id: int) -> Optional[Post]:
        """Get a single post by ID - FIXED for DetachedInstanceError"""
        try:
            with self.get_session() as session:
                post = session.query(Post).filter(Post.id == post_id).first()
                if post:
                    # Force load all attributes while session is active
                    self._load_all_attributes(post)
                    session.refresh(post)
                    # Make the instance independent from the session
                    session.expunge(post)
                    logger.debug(f"Retrieved post {post_id}")
                return post
        except Exception as e:
            logger.error(f"Error getting post {post_id}: {str(e)}")
            return None

    def get_post_safe(self, post_id: int) -> Optional[Post]:
        """Get a single post by ID with safe error handling"""
        try:
            return self.get_post(post_id)
        except Exception as e:
            logger.error(f"Safe get post {post_id} failed: {str(e)}")
            return None

    def get_posts(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        order_by: str = 'created_at_desc'
    ) -> List[Post]:
        """Get posts with optional filtering - FIXED for DetachedInstanceError"""
        try:
            with self.get_session() as session:
                query = session.query(Post)

                if status:
                    query = query.filter(Post.status == status)

                # Apply ordering
                if order_by == 'created_at_desc':
                    query = query.order_by(Post.created_at.desc())
                elif order_by == 'created_at_asc':
                    query = query.order_by(Post.created_at.asc())
                elif order_by == 'scheduled_for_asc':
                    query = query.order_by(Post.scheduled_for.asc())
                elif order_by == 'engagement_desc':
                    query = query.order_by(Post.engagement_rate.desc())

                posts = query.limit(limit).offset(offset).all()

                # Force load all attributes for each post
                for post in posts:
                    self._load_all_attributes(post)
                    session.refresh(post)

                # Make all instances independent from the session
                for post in posts:
                    session.expunge(post)

                logger.debug(f"Retrieved {len(posts)} posts")
                return posts
        except Exception as e:
            logger.error(f"Error getting posts: {str(e)}")
            return []

    def update_post(self, post_id: int, **kwargs) -> Optional[Post]:
        """Update a post"""
        try:
            with self.get_session() as session:
                post = session.query(Post).filter(Post.id == post_id).first()
                if post:
                    for key, value in kwargs.items():
                        if hasattr(post, key):
                            setattr(post, key, value)
                    post.updated_at = datetime.utcnow()
                    session.commit()

                    # Force load all attributes and detach
                    self._load_all_attributes(post)
                    session.refresh(post)
                    session.expunge(post)

                    logger.info(f"Updated post {post_id}")
                return post
        except Exception as e:
            logger.error(f"Error updating post {post_id}: {str(e)}")
            return None

    def delete_post(self, post_id: int) -> bool:
        """Delete a post"""
        try:
            with self.get_session() as session:
                post = session.query(Post).filter(Post.id == post_id).first()
                if post:
                    session.delete(post)
                    session.commit()
                    logger.info(f"Deleted post {post_id}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Error deleting post {post_id}: {str(e)}")
            return False

    def schedule_post(self, post_id: int, scheduled_time: datetime) -> bool:
        """Schedule a post for future publishing"""
        try:
            with self.get_session() as session:
                post = session.query(Post).filter(Post.id == post_id).first()
                if post:
                    post.scheduled_for = scheduled_time
                    post.status = 'scheduled'

                    # Create scheduled post entry
                    scheduled = ScheduledPost(
                        post_id=post_id,
                        scheduled_time=scheduled_time,
                        status='pending'
                    )
                    session.add(scheduled)
                    session.commit()

                    logger.info(f"Scheduled post {post_id} for {scheduled_time}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Error scheduling post {post_id}: {str(e)}")
            return False

    def mark_post_published(
        self,
        post_id: int,
        linkedin_post_id: str = None,
        linkedin_post_url: str = None
    ) -> Optional[Post]:
        """Mark a post as published"""
        try:
            with self.get_session() as session:
                post = session.query(Post).filter(Post.id == post_id).first()
                if post:
                    post.status = 'published'
                    post.published_at = datetime.utcnow()
                    post.linkedin_post_id = linkedin_post_id
                    post.linkedin_post_url = linkedin_post_url

                    # Update scheduled post if exists
                    scheduled = session.query(ScheduledPost).filter(
                        ScheduledPost.post_id == post_id,
                        ScheduledPost.status == 'pending'
                    ).first()

                    if scheduled:
                        scheduled.status = 'published'
                        scheduled.published_at = datetime.utcnow()

                    session.commit()

                    # Force load all attributes and detach
                    self._load_all_attributes(post)
                    session.refresh(post)
                    session.expunge(post)

                    logger.info(f"Marked post {post_id} as published")
                    return post
                return None
        except Exception as e:
            logger.error(f"Error marking post {post_id} as published: {str(e)}")
            return None

    def mark_post_published_manually(
        self,
        post_id: int,
        notes: str = "Published manually via copy-paste"
    ) -> bool:
        """Mark a post as published manually"""
        try:
            with self.get_session() as session:
                post = session.query(Post).filter(Post.id == post_id).first()
                if post:
                    post.status = 'published'
                    post.published_at = datetime.utcnow()
                    post.linkedin_post_url = "manual_publish"  # Special indicator
                    post.notes = notes
                    session.commit()
                    logger.info(f"Marked post {post_id} as manually published")
                    return True
                return False
        except Exception as e:
            logger.error(f"Error marking post {post_id} as manually published: {str(e)}")
            return False

    # === Content Source Operations ===

        # === Content Source Operations ===

        def save_content_source(
                self,
                source_type: str,
                source_url: str,
                content: str,
                title: str = None,
                summary: str = None,
                keywords: List[str] = None,
                extra_data: Dict = None
        ) -> int:
            """Save extracted content source for reuse - Returns ID"""
            with self.get_session() as session:
                # Check if source already exists
                existing = session.query(ContentSource).filter(
                    ContentSource.source_type == source_type,
                    ContentSource.source_url == source_url
                ).first()

                if existing:
                    # Update existing source
                    existing.content = content
                    existing.title = title
                    existing.summary = summary
                    existing.keywords = keywords or []
                    existing.extra_data = extra_data or {}
                    existing.extracted_at = datetime.utcnow()
                    session.commit()
                    return existing.id
                else:
                    # Create new source
                    source = ContentSource(
                        source_type=source_type,
                        source_url=source_url,
                        title=title,
                        content=content,
                        summary=summary,
                        keywords=keywords or [],
                        extra_data=extra_data or {}
                    )
                    session.add(source)
                    session.commit()
                    session.refresh(source)
                    return source.id
    def get_content_sources(
        self,
        source_type: Optional[str] = None,
        limit: int = 20
    ) -> List[ContentSource]:
        """Get saved content sources"""
        try:
            with self.get_session() as session:
                query = session.query(ContentSource)

                if source_type:
                    query = query.filter(ContentSource.source_type == source_type)

                sources = query.order_by(ContentSource.extracted_at.desc()).limit(limit).all()

                # Force load attributes for each source
                for source in sources:
                    self._load_all_attributes(source)
                    session.refresh(source)

                # Make all instances independent from the session
                for source in sources:
                    session.expunge(source)

                logger.debug(f"Retrieved {len(sources)} content sources")
                return sources
        except Exception as e:
            logger.error(f"Error getting content sources: {str(e)}")
            return []

    # === Analytics Operations ===

    def update_post_analytics(
        self,
        post_id: int,
        views: int = None,
        likes: int = None,
        comments: int = None,
        shares: int = None
    ) -> Optional[Post]:
        """Update post analytics"""
        try:
            with self.get_session() as session:
                post = session.query(Post).filter(Post.id == post_id).first()
                if post:
                    if views is not None:
                        post.views = views
                    if likes is not None:
                        post.likes = likes
                    if comments is not None:
                        post.comments = comments
                    if shares is not None:
                        post.shares = shares

                    # Calculate engagement rate
                    total_interactions = (post.likes or 0) + (post.comments or 0) + (post.shares or 0)
                    if post.views and post.views > 0:
                        post.engagement_rate = (total_interactions / post.views) * 100

                    session.commit()

                    # Force load all attributes and detach
                    self._load_all_attributes(post)
                    session.refresh(post)
                    session.expunge(post)

                    logger.info(f"Updated analytics for post {post_id}")
                    return post
                return None
        except Exception as e:
            logger.error(f"Error updating analytics for post {post_id}: {str(e)}")
            return None

    def get_analytics_summary(self) -> Dict[str, Any]:
        """Get overall analytics summary"""
        try:
            with self.get_session() as session:
                total_posts = session.query(Post).count()
                published_posts = session.query(Post).filter(Post.status == 'published').count()

                # Calculate averages for published posts
                avg_engagement = session.query(func.avg(Post.engagement_rate)).filter(
                    Post.status == 'published',
                    Post.engagement_rate > 0
                ).scalar() or 0

                total_views = session.query(func.sum(Post.views)).scalar() or 0
                total_likes = session.query(func.sum(Post.likes)).scalar() or 0

                return {
                    'total_posts': total_posts,
                    'published_posts': published_posts,
                    'average_engagement_rate': round(float(avg_engagement), 2),
                    'total_views': total_views,
                    'total_likes': total_likes
                }
        except Exception as e:
            logger.error(f"Error getting analytics summary: {str(e)}")
            return {
                'total_posts': 0,
                'published_posts': 0,
                'average_engagement_rate': 0.0,
                'total_views': 0,
                'total_likes': 0
            }

    # === Scheduled Posts Operations ===

    def get_scheduled_posts(self) -> List[Dict[str, Any]]:
        """Get all scheduled posts with their post data"""
        try:
            with self.get_session() as session:
                scheduled = session.query(ScheduledPost).filter(
                    ScheduledPost.status.in_(['pending', 'published', 'failed'])
                ).order_by(ScheduledPost.scheduled_time.asc()).all()

                result = []
                for s in scheduled:
                    # Force load scheduled post attributes
                    self._load_all_attributes(s)
                    session.refresh(s)

                    post = session.query(Post).filter(Post.id == s.post_id).first()
                    if post:
                        # Force load post attributes
                        self._load_all_attributes(post)
                        session.refresh(post)

                        result.append({
                            'scheduled': s.to_dict(),
                            'post': post.to_dict()
                        })

                logger.debug(f"Retrieved {len(result)} scheduled posts")
                return result
        except Exception as e:
            logger.error(f"Error getting scheduled posts: {str(e)}")
            return []

    def get_posts_to_publish(self) -> List[Post]:
        """Get posts that should be published now"""
        try:
            with self.get_session() as session:
                current_time = datetime.utcnow()

                scheduled_ids = session.query(ScheduledPost.post_id).filter(
                    ScheduledPost.scheduled_time <= current_time,
                    ScheduledPost.status == 'pending'
                ).subquery()

                posts = session.query(Post).filter(
                    Post.id.in_(scheduled_ids),
                    Post.status == 'scheduled'
                ).all()

                # Force load attributes for each post
                for post in posts:
                    self._load_all_attributes(post)
                    session.refresh(post)

                # Make all instances independent from the session
                for post in posts:
                    session.expunge(post)

                logger.debug(f"Found {len(posts)} posts to publish")
                return posts
        except Exception as e:
            logger.error(f"Error getting posts to publish: {str(e)}")
            return []

    def get_manual_published_posts(self) -> List[Post]:
        """Get all manually published posts"""
        try:
            with self.get_session() as session:
                posts = session.query(Post).filter(
                    Post.status == 'published',
                    Post.linkedin_post_url == 'manual_publish'
                ).order_by(Post.published_at.desc()).all()

                # Force load attributes for each post
                for post in posts:
                    self._load_all_attributes(post)
                    session.refresh(post)

                # Make all instances independent from the session
                for post in posts:
                    session.expunge(post)

                logger.debug(f"Retrieved {len(posts)} manually published posts")
                return posts
        except Exception as e:
            logger.error(f"Error getting manually published posts: {str(e)}")
            return []

    # === Utility Methods ===

    def health_check(self) -> Dict[str, Any]:
        """Check database health"""
        try:
            with self.get_session() as session:
                # Test basic query
                count = session.query(Post).count()
                return {
                    'status': 'healthy',
                    'total_posts': count,
                    'database_url': self.database_url,
                    'timestamp': datetime.utcnow().isoformat()
                }
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }

    def reset_database(self) -> bool:
        """Reset database (delete all data) - USE WITH CAUTION"""
        try:
            Base.metadata.drop_all(self.engine)
            Base.metadata.create_all(self.engine)
            logger.warning("Database reset completed")
            return True
        except Exception as e:
            logger.error(f"Database reset failed: {str(e)}")
            return False


# Create singleton instance
db = Database()

# Convenience functions
def save_post(content: str, **kwargs) -> int:
    """Quick function to save a post"""
    return db.create_post(content, **kwargs)

def get_recent_posts(limit: int = 10) -> List[Post]:
    """Get recent posts"""
    return db.get_posts(limit=limit)

def get_scheduled_posts() -> List[Dict[str, Any]]:
    """Get scheduled posts"""
    return db.get_scheduled_posts()

def health_check() -> Dict[str, Any]:
    """Check database health"""
    return db.health_check()

# Initialize database on import
if __name__ == "__main__":
    # Test database functionality
    print("Testing database...")
    result = health_check()
    print(f"Database health: {result}")