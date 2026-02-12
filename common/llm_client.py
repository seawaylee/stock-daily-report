
import os
import json

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration from .env
DEFAULT_BASE_URL = os.getenv("LLM_BASE_URL", "http://127.0.0.1:8045")
DEFAULT_API_KEY = os.getenv("LLM_API_KEY", "")
FIXED_MODEL = "gpt-5.1 low"


def _chat_completions_url(base_url):
    normalized = (base_url or "").rstrip("/")
    if normalized.endswith("/v1"):
        return f"{normalized}/chat/completions"
    return f"{normalized}/v1/chat/completions"


def _build_headers(api_key):
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _extract_content(data):
    choices = data.get("choices") or []
    if not choices:
        return None

    message = choices[0].get("message") or {}
    return message.get("content")


def _extract_stream_content(response):
    chunks = []

    for raw_line in response.iter_lines(decode_unicode=True):
        if not raw_line:
            continue

        line = raw_line.strip()
        if not line.startswith("data:"):
            continue

        payload = line[5:].strip()
        if payload == "[DONE]":
            break

        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            continue

        choices = data.get("choices") or []
        if not choices:
            continue

        delta = choices[0].get("delta") or {}
        content = delta.get("content")
        if content:
            chunks.append(content)

    return "".join(chunks).strip()


def chat_completion(prompt, system_prompt=None, model=None, temperature=0.7):
    """
    Call the LLM API (OpenAI compatible) with streaming enabled and a fixed model.
    """
    url = _chat_completions_url(DEFAULT_BASE_URL)
    headers = _build_headers((DEFAULT_API_KEY or "").strip())

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    messages.append({"role": "user", "content": prompt})

    payload = {
        "messages": messages,
        "temperature": temperature,
        "stream": True,
    }

    request_payload = dict(payload, model=FIXED_MODEL)
    try:
        print(f"🤖 Calling LLM: {FIXED_MODEL}...")
        response = requests.post(url, headers=headers, json=request_payload, timeout=120, stream=True)
        response.raise_for_status()
        content = _extract_stream_content(response)
        if not content:
            print("⚠️ LLM Response Error: No stream content found.")
            raise ValueError("No stream content in response")
        print(f"✅ {FIXED_MODEL} responded successfully")
        return content
    except Exception as error:
        print(f"❌ {FIXED_MODEL} failed: {error}")

    return None

if __name__ == "__main__":
    # Test
    print("Testing LLM Connection with Fixed Model...")
    res = chat_completion("Hello, are you working?", system_prompt="You are a helpful assistant.")
    print(f"Response: {res}")
