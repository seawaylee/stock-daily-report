
import os
import requests
import json
import time

# Configuration
DEFAULT_BASE_URL = "http://127.0.0.1:8045"
DEFAULT_API_KEY = "sk-055b734b4d584ecabf4a3c3b082ccfb8"
DEFAULT_MODEL = "gpt-4"  # Using standard alias which usually maps to the best model on proxies

def chat_completion(prompt, system_prompt=None, model=DEFAULT_MODEL, temperature=0.7, max_tokens=4000):
    """
    Call the LLM API (OpenAI compatible)
    """
    url = f"{DEFAULT_BASE_URL}/v1/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEFAULT_API_KEY}"
    }

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False
    }

    try:
        # print(f"🤖 Calling LLM: {url}...")
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()

        data = response.json()
        if "choices" in data and len(data["choices"]) > 0:
            content = data["choices"][0]["message"]["content"]
            return content
        else:
            print(f"⚠️ LLM Response Error: No choices found. Raw: {data}")
            return None

    except Exception as e:
        print(f"❌ LLM Request Failed: {e}")
        return None

if __name__ == "__main__":
    # Test
    print("Testing LLM Connection...")
    res = chat_completion("Hello, are you working?", system_prompt="You are a helpful assistant.")
    print(f"Response: {res}")
