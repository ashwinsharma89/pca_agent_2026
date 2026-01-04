import sys
import os
sys.path.append(os.getcwd())
import time
import pybreaker
from src.connectors.connector_manager import AdConnectorManager

# Mock Connector
class MockConnector:
    def __init__(self):
        self.should_fail = False
    
    def get_campaigns(self, start_date, end_date):
        if self.should_fail:
            raise Exception("API Connection Failed")
        return ["campaign1"]

def test_circuit_breaker_logic():
    print("🚀 Testing Circuit Breaker Logic...")
    
    # 1. Setup
    # Create a fresh breaker for testing
    circuit_breaker = pybreaker.CircuitBreaker(fail_max=3, reset_timeout=1)
    connector = MockConnector()
    
    # 2. Verify Normal Operation (Closed State)
    print("1. Testing Normal Operation...")
    result = circuit_breaker.call(connector.get_campaigns, "2024-01-01", "2024-01-07")
    assert result == ["campaign1"]
    assert circuit_breaker.current_state == "closed"
    print("✅ Normal operation passed")

    # 3. Simulate Failures (Trip the Breaker)
    print("2. Simulating Failures...")
    connector.should_fail = True
    
    # Failure 1
    try:
        circuit_breaker.call(connector.get_campaigns, "start", "end")
    except Exception:
        pass
            
    # Failure 2
    try:
        circuit_breaker.call(connector.get_campaigns, "start", "end")
    except Exception:
        pass
            
    # Failure 3 (Threshold reached)
    try:
        circuit_breaker.call(connector.get_campaigns, "start", "end")
    except Exception:
        pass

    # 4. Verify Circuit is OPEN
    print(f"Current State: {circuit_breaker.current_state}")
    assert circuit_breaker.current_state == "open"
    print("✅ Circuit correctly OPENED after 3 failures")

    # 5. Verify Fail Fast (No actual call made)
    print("3. Verifying Fail Fast...")
    try:
        circuit_breaker.call(connector.get_campaigns, "start", "end")
        print("❌ FAILED: Call should have been blocked")
        exit(1)
    except pybreaker.CircuitBreakerError:
        print("✅ Call correctly blocked by breaker")
    except Exception as e:
        print(f"❌ FAILED: Wrong exception {type(e)}")
        exit(1)
    
    # 6. Verify Recovery (Half-Open)
    print("4. Testing Recovery...")
    time.sleep(2)  # Wait for reset_timeout (1s) + buffer
    
    # Set connector to succeed
    connector.should_fail = False
    
    # Next call should be allowed (Half-Open -> Closed)
    result = circuit_breaker.call(connector.get_campaigns, "2024-01-01", "2024-01-07")
    
    assert result == ["campaign1"]
    assert circuit_breaker.current_state == "closed"
    print("✅ Circuit Breaker recovered to CLOSED state")

if __name__ == "__main__":
    test_circuit_breaker_logic()
