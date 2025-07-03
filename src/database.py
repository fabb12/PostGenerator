"""
Database Module
Handles all database operations for storing posts, drafts, and analytics
Uses SQLAlchemy with SQLite for simplicity
"""

from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer, Float, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import contextmanager
import json
from pathlib import Path

from config import config

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
    metadata = Column(JSON)
    
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
    """Main database handler class"""
    
    def __init__(self, database_url: Optional[str] = None):
        """Initialize database connection"""
        self.database_url = database_url or config.DATABASE_URL
        
        # Ensure database directory exists
        if 'sqlite' in self.database_url:
            db_path = self.database_url.replace('sqlite:///', '')
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Create engine and session
        self.engine = create_engine(
            self.database_url,
            connect_args={'check_same_thread': False} if 'sqlite' in self.database_url else {}
        )
        
        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)
        
        # Create session factory
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    @contextmanager
    def get_session(self) -> Session:
        """Get database session with automatic cleanup"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    # === Post Operations ===
    
    def create_post(
        self,
        content: str,
        post_type: str = 'informative',
        tone: str = 'professional',
        sources: List[Dict] = None,
        model_used: str = None,
        **kwargs
    ) -> Post:
        """Create a new post"""
        with self.get_session() as session:
            post = Post(
                content=content,
                post_type=post_type,
                tone=tone,
                sources=sources or [],
                model_used=model_used,
                status='draft',
                **kwargs
            )
            session.add(post)
            session.commit()
            session.refresh(post)
            return post
    
    def get_post(self, post_id: int) -> Optional[Post]:
        """Get a single post by ID"""
        with self.get_session() as session:
            return session.query(Post).filter(Post.id == post_id).first()
    
    def get_posts(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        order_by: str = 'created_at_desc'
    ) -> List[Post]:
        """Get posts with optional filtering"""
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
            
            return query.limit(limit).offset(offset).all()
    
    def update_post(self, post_id: int, **kwargs) -> Optional[Post]:
        """Update a post"""
        with self.get_session() as session:
            post = session.query(Post).filter(Post.id == post_id).first()
            if post:
                for key, value in kwargs.items():
                    if hasattr(post, key):
                        setattr(post, key, value)
                post.updated_at = datetime.utcnow()
                session.commit()
                session.refresh(post)
            return post
    
    def delete_post(self, post_id: int) -> bool:
        """Delete a post"""
        with self.get_session() as session:
            post = session.query(Post).filter(Post.id == post_id).first()
            if post:
                session.delete(post)
                session.commit()
                return True
            return False
    
    def schedule_post(self, post_id: int, scheduled_time: datetime) -> Post:
        """Schedule a post for future publishing"""
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
                session.refresh(post)
                
            return post
    
    def mark_post_published(
        self,
        post_id: int,
        linkedin_post_id: str = None,
        linkedin_post_url: str = None
    ) -> Post:
        """Mark a post as published"""
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
                session.refresh(post)
                
            return post
    
    # === Content Source Operations ===
    
    def save_content_source(
        self,
        source_type: str,
        source_url: str,
        content: str,
        title: str = None,
        summary: str = None,
        keywords: List[str] = None,
        metadata: Dict = None
    ) -> ContentSource:
        """Save extracted content source for reuse"""
        with self.get_session() as session:
            source = ContentSource(
                source_type=source_type,
                source_url=source_url,
                title=title,
                content=content,
                summary=summary,
                keywords=keywords or [],
                metadata=metadata or {}
            )
            session.add(source)
            session.commit()
            session.refresh(source)
            return source
    
    def get_content_sources(
        self,
        source_type: Optional[str] = None,
        limit: int = 20
    ) -> List[ContentSource]:
        """Get saved content sources"""
        with self.get_session() as session:
            query = session.query(ContentSource)
            
            if source_type:
                query = query.filter(ContentSource.source_type == source_type)
            
            return query.order_by(ContentSource.extracted_at.desc()).limit(limit).all()
    
    # === Analytics Operations ===
    
    def update_post_analytics(
        self,
        post_id: int,
        views: int = None,
        likes: int = None,
        comments: int = None,
        shares: int = None
    ) -> Post:
        """Update post analytics"""
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
                session.refresh(post)
                
            return post
    
    def get_analytics_summary(self) -> Dict[str, Any]:
        """Get overall analytics summary"""
        with self.get_session() as session:
            total_posts = session.query(Post).count()
            published_posts = session.query(Post).filter(Post.status == 'published').count()
            
            # Calculate averages for published posts
            avg_engagement = session.query(Post).filter(
                Post.status == 'published',
                Post.engagement_rate > 0
            ).with_entities(
                func.avg(Post.engagement_rate)
            ).scalar() or 0
            
            total_views = session.query(func.sum(Post.views)).scalar() or 0
            total_likes = session.query(func.sum(Post.likes)).scalar() or 0
            
            return {
                'total_posts': total_posts,
                'published_posts': published_posts,
                'average_engagement_rate': round(avg_engagement, 2),
                'total_views': total_views,
                'total_likes': total_likes
            }
    
    # === Scheduled Posts Operations ===
    
    def get_scheduled_posts(self) -> List[Dict[str, Any]]:
        """Get all pending scheduled posts"""
        with self.get_session() as session:
            scheduled = session.query(ScheduledPost).filter(
                ScheduledPost.status == 'pending'
            ).order_by(ScheduledPost.scheduled_time.asc()).all()
            
            result = []
            for s in scheduled:
                post = session.query(Post).filter(Post.id == s.post_id).first()
                if post:
                    result.append({
                        'scheduled': s.to_dict(),
                        'post': post.to_dict()
                    })
            
            return result
    
    def get_posts_to_publish(self) -> List[Post]:
        """Get posts that should be published now"""
        with self.get_session() as session:
            current_time = datetime.utcnow()
            
            scheduled_ids = session.query(ScheduledPost.post_id).filter(
                ScheduledPost.scheduled_time <= current_time,
                ScheduledPost.status == 'pending'
            ).subquery()
            
            return session.query(Post).filter(
                Post.id.in_(scheduled_ids),
                Post.status == 'scheduled'
            ).all()


# Import fix for func
from sqlalchemy import func

# Create singleton instance
db = Database()


# Convenience functions
def save_post(content: str, **kwargs) -> Post:
    """Quick function to save a post"""
    return db.create_post(content, **kwargs)


def get_recent_posts(limit: int = 10) -> List[Post]:
    """Get recent posts"""
    return db.get_posts(limit=limit)


def get_scheduled_posts() -> List[Dict[str, Any]]:
    """Get scheduled posts"""
    return db.get_scheduled_posts()
