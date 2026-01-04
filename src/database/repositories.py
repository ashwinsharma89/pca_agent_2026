"""
Repository pattern for data access.
Provides clean abstraction over database operations.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from src.database.models import QueryHistory, LLMUsage

logger = logging.getLogger(__name__)


class BaseRepository:
    """Base repository with common operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def commit(self):
        """Commit transaction."""
        self.session.commit()
    
    def rollback(self):
        """Rollback transaction."""
        self.session.rollback()
    
    def flush(self):
        """Flush changes to database."""
        self.session.flush()





class QueryHistoryRepository(BaseRepository):
    """Repository for QueryHistory operations."""
    
    def create(self, query_data: Dict[str, Any]) -> QueryHistory:
        """Create a new query history entry."""
        query = QueryHistory(**query_data)
        self.session.add(query)
        self.session.flush()
        return query
    
    def get_by_id(self, query_id: int) -> Optional[QueryHistory]:
        """Get query by ID."""
        return self.session.query(QueryHistory).filter(QueryHistory.id == query_id).first()
    
    def get_recent(self, limit: int = 50) -> List[QueryHistory]:
        """Get recent queries."""
        return self.session.query(QueryHistory).order_by(
            desc(QueryHistory.created_at)
        ).limit(limit).all()
    
    def search_by_text(self, search_text: str, limit: int = 20) -> List[QueryHistory]:
        """Search queries by text."""
        return self.session.query(QueryHistory).filter(
            QueryHistory.user_query.ilike(f'%{search_text}%')
        ).order_by(desc(QueryHistory.created_at)).limit(limit).all()
    
    def get_by_status(self, status: str, limit: int = 100) -> List[QueryHistory]:
        """Get queries by status."""
        return self.session.query(QueryHistory).filter(
            QueryHistory.status == status
        ).order_by(desc(QueryHistory.created_at)).limit(limit).all()


