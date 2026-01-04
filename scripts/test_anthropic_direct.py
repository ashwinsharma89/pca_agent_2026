#!/usr/bin/env python3
"""Diagnostic: Test raw Anthropic API call."""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    print("❌ ANTHROPIC_API_KEY not found in environment")
    exit(1)

print(f"API Key (first 8 chars): {api_key[:8]}...")

url = "https://api.anthropic.com/v1/messages"
headers = {
    "x-api-key": api_key,
    "anthropic-version": "2023-06-01",
    "content-type": "application/json"
}

payload = {
    "model": "claude-3-haiku-20240307",
    "max_tokens": 100,
    "messages": [{"role": "user", "content": "Say hello in one word."}]
}

print(f"URL: {url}")
print(f"Headers: {list(headers.keys())}")
print(f"Model: {payload['model']}")

try:
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print(f"Response Body:\n{response.text}")
    
    if response.status_code == 200:
        print("\n✅ Anthropic API working!")
    else:
        print(f"\n❌ API Error: {response.status_code}")
except Exception as e:
    print(f"❌ Request failed: {e}")
