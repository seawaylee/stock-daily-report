
import os
import requests
import json
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration from .env
DEFAULT_BASE_URL = os.getenv("LLM_BASE_URL", "http://127.0.0.1:8045")
DEFAULT_API_KEY = os.getenv("LLM_API_KEY", "")
DEFAULT_MODEL = os.getenv("LLM_MODEL", "gemini-3-pro-high")
FALLBACK_MODEL = os.getenv("LLM_FALLBACK_MODEL", "claude-sonnet-4-5-thinking")

def chat_completion(prompt, system_prompt=None, model=DEFAULT_MODEL, temperature=0.7, max_tokens=4000):
    """
    Call the LLM API (OpenAI compatible) with automatic fallback

    If primary model fails (503/404/timeout), automatically retry with fallback model
    Primary: gemini-3-pro-high
    Fallback: claude-sonnet-4-5-thinking
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

    # Try primary model
    try:
        print(f"🤖 Calling LLM: {model}...")
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()

        data = response.json()
        if "choices" in data and len(data["choices"]) > 0:
            content = data["choices"][0]["message"]["content"]
            print(f"✅ {model} responded successfully")
            return content
        else:
            print(f"⚠️ LLM Response Error: No choices found. Raw: {data}")
            raise Exception("No choices in response")

    except Exception as e:
        error_msg = str(e)
        print(f"❌ {model} failed: {error_msg}")

        # Check if we should try fallback
        should_fallback = (
            "503" in error_msg or
            "Service Unavailable" in error_msg or
            "404" in error_msg or
            "timeout" in error_msg.lower() or
            "connection" in error_msg.lower()
        )

        if should_fallback and FALLBACK_MODEL and model != FALLBACK_MODEL:
            print(f"🔄 Retrying with fallback model: {FALLBACK_MODEL}...")

            # Update payload with fallback model
            payload["model"] = FALLBACK_MODEL

            try:
                response = requests.post(url, headers=headers, json=payload, timeout=120)
                response.raise_for_status()

                data = response.json()
                if "choices" in data and len(data["choices"]) > 0:
                    content = data["choices"][0]["message"]["content"]
                    print(f"✅ {FALLBACK_MODEL} responded successfully (fallback)")
                    return content
                else:
                    print(f"⚠️ Fallback Response Error: No choices found")
                    return None

            except Exception as e2:
                print(f"❌ Fallback {FALLBACK_MODEL} also failed: {e2}")
                return None
        else:
            return None

if __name__ == "__main__":
    # Test
    print("Testing LLM Connection with Fallback...")
    res = chat_completion("Hello, are you working?", system_prompt="You are a helpful assistant.")
    print(f"Response: {res}")

