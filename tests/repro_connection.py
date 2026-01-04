
import requests
import json

API_URL = "http://localhost:8000/api/v1/databases/test-connection"

def test_supabase():
    payload = {
        "category": "database",
        "type": "supabase",
        "host": "db.supabase.co",
        "port": 5432,
        "database": "postgres",
        "username": "postgres",
        "password": "password"
    }
    
    try:
        print(f"Sending payload: {json.dumps(payload, indent=2)}")
        response = requests.post(API_URL, json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        response.raise_for_status()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_supabase()
