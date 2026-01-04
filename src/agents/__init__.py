"""AI Agents package."""
from .vision_agent import VisionAgent
from .extraction_agent import ExtractionAgent
from .reasoning_agent import ReasoningAgent
from .visualization_agent import VisualizationAgent
from .b2b_specialist_agent import B2BSpecialistAgent
from .enhanced_reasoning_agent import EnhancedReasoningAgent, PatternDetector
from .smart_visualization_engine import SmartVisualizationEngine, VisualizationType, InsightType
from .marketing_visualization_rules import (
    MarketingVisualizationRules,
    MarketingInsightCategory,
    MarketingColorSchemes
)
from .chart_generators import SmartChartGenerator
from .enhanced_visualization_agent import EnhancedVisualizationAgent
from .visualization_filters import SmartFilterEngine, FilterType, FilterCondition
from .filter_presets import FilterPresets

# Prompt Template System for versioned prompt management
from .prompt_templates import (
    PromptTemplate,
    PromptRegistry,
    PromptCategory,
    prompt_registry,
    get_prompt,
    list_prompts
)

# Shared Context for agent collaboration
from .shared_context import (
    SharedContext,
    ContextEntry,
    get_shared_context,
    reset_shared_context
)

# Agent Chain workflows
from .agent_chain import (
    campaign_health_check,
    deep_analysis,
    quick_insights,
    get_workflow_status,
    clear_workflow_state
)

__all__ = [
    "VisionAgent",
    "ExtractionAgent",
    "ReasoningAgent",
    "VisualizationAgent",
    "B2BSpecialistAgent",
    "EnhancedReasoningAgent",
    "PatternDetector",
    "SmartVisualizationEngine",
    "VisualizationType",
    "InsightType",
    "MarketingVisualizationRules",
    "MarketingInsightCategory",
    "MarketingColorSchemes",
    "SmartChartGenerator",
    "EnhancedVisualizationAgent",
    "SmartFilterEngine",
    "FilterType",
    "FilterCondition",
    "FilterPresets",
    # Prompt Templates
    "PromptTemplate",
    "PromptRegistry",
    "PromptCategory",
    "prompt_registry",
    "get_prompt",
    "list_prompts",
    # Shared Context
    "SharedContext",
    "ContextEntry",
    "get_shared_context",
    "reset_shared_context",
    # Agent Chain Workflows
    "campaign_health_check",
    "deep_analysis",
    "quick_insights",
    "get_workflow_status",
    "clear_workflow_state",
]