class LLMUsageRepository(BaseRepository):
    """Repository for LLM usage tracking."""
    
    def create(self, usage_data: Dict[str, Any]) -> LLMUsage:
        """Create a new LLM usage entry."""
        usage = LLMUsage(**usage_data)
        self.session.add(usage)
        self.session.flush()
        return usage
    
    def get_usage_by_provider(self, provider: str, start_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get aggregated usage by provider."""
        from sqlalchemy import func
        
        query = self.session.query(
            func.sum(LLMUsage.total_tokens).label('total_tokens'),
            func.sum(LLMUsage.cost).label('total_cost'),
            func.count(LLMUsage.id).label('request_count')
        ).filter(LLMUsage.provider == provider)
        
        if start_date:
            query = query.filter(LLMUsage.created_at >= start_date)
        
        result = query.first()
        
        return {
            'provider': provider,
            'total_tokens': int(result.total_tokens or 0),
            'total_cost': float(result.total_cost or 0),
            'request_count': int(result.request_count or 0)
        }
    
    def get_usage_by_operation(self, operation: str, start_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get aggregated usage by operation."""
        from sqlalchemy import func
        
        query = self.session.query(
            func.sum(LLMUsage.total_tokens).label('total_tokens'),
            func.sum(LLMUsage.cost).label('total_cost'),
            func.count(LLMUsage.id).label('request_count')
        ).filter(LLMUsage.operation == operation)
        
        if start_date:
            query = query.filter(LLMUsage.created_at >= start_date)
        
        result = query.first()
        
        return {
            'operation': operation,
            'total_tokens': int(result.total_tokens or 0),
            'total_cost': float(result.total_cost or 0),
            'request_count': int(result.request_count or 0)
        }
    
    def get_total_usage(self, start_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get total usage across all providers."""
        from sqlalchemy import func
        
        query = self.session.query(
            func.sum(LLMUsage.total_tokens).label('total_tokens'),
            func.sum(LLMUsage.cost).label('total_cost'),
            func.count(LLMUsage.id).label('request_count')
        )
        
        if start_date:
            query = query.filter(LLMUsage.created_at >= start_date)
        
        result = query.first()
        
        return {
            'total_tokens': int(result.total_tokens or 0),
            'total_cost': float(result.total_cost or 0),
            'request_count': int(result.request_count or 0)
        }




from src.database.models import Campaign, Analysis, CampaignContext

class CampaignRepository(BaseRepository):
    """Repository for Campaign operations."""
    
    def create(self, data: Dict[str, Any]) -> Campaign:
        """Create a new campaign."""
        campaign = Campaign(**data)
        self.session.add(campaign)
        self.session.flush()
        return campaign
    
    def create_bulk(self, data_list: List[Dict[str, Any]], batch_size: int = 50) -> List[Campaign]:
        """
        Bulk create campaigns with batching to avoid timeouts.
        Returns all created campaigns.
        """
        all_campaigns = []
        total = len(data_list)
        
        for i in range(0, total, batch_size):
            batch_data = data_list[i:i + batch_size]
            batch_campaigns = [Campaign(**data) for data in batch_data]
            
            try:
                self.session.add_all(batch_campaigns)
                self.session.commit()
                # Refresh instances if needed, or just append to list (ids will be populated)
                all_campaigns.extend(batch_campaigns)
            except Exception as e:
                self.session.rollback()
                # Log error but try to continue or re-raise? 
                # For bulk import, failing safely or re-raising is a choice. 
                # Re-raising is safer to alert the user.
                raise e
                
        return all_campaigns
    
    def get_by_campaign_id(self, campaign_id: str) -> Optional[Campaign]:
        """Get campaign by its unique ID string."""
        return self.session.query(Campaign).filter(
            Campaign.campaign_id == campaign_id
        ).first()
    
    def get_all(self, limit: int = 100, offset: int = 0) -> List[Campaign]:
        """Get all campaigns with pagination."""
        return self.session.query(Campaign).order_by(
            desc(Campaign.created_at)
        ).offset(offset).limit(limit).all()
    
    def search(self, filters: Dict[str, Any], limit: int = 100) -> List[Campaign]:
        """Search campaigns with filters."""
        query = self.session.query(Campaign)
        
        if filters:
            for key, value in filters.items():
                if hasattr(Campaign, key) and value is not None:
                    query = query.filter(getattr(Campaign, key) == value)
        
        return query.order_by(desc(Campaign.created_at)).limit(limit).all()
    
    def get_aggregated_metrics(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get aggregated metrics across campaigns."""
        from sqlalchemy import func
        
        query = self.session.query(
            func.sum(Campaign.spend).label('total_spend'),
            func.sum(Campaign.impression).label('total_impressions'),
            func.sum(Campaign.clicks).label('total_clicks'),
            func.sum(Campaign.conversions).label('total_conversions')
        )
        
        if filters:
            for key, value in filters.items():
                if hasattr(Campaign, key) and value is not None:
                    query = query.filter(getattr(Campaign, key) == value)
        
        result = query.first()
        
        return {
            "total_spend": float(result.total_spend or 0),
            "total_impressions": int(result.total_impressions or 0),
            "total_clicks": int(result.total_clicks or 0),
            "total_conversions": int(result.total_conversions or 0)
        }


class AnalysisRepository(BaseRepository):
    """Repository for Analysis operations."""
    
    def create(self, data: Dict[str, Any]) -> Analysis:
        """Create a new analysis."""
        analysis = Analysis(**data)
        self.session.add(analysis)
        self.session.flush()
        return analysis
    
    def get_by_campaign(self, campaign_id: int, limit: int = 10) -> List[Analysis]:
        """Get analyses for a specific campaign."""
        return self.session.query(Analysis).filter(
            Analysis.campaign_id == campaign_id
        ).order_by(desc(Analysis.created_at)).limit(limit).all()


class CampaignContextRepository(BaseRepository):
    """Repository for Campaign Context operations."""
    
    def update(self, campaign_id: int, data: Dict[str, Any]) -> CampaignContext:
        """Update or create campaign context."""
        context = self.session.query(CampaignContext).filter(
            CampaignContext.campaign_id == campaign_id
        ).first()
        
        if context:
            context.context_data = data
        else:
            context = CampaignContext(campaign_id=campaign_id, context_data=data)
            self.session.add(context)
        
        self.session.flush()
        return context
