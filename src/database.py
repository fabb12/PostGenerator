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


# --- MODEL DEFINITIONS ---

class Post(Base):
    """Post model for storing LinkedIn posts"""
    __tablename__ = 'posts'
    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    status = Column(String(50), default='draft')
    post_type = Column(String(50))
    tone = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    scheduled_for = Column(DateTime, nullable=True)
    published_at = Column(DateTime, nullable=True)
    model_used = Column(String(100))
    generation_temperature = Column(Float)
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    sources = Column(JSON)
    sources_summary = Column(Text)
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    engagement_rate = Column(Float, default=0.0)
    linkedin_post_id = Column(String(200), nullable=True)
    linkedin_post_url = Column(String(500), nullable=True)
    hashtags = Column(JSON)
    has_media = Column(Boolean, default=False)
    media_urls = Column(JSON)
    notes = Column(Text, nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id, 'content': self.content, 'status': self.status,
            'post_type': self.post_type, 'tone': self.tone,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'scheduled_for': self.scheduled_for.isoformat() if self.scheduled_for else None,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'model_used': self.model_used, 'sources': self.sources,
            'analytics': {'views': self.views, 'likes': self.likes, 'comments': self.comments, 'shares': self.shares, 'engagement_rate': self.engagement_rate},
            'linkedin_post_url': self.linkedin_post_url, 'hashtags': self.hashtags, 'notes': self.notes
        }

class ContentSource(Base):
    """Store extracted content sources for reuse"""
    __tablename__ = 'content_sources'
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_type = Column(String(50))
    source_url = Column(String(500))
    title = Column(String(500))
    content = Column(Text)
    summary = Column(Text)
    keywords = Column(JSON)
    extracted_at = Column(DateTime, default=datetime.utcnow)
    extra_data = Column(JSON)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id, 'source_type': self.source_type, 'source_url': self.source_url,
            'title': self.title, 'content': self.content[:500] + '...' if self.content else None,
            'summary': self.summary, 'keywords': self.keywords,
            'extracted_at': self.extracted_at.isoformat() if self.extracted_at else None
        }

class ScheduledPost(Base):
    """Track scheduled posts"""
    __tablename__ = 'scheduled_posts'
    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, nullable=False)
    scheduled_time = Column(DateTime, nullable=False)
    status = Column(String(50), default='pending')
    created_at = Column(DateTime, default=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id, 'post_id': self.post_id, 'scheduled_time': self.scheduled_time.isoformat(),
            'status': self.status, 'created_at': self.created_at.isoformat() if self.created_at else None,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'error_message': self.error_message, 'retry_count': self.retry_count
        }

class AutomationSource(Base):
    """Store sources for automated post generation"""
    __tablename__ = 'automation_sources'
    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(500), unique=True, nullable=False)
    source_type = Column(String(50), default='URL')
    is_active = Column(Boolean, default=True)
    last_checked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id, 'url': self.url, 'source_type': self.source_type,
            'is_active': self.is_active, 'last_checked_at': self.last_checked_at.isoformat() if self.last_checked_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None, 'notes': self.notes
        }

# --- DATABASE HANDLER CLASS ---

