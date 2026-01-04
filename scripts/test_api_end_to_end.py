
import requests
import json
import time

def test_analysis_api():
    url = "http://localhost:8000/api/v1/campaigns/analyze/global"
    
    payload = {
        "use_rag_summary": True,
        "include_recommendations": True,
        "analysis_depth": "standard",
        "campaign_objective": "Maximize ROAS and Scalability",
        "conversion_definition": "Purchase",
        "time_period": "Q4 2024 Validation Run",
        "enrichment_context": {
            "attribution_model": "Data-Driven"
        }
    }
    
    print(f"Sending request to {url}...")
    start_time = time.time()
    try:
        # 1. Register User (Idempotent-ish)
        # ... (keep existing auth logic) ...
        register_url = "http://localhost:8000/api/v1/users/register"
        register_payload = {
            "username": "testuser_e2e",
            "email": "testuser_e2e@example.com",
            "password": "TestPass123!",
            "role": "admin",
            "tier": "enterprise"
        }
        requests.post(register_url, json=register_payload, timeout=5)
        
        # 2. Login
        login_url = "http://localhost:8000/api/v1/auth/login"
        login_payload = {"username": "testuser_e2e", "password": "TestPass123!"}
        auth_response = requests.post(login_url, data=login_payload, timeout=10)
        if auth_response.status_code != 200:
             auth_response = requests.post(login_url, json=login_payload, timeout=10)
        
        if auth_response.status_code != 200:
            print(f"❌ Login Failed: {auth_response.status_code} {auth_response.text}")
            return
            
        token = auth_response.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.post(url, json=payload, headers=headers, timeout=120)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Analysis Successful (Time: {elapsed:.2f}s)")
            
            # Debug structure
            insights = data.get('insights', {})
            print(f"Insights type: {type(insights)}")
            if isinstance(insights, dict):
                 print(f"Insights keys: {insights.keys()}")
                 summary = insights.get('executive_summary', {})
                 print(f"Summary type: {type(summary)}")
                 if isinstance(summary, dict):
                     brief = summary.get('brief', "No Brief Found")
                     print("\n--- BRIEF SUMMARY PREVIEW ---")
                     print(brief[:500] + "...")
                     print("-----------------------------")
                 else:
                     print(f"Summary is not a dict: {summary}")
            else:
                 print(f"Insights is not a dict: {insights}")

        else:
            print(f"❌ Analysis Failed: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Request Error: {e}")

if __name__ == "__main__":
    test_analysis_api()
