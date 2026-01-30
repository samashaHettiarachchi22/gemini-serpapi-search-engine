"""
OPTIMIZED PostgreSQL Schema for Dashboard Analytics
Minimal storage, maximum efficiency
"""

from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import json
from config import Config

Base = declarative_base()


class SearchSnapshot(Base):
    """
    OPTIMIZED: Main table storing calculated metrics
    NO full JSON storage - only structured data
    """
    __tablename__ = 'search_snapshots_optimized'
    
    # Primary key
    id = Column(Integer, primary_key=True)
    
    # Query data
    query = Column(Text, nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    country = Column(String(10), default='us')
    language = Column(String(10), default='en')
    google_domain = Column(String(50), default='google.com')
    
    # ===== INTENT CLASSIFICATION (from Gemini) =====
    intent_type = Column(String(50))  # informational, transactional, navigational
    intent_confidence = Column(Float)  # 0.0 - 1.0
    
    # ===== FEATURE DETECTION (Boolean flags) =====
    has_knowledge_graph = Column(Boolean, default=False)
    has_answer_box = Column(Boolean, default=False)
    has_ai_overview = Column(Boolean, default=False)
    has_featured_snippet = Column(Boolean, default=False)
    has_related_questions = Column(Boolean, default=False)
    
    # ===== AI ANSWER METRICS =====
    brand_mentioned = Column(Boolean, default=False)
    ai_overview_text = Column(Text)  # Only if needed for display
    total_citations = Column(Integer, default=0)
    brand_citations = Column(Integer, default=0)
    
    # ===== ORGANIC RESULTS METRICS =====
    total_organic_results = Column(Integer, default=0)
    brand_organic_positions = Column(Integer, default=0)  # How many positions brand holds
    
    # ===== CALCULATED SCORES (store once, don't recalculate) =====
    visibility_score = Column(Float, default=0.0)  # 0-100
    intensity_score = Column(Float, default=0.0)   # 0-100
    share_of_voice_percentage = Column(Float, default=0.0)  # 0-100
    
    # ===== METADATA =====
    processing_time_ms = Column(Integer)  # How long it took to process
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    citations = relationship("CitationSource", back_populates="snapshot", cascade="all, delete-orphan")
    organic_positions = relationship("OrganicPosition", back_populates="snapshot", cascade="all, delete-orphan")
    execution_log = relationship("ExecutionLog", back_populates="snapshot", uselist=False, cascade="all, delete-orphan")
    
    # Indexes for fast queries
    __table_args__ = (
        Index('idx_query_timestamp', 'query', 'timestamp'),
        Index('idx_timestamp', 'timestamp'),
    )


class CitationSource(Base):
    """
    OPTIMIZED: Store only essential citation data with quality metrics
    For Citation Source Quality table in dashboard
    """
    __tablename__ = 'citation_sources_optimized'
    
    id = Column(Integer, primary_key=True)
    snapshot_id = Column(Integer, ForeignKey('search_snapshots_optimized.id', ondelete='CASCADE'), index=True)
    
    # Source identification
    domain = Column(String(255), index=True)
    url = Column(Text)
    title = Column(Text)
    
    # Source categorization
    source_type = Column(String(50))  # owned, competitor, authority, neutral
    is_brand = Column(Boolean, default=False)
    
    # Quality metrics
    authority_score = Column(Float)  # 0-100 (can be cached/pre-calculated)
    sentiment = Column(String(20))   # positive, neutral, negative (from Gemini)
    ai_reusability_score = Column(String(20))  # High, Medium, Low (how reusable for AI)
    
    # Metadata
    citation_index = Column(Integer)  # Position in AI overview
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    snapshot = relationship("SearchSnapshot", back_populates="citations")
    
    __table_args__ = (
        Index('idx_citation_snapshot', 'snapshot_id'),
        Index('idx_citation_domain', 'domain'),
    )


class OrganicPosition(Base):
    """
    OPTIMIZED: Track only position and domain for Share of Voice
    Minimal data storage
    """
    __tablename__ = 'organic_positions_optimized'
    
    id = Column(Integer, primary_key=True)
    snapshot_id = Column(Integer, ForeignKey('search_snapshots_optimized.id', ondelete='CASCADE'), index=True)
    
    # Position data
    position = Column(Integer)  # 1-10
    domain = Column(String(255), index=True)
    url = Column(Text)
    
    # Classification
    is_brand = Column(Boolean, default=False)
    
    # Metadata
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    snapshot = relationship("SearchSnapshot", back_populates="organic_positions")
    
    __table_args__ = (
        Index('idx_organic_snapshot', 'snapshot_id'),
        Index('idx_organic_position', 'snapshot_id', 'position'),
    )


class ExecutionLog(Base):
    """
    ERROR TRACKING & LOGGING
    Track execution, errors, and performance
    """
    __tablename__ = 'execution_logs_optimized'
    
    id = Column(Integer, primary_key=True)
    snapshot_id = Column(Integer, ForeignKey('search_snapshots_optimized.id', ondelete='CASCADE'), unique=True)
    
    # Execution info
    query = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Service status
    serpapi_status = Column(String(20))  # success, failed, timeout
    gemini_status = Column(String(20))   # success, failed, timeout
    database_status = Column(String(20))  # success, failed
    
    # Performance metrics
    serpapi_time_ms = Column(Integer)
    gemini_time_ms = Column(Integer)
    database_time_ms = Column(Integer)
    total_time_ms = Column(Integer)
    
    # Error tracking
    log_level = Column(String(20))  # INFO, WARNING, ERROR, CRITICAL
    error_service = Column(String(50))  # Which service failed
    error_message = Column(Text)
    error_traceback = Column(Text)
    
    # Relationship
    snapshot = relationship("SearchSnapshot", back_populates="execution_log")
    
    __table_args__ = (
        Index('idx_log_timestamp', 'timestamp'),
        Index('idx_log_level', 'log_level'),
    )


class SearchTrackingDB:
    """
    OPTIMIZED Database Handler
    Single transaction inserts, batch processing
    """
    
    def __init__(self, database_url: str = None):
        """Initialize database connection"""
        if database_url is None:
            database_url = Config.SQLALCHEMY_DATABASE_URI
        
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
    def create_tables(self):
        """Create all tables"""
        Base.metadata.create_all(self.engine)
        print("✅ Optimized tables created successfully")
    
    def drop_tables(self):
        """Drop all tables (use with caution!)"""
        Base.metadata.drop_all(self.engine)
        print("⚠️ Tables dropped")
    
    def save_complete_snapshot(self, 
                              snapshot_data: Dict[str, Any],
                              citations_data: List[Dict[str, Any]],
                              positions_data: List[Dict[str, Any]],
                              log_data: Dict[str, Any]) -> int:
        """
        OPTIMIZED: Single transaction to save everything
        
        Args:
            snapshot_data: Main snapshot metrics
            citations_data: List of citation sources
            positions_data: List of organic positions
            log_data: Execution log information
            
        Returns:
            snapshot_id: ID of saved snapshot
        """
        session = self.SessionLocal()
        
        try:
            # Create snapshot
            snapshot = SearchSnapshot(**snapshot_data)
            session.add(snapshot)
            session.flush()  # Get snapshot ID
            
            snapshot_id = snapshot.id
            
            # Batch insert citations
            if citations_data:
                citation_objects = [
                    CitationSource(snapshot_id=snapshot_id, **citation)
                    for citation in citations_data
                ]
                session.bulk_save_objects(citation_objects)
            
            # Batch insert organic positions
            if positions_data:
                position_objects = [
                    OrganicPosition(snapshot_id=snapshot_id, **position)
                    for position in positions_data
                ]
                session.bulk_save_objects(position_objects)
            
            # Create execution log
            log = ExecutionLog(snapshot_id=snapshot_id, **log_data)
            session.add(log)
            
            # Commit everything in single transaction
            session.commit()
            
            return snapshot_id
            
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_snapshot_by_id(self, snapshot_id: int) -> Optional[SearchSnapshot]:
        """Get snapshot by ID"""
        session = self.SessionLocal()
        try:
            return session.query(SearchSnapshot).filter_by(id=snapshot_id).first()
        finally:
            session.close()
    
    def get_historical_snapshots(self, query: str, days: int = 30) -> List[SearchSnapshot]:
        """Get historical snapshots for trend analysis"""
        session = self.SessionLocal()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            return session.query(SearchSnapshot)\
                .filter(SearchSnapshot.query == query)\
                .filter(SearchSnapshot.timestamp >= cutoff_date)\
                .order_by(SearchSnapshot.timestamp.desc())\
                .all()
        finally:
            session.close()


# Global instance
search_tracking_db_optimized = SearchTrackingDB()
