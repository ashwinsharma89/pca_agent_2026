import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage

from src.agents.state import AgentState
from src.agents.graph import agent_graph

@pytest.mark.asyncio
async def test_langgraph_routing_flow():
    """
    Test that the Supervisor routes to Data Analyst, then Visualizer, then Finishes.
    """
    
    # Mock the LLM in supervisor_node to return specific sequence of decisions
    # 1. First call: Route to Data Analyst
    # 2. Second call: Route to visualizer (after data is fetched)
    # 3. Third call: Finish
    
    mock_responses = [
        AIMessage(content='{"next": "Lead_Data_Analyst", "reason": "Fetch data"}'),
        AIMessage(content='{"next": "Visualization_Expert", "reason": "Draw chart"}'),
        AIMessage(content='{"next": "FINISH", "reason": "Done"}')
    ]
    
    # We need to patch the ChatOpenAI.ainvoke used inside supervisor_node
    with patch("src.agents.nodes.ChatOpenAI") as MockLLM:
        mock_llm_instance = MockLLM.return_value
        mock_llm_instance.ainvoke = AsyncMock(side_effect=mock_responses)
        
        # Also patch the worker agents to avoid real execution
        with patch("src.agents.nodes.query_engine") as mock_qe, \
             patch("src.agents.nodes.viz_agent") as mock_viz:
            
            # Setup Worker Mocks
            mock_df = MagicMock()
            mock_df.empty = False
            mock_df.to_dict.return_value = [{"spend": 100}]
            
            mock_qe.answer_question = AsyncMock(return_value=("Here is the data", "SELECT *", mock_df))
            mock_viz.create_dashboard_visualizations.return_value = {"bar_chart": "fig_obj"}
            
            # Run the Graph
            inputs = {
                "messages": [HumanMessage(content="Show me spend analysis")]
            }
            
            # Run
            final_state = await agent_graph.ainvoke(inputs)
            
            # VERIFICATION
            
            # 1. Check final state has reports
            assert len(final_state["reports"]) == 2
            assert final_state["reports"][0]["source"] == "Data Analyst"
            assert final_state["reports"][1]["source"] == "Visualizer"
            
            # 2. Check conversation history
            # Initial Human + (DataAnalyst response) + (Visualizer response) 
            # Note: Supervisor output isn't added to 'messages' in my implementation, only 'next' logic
            # Worker nodes append AIMessages.
            assert len(final_state["messages"]) == 3  # Human + DataAnalyst + Visualizer
            
            print("Graph execution successful!")
