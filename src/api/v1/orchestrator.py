from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from langchain_core.messages import HumanMessage

from src.agents.graph import agent_graph
from src.agents.state import AgentState

router = APIRouter(prefix="/orchestrator", tags=["Multi-Agent Orchestrator"])

class AgentQueryRequest(BaseModel):
    query: str
    campaign_data: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = "system"

class AgentQueryResponse(BaseModel):
    success: bool
    final_response: str
    reports: List[Dict[str, Any]]
    steps: List[str]

@router.post("/run", response_model=AgentQueryResponse)
async def run_orchestrator(request: AgentQueryRequest):
    """
    Run the Multi-Agent Workflow on a query.
    """
    try:
        # Initialize State
        initial_state = {
            "messages": [HumanMessage(content=request.query)],
            "campaign_data": request.campaign_data or {},
            "reports": [],
            "errors": [],
            "next": None
        }
        
        # Run Graph
        final_state = await agent_graph.ainvoke(initial_state)
        
        # Extract Final Answer (last AIMessage)
        messages = final_state.get("messages", [])
        last_msg = messages[-1].content if messages else "No response generated"
        
        # Extract Steps taken (from reports sources)
        reports = final_state.get("reports", [])
        steps = [r.get("source") for r in reports]
        
        return AgentQueryResponse(
            success=True,
            final_response=str(last_msg),
            reports=reports,
            steps=steps
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
