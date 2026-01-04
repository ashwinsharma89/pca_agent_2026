
import os
import sys
import pandas as pd
# Add project root to path
sys.path.append(os.getcwd())

from src.query_engine.nl_to_sql import NaturalLanguageQueryEngine
from src.query_engine.validator import SQLValidator

def test_integration_security():
    print("🚀 Starting Security Integration Test...")
    
    # Initialize Engine (mock API key)
    engine = NaturalLanguageQueryEngine(api_key="mock-key")
    
    # Load dummy data
    df = pd.DataFrame({'id': [1], 'spend': [100]})
    engine.load_data(df, "campaigns")
    
    # Test 1: Valid Query -> Should Pass
    try:
        print("Test 1: Executing VALID query...")
        engine.execute_query("SELECT * FROM campaigns")
        print("✅ Valid query passed.")
    except Exception as e:
        print(f"❌ Valid query failed: {e}")
        exit(1)

    # Test 2: Malicious Query -> Should FAIL
    try:
        print("Test 2: Executing MALICIOUS query (DROP TABLE)...")
        engine.execute_query("DROP TABLE campaigns")
        print("❌ Security Breach! DROP TABLE was executed.")
        exit(1)
    except ValueError as e:
        if "Security Block" in str(e):
            print(f"✅ Security System Active! Blocked execution: {e}")
        else:
            print(f"⚠️ Caught exception but not Security Block: {e}")
            exit(1)
    except Exception as e:
        print(f"❌ Unexpected exception type: {type(e)}: {e}")
        exit(1)

    print("🎉 Integration Test Passed: Security Gate is Live.")

if __name__ == "__main__":
    test_integration_security()
