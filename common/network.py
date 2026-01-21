import requests
from functools import wraps
import logging

# Setup basic logging
logger = logging.getLogger(__name__)

def apply_patch():
    """
    Monkey patch requests.Session.request to ONLY log success/fail.
    NO retries. NO proxies. NO user-agent rotation.
    """
    original_request = requests.Session.request

    @wraps(original_request)
    def patched_request(self, method, url, *args, **kwargs):
        try:
            response = original_request(self, method, url, *args, **kwargs)
            # Log success
            if response.status_code == 200:
                print(f"✅ Success: {response.url}")
            else:
                print(f"❌ Failed (Status {response.status_code}): {response.url}")
            return response
            
        except Exception as e:
            # Log failure
            params = kwargs.get('params', '')
            print(f"❌ Exception: {url} (Params: {params}) - {str(e)}")
            raise e

    # Apply the patch
    requests.Session.request = patched_request
    print("✅ Network Logging Activated: Only logging success/failure.")

if __name__ == "__main__":
    apply_patch()
    try:
        requests.get("http://httpbin.org/get")
    except:
        pass
