
import requests
import json
import os
import sys

# Set up dummy environment variables if needed
os.environ['JWT_SECRET_KEY'] = 'test_secret'
os.environ['OPENAI_API_KEY'] = 'test_key' 

BASE_URL = "http://localhost:8000/api/v1"

def test_auto_analysis():
    print("Testing /campaigns/analyze/global endpoint...")
    
    url = f"{BASE_URL}/campaigns/analyze/global"
    headers = {
        "Authorization": "Bearer test_token", # Mock auth if bypassed or handled
        "Content-Type": "application/json"
    }
    
    # Payload matching AnalysisConfig
    payload = {
        "use_rag_summary": True,
        "include_benchmarks": True,
        "analysis_depth": "standard",
        "include_recommendations": True
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("Success! Response preview:")
            print(json.dumps(response.json(), indent=2)[:500])
        else:
            print("Failed! Response text:")
            print(response.text)
            
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_auto_analysis()
