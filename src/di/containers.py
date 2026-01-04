"""
Expanded Dependency Injection containers.

Provides comprehensive DI coverage for:
- Database & Repositories
- Knowledge Base (RAG, Benchmarks)
- All 21 Agents
- Orchestrators
- Services
- Event Bus
"""

import os
from dependency_injector import containers, providers
from src.database.connection import DatabaseManager, DatabaseConfig, get_db_session
from src.database.repositories import (
    CampaignRepository,
    AnalysisRepository,
    QueryHistoryRepository,
    LLMUsageRepository,
    CampaignContextRepository
)


# ============================================================================
# Database Container
# ============================================================================

class DatabaseContainer(containers.DeclarativeContainer):
    """Container for database-related dependencies."""
    
    config = providers.Configuration()
    
    # Database configuration
    db_config = providers.Singleton(
        DatabaseConfig
    )
    
    # Database manager
    db_manager = providers.Singleton(
        DatabaseManager,
        config=db_config
    )
    
    # Session factory
    session_factory = providers.Factory(
        get_db_session
    )


# ============================================================================
# Repository Container
# ============================================================================

class RepositoryContainer(containers.DeclarativeContainer):
    """Container for repository dependencies."""
    
    db = providers.DependenciesContainer()
    
    # Repositories
    campaign_repository = providers.Factory(
        CampaignRepository,
        session=db.session_factory
    )
    
    analysis_repository = providers.Factory(
        AnalysisRepository,
        session=db.session_factory
    )
    
    query_history_repository = providers.Factory(
        QueryHistoryRepository,
        session=db.session_factory
    )
    
    llm_usage_repository = providers.Factory(
        LLMUsageRepository,
        session=db.session_factory
    )
    
    campaign_context_repository = providers.Factory(
        CampaignContextRepository,
        session=db.session_factory
    )


# ============================================================================
# Knowledge Base Container
# ============================================================================

class KnowledgeBaseContainer(containers.DeclarativeContainer):
    """Container for knowledge base dependencies."""
    
    config = providers.Configuration()
    
    # RAG Retriever (Hybrid)
    from src.knowledge.vector_store import HybridRetriever
    
    rag_retriever = providers.Singleton(
        HybridRetriever,
        collection_name=config.rag_collection_name.as_(str, default="pca_knowledge"),
        embedding_model=config.embedding_model.as_(str, default="text-embedding-3-small")
    )
    
    # Benchmark Engine
    from src.knowledge.benchmark_engine import DynamicBenchmarkEngine as BenchmarkEngine
    
    benchmark_engine = providers.Singleton(
        BenchmarkEngine,
        data_path=config.benchmark_data_path.as_(str, default="data/benchmarks.json")
    )


# ============================================================================
# Agent Container
# ============================================================================

