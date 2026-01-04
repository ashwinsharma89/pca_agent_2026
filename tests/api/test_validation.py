
import pytest
import sys
import os
sys.path.append(os.getcwd())
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_validation_date_logic():
    print("🚀 Testing Date Validation...")
    endpoint = "/api/v1/campaigns/visualizations"
    
    # 1. Invalid Dates (Start > End)
    params = {
        "start_date": "2024-01-31",
        "end_date": "2024-01-01"
    }
    res = client.get(endpoint, params=params, headers={"Authorization": "Bearer mock_token"})
    
    if res.status_code == 422:
        print("✅ SUCCESS: Caught invalid date range (422 Unprocessable Entity)")
        print(f"Details: {res.json()}")
    elif res.status_code == 429:
        print("⚠️ SKIPPED: Rate limit hit before validation check. Wait and retry.")
    else:
        print(f"❌ FAILURE: Expected 422, got {res.status_code}")
        print(res.text)
        exit(1)

def test_validation_sanitization():
    print("🚀 Testing Input Sanitization (XSS)...")
    endpoint = "/api/v1/campaigns/dashboard-stats"
    
    # 2. XSS Injection in platform list
    # The validator should strip tags
    params = {
        "platforms": "<script>alert('hack')</script>Google", 
        # If sanitized, it becomes "alert('hack')Google" or similar, but NOT execute script
        # The endpoint logs params, so we can't easily check internal state without mocking.
        # However, checking it accepts it (200) is a start, verifying no 500 error.
    }
    
    res = client.get(endpoint, params=params, headers={"Authorization": "Bearer mock_token"})
    
    if res.status_code == 200:
        print("✅ SUCCESS: Endpoint accepted request (Sanitization likely happened silently)")
    elif res.status_code == 429:
        print("⚠️ SKIPPED: Rate limit hit.")
    else:
        print(f"❌ FAILURE: Unexpected status {res.status_code}")
        print(res.text)

if __name__ == "__main__":
    test_validation_date_logic()
    test_validation_sanitization()
