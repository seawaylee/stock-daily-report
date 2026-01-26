import requests
from functools import wraps
import logging
import time
import random

# Setup basic logging
logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/115.0"
]

def apply_patch():
    """
    Monkey patch requests.Session.request to:
    1. Inject random User-Agent if missing.
    2. Auto-retry on failures (up to 3 times).
    3. Log success/fail.
    """
    original_request = requests.Session.request

    @wraps(original_request)
    def patched_request(self, method, url, *args, **kwargs):
        # 1. Inject User-Agent
        kwargs.setdefault('headers', {})
        if 'User-Agent' not in kwargs['headers']:
            kwargs['headers']['User-Agent'] = random.choice(USER_AGENTS)

        # 2. Retry Logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = original_request(self, method, url, *args, **kwargs)
                
                # Check for 200 OK
                if response.status_code == 200:
                    print(f"✅ Success: {response.url}")
                    return response
                
                # If 403/429/5xx, logic to retry? 
                # For now, just log and treat as soft fail, but if it's the last attempt...
                print(f"⚠️ Warning (Attempt {attempt+1}/{max_retries}): Status {response.status_code} for {url}")
                if attempt < max_retries - 1 and response.status_code in [403, 429, 500, 502, 503, 504]:
                    time.sleep(random.uniform(1, 3))
                    continue
                
                return response
                
            except Exception as e:
                # Log failure and retry
                params = kwargs.get('params', '')
                print(f"❌ Exception (Attempt {attempt+1}/{max_retries}): {url} - {str(e)}")
                
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(2, 5))
                    continue
                
                # Raise on final failure
                raise e

    # Apply the patch
    requests.Session.request = patched_request
    print("✅ Network Logging Activated: Auto-Retry (3x) + UA Injection enabled.")

if __name__ == "__main__":
    apply_patch()
    try:
        requests.get("http://httpbin.org/get")
    except:
        pass