class AgentContainer(containers.DeclarativeContainer):
    """Container for all agent dependencies."""
    
    config = providers.Configuration()
    knowledge = providers.DependenciesContainer()
    
    # Pattern Detector
    from src.agents.enhanced_reasoning_agent import PatternDetector
    
    pattern_detector = providers.Factory(
        PatternDetector
    )
    
    # Reasoning Agents
    from src.agents.reasoning_agent import ReasoningAgent
    from src.agents.enhanced_reasoning_agent import EnhancedReasoningAgent
    from src.agents.validated_reasoning_agent import ValidatedReasoningAgent
    
    reasoning_agent = providers.Factory(
        ReasoningAgent,
        rag_retriever=knowledge.rag_retriever,
        benchmark_engine=knowledge.benchmark_engine
    )
    
    enhanced_reasoning_agent = providers.Factory(
        EnhancedReasoningAgent,
        rag_retriever=knowledge.rag_retriever,
        benchmark_engine=knowledge.benchmark_engine
    )
    
    validated_reasoning_agent = providers.Factory(
        ValidatedReasoningAgent,
        rag_retriever=knowledge.rag_retriever,
        benchmark_engine=knowledge.benchmark_engine
    )
    
    # Vision Agent
    from src.agents.vision_agent import VisionAgent
    
    vision_agent = providers.Factory(
        VisionAgent,
        api_key=config.openai_api_key
    )
    
    # Channel Specialists
    from src.agents.channel_specialists.social_agent import SocialChannelAgent as SocialMediaSpecialist
    from src.agents.channel_specialists.search_agent import SearchChannelAgent as SearchSpecialist
    from src.agents.channel_specialists.programmatic_agent import ProgrammaticAgent as ProgrammaticSpecialist
    
    social_specialist = providers.Factory(
        SocialMediaSpecialist,
        rag_retriever=knowledge.rag_retriever
    )
    
    search_specialist = providers.Factory(
        SearchSpecialist,
        rag_retriever=knowledge.rag_retriever
    )
    
    programmatic_specialist = providers.Factory(
        ProgrammaticSpecialist,
        rag_retriever=knowledge.rag_retriever
    )
    
    # Resilience Components
    from src.agents.agent_resilience import AgentFallback, CircuitBreaker
    
    # Reasoning agent with fallback
    reasoning_with_fallback = providers.Factory(
        AgentFallback,
        primary_agent=validated_reasoning_agent,
        fallback_agent=enhanced_reasoning_agent,
        name="ReasoningAgent"
    )
    
    # Circuit breakers
    rag_circuit_breaker = providers.Singleton(
        CircuitBreaker,
        failure_threshold=config.circuit_breaker_threshold.as_(int, default=5),
        recovery_timeout=config.circuit_breaker_timeout.as_(float, default=60.0)
    )
    
    benchmark_circuit_breaker = providers.Singleton(
        CircuitBreaker,
        failure_threshold=config.circuit_breaker_threshold.as_(int, default=5),
        recovery_timeout=config.circuit_breaker_timeout.as_(float, default=60.0)
    )


# ============================================================================
# Orchestrator Container
# ============================================================================

class OrchestratorContainer(containers.DeclarativeContainer):
    """Container for orchestrator dependencies."""
    
    agents = providers.DependenciesContainer()
    knowledge = providers.DependenciesContainer()
    
    # Multi-Agent Orchestrator
    from src.agents.multi_agent_orchestrator import MultiAgentOrchestrator
    
    multi_agent_orchestrator = providers.Factory(
        MultiAgentOrchestrator
    )
    
    # Resilient Orchestrator
    from src.agents.resilient_orchestrator import ResilientMultiAgentOrchestrator
    
    resilient_orchestrator = providers.Factory(
        ResilientMultiAgentOrchestrator,
        rag_retriever=knowledge.rag_retriever,
        benchmark_engine=knowledge.benchmark_engine
    )


# ============================================================================
# Service Container
# ============================================================================

class ServiceContainer(containers.DeclarativeContainer):
    """Container for service-level dependencies."""
    
    config = providers.Configuration()
    db = providers.DependenciesContainer()
    repositories = providers.DependenciesContainer()
    agents = providers.DependenciesContainer()
    
    # Analytics services
    from src.analytics.auto_insights import MediaAnalyticsExpert
    
    analytics_expert = providers.Factory(
        MediaAnalyticsExpert,
        use_anthropic=config.use_anthropic
    )
    
    # User Service
    from src.services.user_service import UserService
    
    user_service = providers.Factory(
        UserService,
        session=db.session_factory
    )
    
    # Campaign Service
    from src.services.campaign_service import CampaignService
    
    campaign_service = providers.Factory(
        CampaignService,
        campaign_repo=repositories.campaign_repository,
        analysis_repo=repositories.analysis_repository,
        context_repo=repositories.campaign_context_repository
    )


# ============================================================================
# Event Bus Container
# ============================================================================

