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

    # Category to indicate source/type (e.g. 'gemini-only', 'serp', 'test')
    category = Column(String(50), nullable=True)
    
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


class APICallLog(Base):
    """
    UNIFIED: Track all AI API calls (Claude, Gemini, etc.)
    Single table for all services
    """
    __tablename__ = 'api_call_logs'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Service identification
    service = Column(String(50), nullable=False, index=True)  # 'claude', 'gemini', 'openai'
    model = Column(String(100))
    
    # Request data
    prompt = Column(Text, nullable=False)
    max_tokens = Column(Integer, nullable=True)
    
    # Response data
    response = Column(Text)
    response_time_ms = Column(Integer)
    
    # Token tracking
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    
    # Cost tracking
    estimated_cost = Column(Float, nullable=True)
    
    # Status tracking
    success = Column(Boolean, default=True, index=True)
    error_message = Column(Text, nullable=True)
    
    # Metadata
    user_ip = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_api_service_timestamp', 'service', 'timestamp'),
        Index('idx_api_success', 'success'),
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
    
    def log_api_call(self,
                    service: str,
                    prompt: str,
                    model: str,
                    response: Optional[str],
                    response_time_ms: int,
                    success: bool = True,
                    error_message: Optional[str] = None,
                    max_tokens: Optional[int] = None,
                    input_tokens: Optional[int] = None,
                    output_tokens: Optional[int] = None,
                    total_tokens: Optional[int] = None,
                    estimated_cost: Optional[float] = None,
                    user_ip: Optional[str] = None) -> int:
        """
        Log any AI API call to unified table
        
        Args:
            service: Service name ('claude', 'gemini', etc.)
            prompt: User's prompt
            model: Model used
            response: AI response text (None if error)
            response_time_ms: Response time in milliseconds
            success: Whether call was successful
            error_message: Error message if failed
            max_tokens: Max tokens setting
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens used
            total_tokens: Total tokens used
            estimated_cost: Estimated cost in USD
            user_ip: User's IP address (optional)
            
        Returns:
            log_id: ID of the log entry
        """
        session = self.SessionLocal()
        
        try:
            log = APICallLog(
                service=service,
                prompt=prompt,
                model=model,
                max_tokens=max_tokens,
                response=response,
                response_time_ms=response_time_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                estimated_cost=estimated_cost,
                success=success,
                error_message=error_message,
                user_ip=user_ip
            )
            session.add(log)
            session.commit()
            
            return log.id
            
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_api_stats(self, service: Optional[str] = None, days: int = 7) -> Dict[str, Any]:
        """
        Get API usage statistics for any service FROM DATABASE
        
        Args:
            service: Filter by service ('claude', 'gemini', etc.) - None for all
            days: Number of days to look back
            
        Returns:
            Dictionary with stats from DATABASE (persistent)
        """
        session = self.SessionLocal()
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            query = session.query(APICallLog)\
                .filter(APICallLog.timestamp >= cutoff_date)
            
            if service:
                query = query.filter(APICallLog.service == service)
            
            logs = query.all()
            
            if not logs:
                return {
                    "service": service or "all",
                    "total_calls": 0,
                    "successful_calls": 0,
                    "failed_calls": 0,
                    "success_rate": 0.0,
                    "avg_response_time_ms": 0,
                    "period_days": days,
                    "source": "database"
                }
            
            total = len(logs)
            successful = sum(1 for log in logs if log.success)
            failed = total - successful
            avg_time = sum(log.response_time_ms for log in logs if log.response_time_ms) / total if total > 0 else 0
            
            return {
                "service": service or "all",
                "total_calls": total,
                "successful_calls": successful,
                "failed_calls": failed,
                "success_rate": round((successful / total * 100) if total > 0 else 0.0, 2),
                "avg_response_time_ms": int(avg_time),
                "period_days": days,
                "source": "database"
            }
            
        finally:
            session.close()
    
    def get_api_cost_analysis(self, service: Optional[str] = None, days: int = 7) -> Dict[str, Any]:
        """
        Calculate costs from database logs (more accurate than in-memory)
        
        Args:
            service: Service to analyze
            days: Days to look back
            
        Returns:
            Cost analysis with token estimates
        """
        session = self.SessionLocal()
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            query = session.query(APICallLog)\
                .filter(APICallLog.timestamp >= cutoff_date)\
                .filter(APICallLog.success == True)
            
            if service:
                query = query.filter(APICallLog.service == service)
            
            logs = query.all()
            
            # Token estimation fallback (4 chars = 1 token)
            def estimate_tokens(text):
                return len(text or "") // 4
            
            # Cost per 1k tokens
            cost_per_1k = {
                'gemini': 0.0001,
                'claude': 0.0003,
                'serpapi': 0.002
            }
            
            total_cost = 0
            total_tokens = 0
            breakdown = {}
            actual_token_count = 0
            estimated_token_count = 0
            
            for log in logs:
                svc = log.service
                
                # Use stored token data if available (100% accurate for Claude)
                # Otherwise estimate from text (for older/legacy records)
                if log.total_tokens and log.total_tokens > 0:
                    tokens = log.total_tokens
                    actual_token_count += 1
                else:
                    # Fallback to estimation
                    input_tokens = estimate_tokens(log.prompt)
                    output_tokens = estimate_tokens(log.response)
                    tokens = input_tokens + output_tokens
                    estimated_token_count += 1
                
                # Use stored cost if available, otherwise calculate
                if log.estimated_cost and log.estimated_cost > 0:
                    cost = log.estimated_cost
                else:
                    cost = (tokens / 1000) * cost_per_1k.get(svc, 0)
                
                total_tokens += tokens
                total_cost += cost
                
                if svc not in breakdown:
                    breakdown[svc] = {'calls': 0, 'tokens': 0, 'cost': 0, 'actual_tokens': 0, 'estimated_tokens': 0}
                
                breakdown[svc]['calls'] += 1
                breakdown[svc]['tokens'] += tokens
                breakdown[svc]['cost'] += cost
                if log.total_tokens and log.total_tokens > 0:
                    breakdown[svc]['actual_tokens'] += 1
                else:
                    breakdown[svc]['estimated_tokens'] += 1
            
            # Format breakdown
            for svc in breakdown:
                breakdown[svc]['cost'] = round(breakdown[svc]['cost'], 4)
            
            daily_avg_cost = total_cost / days if days > 0 else 0
            
            accuracy_pct = (actual_token_count / len(logs) * 100) if logs else 0
            
            return {
                "period_days": days,
                "total_calls": len(logs),
                "total_tokens": total_tokens,
                "total_cost_usd": round(total_cost, 4),
                "avg_cost_per_call": round(total_cost / len(logs), 6) if logs else 0,
                "breakdown": breakdown,
                "estimated_monthly_cost": round(daily_avg_cost * 30, 2),
                "accuracy": {
                    "actual_token_data": actual_token_count,
                    "estimated_token_data": estimated_token_count,
                    "accuracy_percentage": round(accuracy_pct, 1),
                    "note": "Claude returns 100% accurate tokens, Gemini uses estimation"
                },
                "source": "database"
            }
            
        finally:
            session.close()


# Global instance
search_tracking_db_optimized = SearchTrackingDB()
