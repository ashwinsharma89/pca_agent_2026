import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from langchain_core.messages import AIMessage
import src.api.v1.orchestrator as orchestrator_module

# Import app to create TestClient
from src.api.main import app

client = TestClient(app)

@pytest.fixture
def mock_graph_invoke():
    """Mock the LangGraph ainvoke method using manual replacement"""
    # 1. Save original
    original_graph = orchestrator_module.agent_graph
    
    # 2. Create Mock
    mock_graph = MagicMock()
    mock_invoke = AsyncMock()
    mock_graph.ainvoke = mock_invoke
    
    # 3. Replace
    orchestrator_module.agent_graph = mock_graph
    
    yield mock_invoke
    
    # 4. Restore
    orchestrator_module.agent_graph = original_graph

def test_run_orchestrator_api_success(mock_graph_invoke):
    """
    Test the successful execution of the orchestrator API.
    """
    # Setup Mock Return Value for Graph
    mock_graph_invoke.return_value = {
        "messages": [AIMessage(content="Here is the final answer.")],
        "reports": [{"source": "Data Analyst", "data_summary": "Spent $100"}],
        "steps": ["Lead_Data_Analyst"]
    }
    
    # Payload
    payload = {
        "query": "How much did we spend?",
        "campaign_data": {"active_dataset": []}
    }
    
    # Call API
    response = client.post("/api/v1/orchestrator/run", json=payload)
    
    if response.status_code != 200:
        print(f"\nAPI Error Response: {response.json()}")
    
    # Verify Response
    assert response.status_code == 200
    data = response.json()
    
    assert data["success"] is True
    assert data["final_response"] == "Here is the final answer."
    assert len(data["reports"]) == 1
    assert data["reports"][0]["source"] == "Data Analyst"
    
    # Verify Graph was called
    mock_graph_invoke.assert_called_once()
    call_args = mock_graph_invoke.call_args[0][0] # First arg of first call
    assert call_args["messages"][0].content == "How much did we spend?"

def test_run_orchestrator_api_error_handling(mock_graph_invoke):
    """
    Test error handling in the orchestrator API.
    """
    # Setup Mock to Raise Exception
    mock_graph_invoke.side_effect = Exception("Graph execution failed")
    
    payload = {"query": "Crash me"}
    
    response = client.post("/api/v1/orchestrator/run", json=payload)
    
    assert response.status_code == 500
    error_detail = response.json()["detail"]
    assert "Graph execution failed" in error_detail
