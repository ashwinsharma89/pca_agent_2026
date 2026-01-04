
import pytest
import sys
import os
sys.path.append(os.getcwd())
from unittest.mock import MagicMock
from src.connectors.connector_manager import AdConnectorManager
import pybreaker

def test_manager_circuit_breaker():
    print("🚀 Starting Manager Resilience Test...")
    manager = AdConnectorManager(use_mock=True, platforms=[])
    
    # Inject a mock connector
    mock_connector = MagicMock()
    # Configure it to fail
    mock_connector.get_campaigns.side_effect = Exception("API Down")
    
    manager._connectors["test_platform"] = mock_connector
    
    # 1. Trigger failures
    print("Simulating 5 failures...")
    for i in range(5):
        try:
            manager.get_campaigns(platforms=["test_platform"])
            print(f"Call {i+1}: Failed (as expected)")
        except Exception as e:
            print(f"Call {i+1}: Exception {e}")

    # 2. Check Breaker State
    breaker = manager._get_breaker("test_platform")
    print(f"Breaker state after 5 failures: {breaker.current_state}")
    
    # 3. Next call should be BLOCKED (CircuitBreakerError caught internally)
    # The manager catches CircuitBreakerError and returns [] or logs warning
    
    # Reset mock to ensure we don't call it if blocked
    mock_connector.get_campaigns.reset_mock()
    
    print("Executing call 6 (Should be blocked)...")
    results = manager.get_campaigns(platforms=["test_platform"])
    
    # Assertions
    if breaker.current_state != "open":
        print("❌ FAILURE: Breaker did not open!")
        exit(1)
        
    if mock_connector.get_campaigns.called:
        print("❌ FAILURE: Connector was called despite open circuit!")
        exit(1)
        
    if results.get("test_platform") != []:
        print(f"❌ FAILURE: Expected empty list, got {results}")
        exit(1)

    print("✅ SUCCESS: Circuit Breaker blocked the call and returned safe fallback.")

if __name__ == "__main__":
    test_manager_circuit_breaker()