class EventBusContainer(containers.DeclarativeContainer):
    """Container for event bus and event-driven components."""
    
    from src.events.event_bus import EventBus
    
    # Global event bus
    event_bus = providers.Singleton(
        EventBus,
        max_history=1000
    )
    
    # Event listeners
    from src.events.event_listeners import (
        AnalyticsEventListener,
        MonitoringEventListener,
        AuditEventListener
    )
    
    analytics_listener = providers.Singleton(
        AnalyticsEventListener
    )
    
    monitoring_listener = providers.Singleton(
        MonitoringEventListener
    )
    
    audit_listener = providers.Singleton(
        AuditEventListener
    )


# ============================================================================
# Application Container
# ============================================================================

class ApplicationContainer(containers.DeclarativeContainer):
    """
    Main application container.
    
    Wires all dependencies together with proper hierarchy:
    Database → Repositories → Knowledge Base → Agents → Orchestrators → Services
    """
    
    config = providers.Configuration()
    
    # Wire configuration from environment
    config.use_anthropic.from_env("USE_ANTHROPIC", default=False, as_=bool)
    config.anthropic_api_key.from_env("ANTHROPIC_API_KEY", default="")
    config.openai_api_key.from_env("OPENAI_API_KEY", default="")
    config.gemini_api_key.from_env("GEMINI_API_KEY", default="")
    
    # RAG configuration
    config.rag_collection_name.from_env("RAG_COLLECTION_NAME", default="pca_knowledge")
    config.embedding_model.from_env("EMBEDDING_MODEL", default="text-embedding-3-small")
    
    # Benchmark configuration
    config.benchmark_data_path.from_env("BENCHMARK_DATA_PATH", default="data/benchmarks.json")
    
    # Circuit breaker configuration
    config.circuit_breaker_threshold.from_env("CIRCUIT_BREAKER_THRESHOLD", default=5, as_=int)
    config.circuit_breaker_timeout.from_env("CIRCUIT_BREAKER_TIMEOUT", default=60.0, as_=float)
    
    # Database container
    database = providers.Container(
        DatabaseContainer
    )
    
    # Repository container
    repositories = providers.Container(
        RepositoryContainer,
        db=database
    )
    
    # Knowledge base container
    knowledge = providers.Container(
        KnowledgeBaseContainer,
        config=config
    )
    
    # Agent container
    agents = providers.Container(
        AgentContainer,
        config=config,
        knowledge=knowledge
    )
    
    # Orchestrator container
    orchestrators = providers.Container(
        OrchestratorContainer,
        agents=agents,
        knowledge=knowledge
    )
    
    # Service container
    services = providers.Container(
        ServiceContainer,
        config=config,
        db=database,
        repositories=repositories,
        agents=agents
    )
    
    # Event bus container
    events = providers.Container(
        EventBusContainer
    )


# ============================================================================
# Global Application Container Instance
# ============================================================================

app_container = ApplicationContainer()


def init_container():
    """
    Initialize the application container.
    
    This should be called at application startup to:
    1. Initialize database
    2. Load knowledge base
    3. Set up event listeners
    4. Warm up agents
    """
    # Initialize database
    app_container.database.db_manager().initialize()
    
    # Initialize event listeners
    app_container.events.analytics_listener()
    app_container.events.monitoring_listener()
    app_container.events.audit_listener()
    
    return app_container


def get_container() -> ApplicationContainer:
    """Get the application container."""
    return app_container


# ============================================================================
# Convenience Functions
# ============================================================================

def get_reasoning_agent():
    """Get reasoning agent with fallback."""
    return app_container.agents.reasoning_with_fallback()


def get_orchestrator():
    """Get resilient orchestrator."""
    return app_container.orchestrators.resilient_orchestrator()


def get_event_bus():
    """Get global event bus."""
    return app_container.events.event_bus()


def get_analytics_service():
    """Get analytics service."""
    return app_container.services.analytics_expert()


def get_user_service():
    """Get user service."""
    return app_container.services.user_service()
