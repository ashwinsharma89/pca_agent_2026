"""
API Dependencies using Dependency Injection.

Provides FastAPI dependency functions that use the DI container.
This decouples the API from concrete implementations.
"""

from typing import Generator
from fastapi import Depends
from sqlalchemy.orm import Session

from src.di.containers import get_container, init_container
from src.interfaces.protocols import (
    IReasoningAgent,
    IOrchestrator,
    IRetriever,
    IBenchmarkEngine
)
from src.events.event_bus import EventBus


# Initialize container at module load
container = init_container()


# ============================================================================
# Database Dependencies
# ============================================================================

def get_db() -> Generator[Session, None, None]:
    """
    Get database session.
    
    Usage in FastAPI:
        @app.get("/campaigns")
        def list_campaigns(db: Session = Depends(get_db)):
            ...
    """
    session = container.database.session_factory()
    try:
        yield session
    finally:
        session.close()


# ============================================================================
# Repository Dependencies
# ============================================================================

def get_campaign_repository(db: Session = Depends(get_db)):
    """Get campaign repository."""
    return container.repositories.campaign_repository(session=db)


def get_analysis_repository(db: Session = Depends(get_db)):
    """Get analysis repository."""
    return container.repositories.analysis_repository(session=db)


def get_query_history_repository(db: Session = Depends(get_db)):
    """Get query history repository."""
    return container.repositories.query_history_repository(session=db)


# ============================================================================
# Knowledge Base Dependencies
# ============================================================================

def get_rag_retriever() -> IRetriever:
    """
    Get RAG retriever.
    
    Returns interface, not concrete implementation.
    Easy to swap implementations without changing API code.
    """
    return container.knowledge.rag_retriever()


def get_benchmark_engine() -> IBenchmarkEngine:
    """Get benchmark engine."""
    return container.knowledge.benchmark_engine()


# ============================================================================
# Agent Dependencies
# ============================================================================

def get_reasoning_agent() -> IReasoningAgent:
    """
    Get reasoning agent with fallback.
    
    Returns:
        ValidatedReasoningAgent with EnhancedReasoningAgent fallback
    """
    return container.agents.reasoning_with_fallback()


def get_vision_agent():
    """Get vision agent."""
    return container.agents.vision_agent()


def get_social_specialist():
    """Get social media specialist."""
    return container.agents.social_specialist()


def get_search_specialist():
    """Get search specialist."""
    return container.agents.search_specialist()


def get_programmatic_specialist():
    """Get programmatic specialist."""
    return container.agents.programmatic_specialist()


# ============================================================================
# Orchestrator Dependencies
# ============================================================================

def get_orchestrator() -> IOrchestrator:
    """
    Get resilient multi-agent orchestrator.
    
    Includes:
    - Automatic fallback
    - Retry logic
    - Circuit breakers
    """
    return container.orchestrators.resilient_orchestrator()


# ============================================================================
# Service Dependencies
# ============================================================================

def get_analytics_service():
    """Get analytics service."""
    return container.services.analytics_expert()


def get_user_service(db: Session = Depends(get_db)):
    """Get user service."""
    return container.services.user_service(session=db)


def get_campaign_service():
    """Get campaign service."""
    return container.services.campaign_service()


# ============================================================================
# Event Bus Dependencies
# ============================================================================

def get_event_bus() -> EventBus:
    """Get global event bus."""
    return container.events.event_bus()


# ============================================================================
# Example Usage in API Endpoints
# ============================================================================

"""
Example 1: Using reasoning agent in API

from fastapi import APIRouter, Depends
from src.api.dependencies import get_reasoning_agent, get_event_bus
from src.interfaces.protocols import IReasoningAgent

router = APIRouter()

@router.post("/analyze")
async def analyze_campaign(
    data: CampaignData,
    agent: IReasoningAgent = Depends(get_reasoning_agent),
    event_bus: EventBus = Depends(get_event_bus)
):
    # Agent is injected - no direct instantiation
    result = await agent.analyze(data.to_dataframe())
    
    # Publish event
    event_bus.publish(AnalysisCompleted(result=result))
    
    return result


Example 2: Using orchestrator

@router.post("/chat")
async def chat(
    query: str,
    orchestrator: IOrchestrator = Depends(get_orchestrator)
):
    # Orchestrator handles all agent coordination
    result = await orchestrator.run(
        query=query,
        campaign_data=data
    )
    
    return result


Example 3: Using repository

from src.api.dependencies import get_campaign_repository

@router.get("/campaigns/{campaign_id}")
def get_campaign(
    campaign_id: str,
    repo = Depends(get_campaign_repository)
):
    campaign = repo.get(campaign_id)
    return campaign


Example 4: Testing with mocks

from unittest.mock import Mock
from fastapi.testclient import TestClient

def test_analyze_endpoint():
    # Create mock agent
    mock_agent = Mock(spec=IReasoningAgent)
    mock_agent.analyze.return_value = {"insights": []}
    
    # Override dependency
    app.dependency_overrides[get_reasoning_agent] = lambda: mock_agent
    
    # Test endpoint
    client = TestClient(app)
    response = client.post("/analyze", json={...})
    
    # Verify mock was called
    mock_agent.analyze.assert_called_once()
    
    # Clean up
    app.dependency_overrides.clear()
"""
