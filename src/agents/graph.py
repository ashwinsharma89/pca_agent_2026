from langgraph.graph import StateGraph, END
from typing import Literal

from src.agents.state import AgentState
from src.agents.nodes import (
    supervisor_node,
    data_analyst_node,
    visualizer_node,
    b2b_strategist_node
)

# Define the graph
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("Supervisor", supervisor_node)
workflow.add_node("Lead_Data_Analyst", data_analyst_node)
workflow.add_node("Visualization_Expert", visualizer_node)
workflow.add_node("B2B_Strategist", b2b_strategist_node)

# Add Edges
# Workers always report back to Supervisor for next steps/verification
workflow.add_edge("Lead_Data_Analyst", "Supervisor")
workflow.add_edge("Visualization_Expert", "Supervisor")
workflow.add_edge("B2B_Strategist", "Supervisor")

# Conditional Routing Logic
def route_supervisor(state: AgentState) -> Literal["Lead_Data_Analyst", "Visualization_Expert", "B2B_Strategist", "__end__"]:
    next_node = state.get("next", "FINISH")
    
    if next_node == "Lead_Data_Analyst":
        return "Lead_Data_Analyst"
    elif next_node == "Visualization_Expert":
        return "Visualization_Expert"
    elif next_node == "B2B_Strategist":
        return "B2B_Strategist"
    else:
        return "__end__"

workflow.add_conditional_edges(
    "Supervisor",
    route_supervisor,
    {
        "Lead_Data_Analyst": "Lead_Data_Analyst",
        "Visualization_Expert": "Visualization_Expert",
        "B2B_Strategist": "B2B_Strategist",
        "__end__": END
    }
)

# Entry Point
workflow.set_entry_point("Supervisor")

# Compile
agent_graph = workflow.compile()