class Database:
    """Main database handler class - FIXED for DetachedInstanceError"""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or config.DATABASE_URL
        logger.info(f"Initializing database: {self.database_url}")
        if 'sqlite' in self.database_url:
            db_path = self.database_url.replace('sqlite:///', '')
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(
            self.database_url,
            connect_args={'check_same_thread': False} if 'sqlite' in self.database_url else {},
            echo=False
        )
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        logger.info("Database initialized successfully")

    @contextmanager
    def get_session(self) -> Session:
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
        if isinstance(obj, Post):
            _ = obj.id; _ = obj.content; _ = obj.status; _ = obj.post_type; _ = obj.tone; _ = obj.created_at; _ = obj.updated_at; _ = obj.scheduled_for; _ = obj.published_at; _ = obj.model_used; _ = obj.generation_temperature; _ = obj.prompt_tokens; _ = obj.completion_tokens; _ = obj.sources; _ = obj.sources_summary; _ = obj.views; _ = obj.likes; _ = obj.comments; _ = obj.shares; _ = obj.engagement_rate; _ = obj.linkedin_post_id; _ = obj.linkedin_post_url; _ = obj.hashtags; _ = obj.has_media; _ = obj.media_urls; _ = obj.notes
        elif isinstance(obj, ContentSource):
            _ = obj.id; _ = obj.source_type; _ = obj.source_url; _ = obj.title; _ = obj.content; _ = obj.summary; _ = obj.keywords; _ = obj.extracted_at; _ = obj.extra_data
        elif isinstance(obj, ScheduledPost):
            _ = obj.id; _ = obj.post_id; _ = obj.scheduled_time; _ = obj.status; _ = obj.created_at; _ = obj.published_at; _ = obj.error_message; _ = obj.retry_count
        elif isinstance(obj, AutomationSource): # Aggiunto il blocco mancante
            _ = obj.id; _ = obj.url; _ = obj.source_type; _ = obj.is_active; _ = obj.last_checked_at; _ = obj.created_at; _ = obj.notes

    # === Post Operations ===
    def create_post(self, content: str, **kwargs) -> int:
        try:
            with self.get_session() as session:
                post = Post(content=content, **kwargs)
                session.add(post)
                session.commit()
                session.refresh(post)
                post_id = int(post.id)
                logger.info(f"Created post with ID: {post_id}")
                return post_id
        except Exception as e:
            logger.error(f"Error creating post: {str(e)}")
            raise

    def get_post(self, post_id: int) -> Optional[Post]:
        try:
            with self.get_session() as session:
                post = session.query(Post).filter(Post.id == post_id).first()
                if post:
                    self._load_all_attributes(post)
                    session.expunge(post)
                return post
        except Exception as e:
            logger.error(f"Error getting post {post_id}: {str(e)}")
            return None

    def get_posts(self, status: Optional[str] = None, limit: int = 50, offset: int = 0, order_by: str = 'created_at_desc') -> List[Post]:
        try:
            with self.get_session() as session:
                query = session.query(Post)
                if status:
                    query = query.filter(Post.status == status)

                if order_by == 'created_at_desc':
                    query = query.order_by(Post.created_at.desc())
                elif order_by == 'created_at_asc':
                    query = query.order_by(Post.created_at.asc())
                elif order_by == 'scheduled_for_asc':
                    query = query.order_by(Post.scheduled_for.asc())
                elif order_by == 'engagement_desc':
                    query = query.order_by(Post.engagement_rate.desc())

                posts = query.limit(limit).offset(offset).all()
                for post in posts:
                    self._load_all_attributes(post)
                    session.expunge(post)
                return posts
        except Exception as e:
            logger.error(f"Error getting posts: {str(e)}")
            return []

    def update_post(self, post_id: int, **kwargs) -> Optional[Post]:
        try:
            with self.get_session() as session:
                post = session.query(Post).filter(Post.id == post_id).first()
                if post:
                    for key, value in kwargs.items():
                        if hasattr(post, key):
                            setattr(post, key, value)
                    post.updated_at = datetime.utcnow()
                    session.commit()
                    self._load_all_attributes(post)
                    session.expunge(post)
                return post
        except Exception as e:
            logger.error(f"Error updating post {post_id}: {str(e)}")
            return None

    def delete_post(self, post_id: int) -> bool:
        try:
            with self.get_session() as session:
                post = session.query(Post).filter(Post.id == post_id).first()
                if post:
                    session.delete(post)
                    return True
                return False
        except Exception as e:
            logger.error(f"Error deleting post {post_id}: {str(e)}")
            return False

    def schedule_post(self, post_id: int, scheduled_time: datetime) -> bool:
        try:
            with self.get_session() as session:
                post = session.query(Post).filter(Post.id == post_id).first()
                if post:
                    post.status = 'scheduled'
                    post.scheduled_for = scheduled_time
                    scheduled = ScheduledPost(post_id=post.id, scheduled_time=scheduled_time, status='pending')
                    session.add(scheduled)
                logger.info(f"Scheduled post {post_id} for {scheduled_time}")
                return True
        except Exception as e:
            logger.error(f"Error scheduling post {post_id}: {str(e)}")
            return False

    def mark_post_published(self, post_id: int, linkedin_post_id: str, linkedin_post_url: str) -> bool:
        try:
            with self.get_session() as session:
                post = session.query(Post).filter(Post.id == post_id).first()
                if post:
                    post.status = 'published'
                    post.published_at = datetime.utcnow()
                    post.linkedin_post_id = linkedin_post_id
                    post.linkedin_post_url = linkedin_post_url

                    scheduled = session.query(ScheduledPost).filter(ScheduledPost.post_id == post_id, ScheduledPost.status == 'pending').first()
                    if scheduled:
                        scheduled.status = 'published'
                        scheduled.published_at = datetime.utcnow()
                    logger.info(f"Marked post {post_id} as published.")
                    return True
                return False
        except Exception as e:
            logger.error(f"Error marking post {post_id} as published: {str(e)}")
            return False

    # === Content Source Operations ===
    def save_content_source(self, source_type: str, source_url: str, content: str, title: str = None, summary: str = None, keywords: List[str] = None, extra_data: Dict = None) -> int:
        with self.get_session() as session:
            existing = session.query(ContentSource).filter(ContentSource.source_type == source_type, ContentSource.source_url == source_url).first()
            if existing:
                existing.content = content
                existing.title = title
                existing.summary = summary
                existing.keywords = keywords or []
                existing.extra_data = extra_data or {}
                existing.extracted_at = datetime.utcnow()
                session.commit()
                return existing.id
            else:
                source = ContentSource(source_type=source_type, source_url=source_url, title=title, content=content, summary=summary, keywords=keywords or [], extra_data=extra_data or {})
                session.add(source)
                session.commit()
                session.refresh(source)
                return source.id

    def get_content_sources(self, source_type: Optional[str] = None, limit: int = 20) -> List[ContentSource]:
        try:
            with self.get_session() as session:
                query = session.query(ContentSource)
                if source_type:
                    query = query.filter(ContentSource.source_type == source_type)
                sources = query.order_by(ContentSource.extracted_at.desc()).limit(limit).all()
                for source in sources:
                    self._load_all_attributes(source)
                    session.expunge(source)
                return sources
        except Exception as e:
            logger.error(f"Error getting content sources: {str(e)}")
            return []

    # === Automation Source Operations ===
    def add_automation_source(self, url: str, source_type: str = 'URL') -> Optional[AutomationSource]:
        try:
            with self.get_session() as session:
                if session.query(AutomationSource).filter(AutomationSource.url == url).first():
                    logger.warning(f"Automation source {url} already exists.")
                    return None
                source = AutomationSource(url=url, source_type=source_type)
                session.add(source)
                session.commit()
                session.refresh(source)
                self._load_all_attributes(source)
                session.expunge(source)
                return source
        except Exception as e:
            logger.error(f"Error adding automation source {url}: {str(e)}")
            return None

    def get_active_automation_sources(self) -> List[AutomationSource]:
        try:
            with self.get_session() as session:
                sources = session.query(AutomationSource).filter(AutomationSource.is_active == True).order_by(AutomationSource.created_at.desc()).all()
                for source in sources:
                    self._load_all_attributes(source)
                    session.expunge(source)
                return sources
        except Exception as e:
            logger.error(f"Error getting active automation sources: {str(e)}")
            return []

    def update_automation_source(self, source_id: int, **kwargs) -> bool:
        try:
            with self.get_session() as session:
                source = session.query(AutomationSource).filter(AutomationSource.id == source_id).first()
                if not source: return False
                for key, value in kwargs.items():
                    setattr(source, key, value)
                return True
        except Exception as e:
            logger.error(f"Error updating automation source {source_id}: {str(e)}")
            return False

    def delete_automation_source(self, source_id: int) -> bool:
        try:
            with self.get_session() as session:
                source = session.query(AutomationSource).filter(AutomationSource.id == source_id).first()
                if source:
                    session.delete(source)
                    logger.info(f"Deleted automation source ID {source_id}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Error deleting automation source {source_id}: {str(e)}")
            return False

    # === Publishing Queue & Analytics Operations ===
    def get_posts_to_publish(self) -> List[Post]:
        try:
            with self.get_session() as session:
                posts = session.query(Post).filter(
                    Post.status == 'scheduled',
                    Post.scheduled_for <= datetime.utcnow()
                ).all()
                for post in posts:
                    self._load_all_attributes(post)
                    session.expunge(post)
                return posts
        except Exception as e:
            logger.error(f"Error getting posts to publish: {str(e)}")
            return []

    def get_scheduled_posts(self) -> List[Dict[str, Any]]:
        try:
            with self.get_session() as session:
                scheduled_items = session.query(ScheduledPost).order_by(ScheduledPost.scheduled_time.desc()).all()
                results = []
                for item in scheduled_items:
                    post = self.get_post(item.post_id)
                    if post:
                        results.append({
                            'scheduled': item.to_dict(),
                            'post': post.to_dict()
                        })
                return results
        except Exception as e:
            logger.error(f"Error getting scheduled posts: {str(e)}")
            return []

    def get_analytics_summary(self) -> Dict[str, Any]:
        try:
            with self.get_session() as session:
                total_posts = session.query(Post).count()
                published_posts = session.query(Post).filter(Post.status == 'published').count()
                avg_engagement = session.query(func.avg(Post.engagement_rate)).filter(Post.status == 'published', Post.engagement_rate > 0).scalar() or 0
                total_views = session.query(func.sum(Post.views)).filter(Post.status == 'published').scalar() or 0
                return {
                    'total_posts': total_posts,
                    'published_posts': published_posts,
                    'average_engagement_rate': round(float(avg_engagement), 2),
                    'total_views': total_views,
                }
        except Exception as e:
            logger.error(f"Error getting analytics summary: {str(e)}")
            return {}

# --- SINGLETON INSTANCE ---
db = Database()

# --- CONVENIENCE FUNCTIONS ---
def get_recent_posts(limit: int = 10) -> List[Post]:
    return db.get_posts(limit=limit)