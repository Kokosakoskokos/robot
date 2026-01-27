#!/usr/bin/env python3
import os
import requests
import json

def test_eden_ai():
    api_key = os.getenv("EDENAI_API_KEY")
    if not api_key:
        print("❌ EDENAI_API_KEY not found in environment variables.")
        return

    print(f"✓ API key found (starts with: {api_key[:10]}...)")
    
    # Eden AI OpenAI-compatible endpoint
    url = "https://api.edenai.run/v3/openai/chat/completions"
    
    # We'll try gpt-4o-mini as a default for Eden AI
    model = "openai/gpt-4o-mini"
    
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": "Ahoj, jsi v pořádku? Odpověz krátce."}
        ],
        "temperature": 0.2
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    print(f"Testing Eden AI with model: {model}...")
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            content = data['choices'][0]['message']['content']
            print(f"✅ SUCCESS! Eden AI responded: {content}")
        else:
            print(f"❌ FAILED. HTTP {response.status_code}: {response.text}")
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    test_eden_ai()
