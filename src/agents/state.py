from typing import TypedDict, Annotated, List, Union, Dict, Any, Optional
import operator
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

class AgentState(TypedDict):
    """
    The shared state of the Multi-Agent Graph.
    
    Attributes:
        messages: The full conversation history. LangGraph handles appending new messages.
        next: The name of the next agent to route to (set by Supervisor).
        campaign_data: Contextual data (e.g., current dataset summary).
        reports: Accumulated analysis reports or artifacts.
        errors: Any errors encountered during execution.
    """
    messages: Annotated[List[BaseMessage], operator.add]
    next: Optional[str]
    
    # Context
    campaign_data: Optional[Dict[str, Any]]
    
    # Outputs
    reports: Annotated[List[Dict[str, Any]], operator.add]
    images: Annotated[List[str], operator.add]  # Paths to generated chart images
    
    # Diagnostics
    errors: Annotated[List[str], operator.add]
