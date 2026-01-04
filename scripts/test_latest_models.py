#!/usr/bin/env python3
"""Test latest model accessibility."""

import os
import requests
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

# Test Anthropic models
anthropic_key = os.getenv("ANTHROPIC_API_KEY")
models_to_test = [
    "claude-sonnet-4-5-20250929",  # Sonnet 4.5
    "claude-sonnet-4-5",           # Sonnet 4.5 (short name)
    "claude-sonnet-4-20250514",    # Sonnet 4
    "claude-sonnet-4",             # Sonnet 4 (short name)
    "claude-3-5-sonnet-20241022",  # Claude 3.5 Sonnet (latest)
    "claude-3-5-sonnet-latest",    # Claude 3.5 Sonnet (alias)
]

print("=== Testing Anthropic Models ===")
for model in models_to_test:
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": anthropic_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    payload = {
        "model": model,
        "max_tokens": 10,
        "messages": [{"role": "user", "content": "Hi"}]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        if response.status_code == 200:
            print(f"✅ {model}: WORKS")
        else:
            error = response.json().get('error', {}).get('message', response.text[:100])
            print(f"❌ {model}: {response.status_code} - {error[:60]}")
    except Exception as e:
        print(f"❌ {model}: Error - {e}")

# Test Gemini models
print("\n=== Testing Gemini Models ===")
google_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=google_key)

gemini_models = [
    "gemini-2.5-pro",
    "gemini-2.5-pro-exp-03-25",
    "gemini-2.0-flash-exp",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
]

for model_name in gemini_models:
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Hi", generation_config={"max_output_tokens": 10})
        print(f"✅ {model_name}: WORKS")
    except Exception as e:
        print(f"❌ {model_name}: {str(e)[:60]}")
