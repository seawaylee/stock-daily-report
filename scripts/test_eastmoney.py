import requests
import time
import re
from datetime import datetime

def test_eastmoney():
    # EastMoney 7x24 API
    # Template: getlist_102_ajaxResult_{limit}_{page}_.html
    base_url = "https://newsapi.eastmoney.com/kuaixun/v1/getlist_102_ajaxResult_50_{}_.html"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    print("Testing EastMoney 7x24 Pagination...")
    
    for page in range(1, 4): # Try 3 pages
        url = base_url.format(page)
        print(f"Fetching Page {page}: {url}")
        
        try:
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                # Content is usually "var ajaxResult=...;"
                text = r.text
                # Extract JSON part
                json_str = text.split("var ajaxResult=")[1].strip().rstrip(";")
                import json
                data = json.loads(json_str)
                items = data.get('LivesList', [])
                
                if not items:
                    print("No items found.")
                    break
                    
                first_time = items[0]['showtime']
                last_time = items[-1]['showtime']
                print(f"  Items: {len(items)}")
                print(f"  Range: {first_time} -> {last_time}")
                print(f"  Sample Item: {items[0]['digest'][:30]}...")
            else:
                print(f"Error: {r.status_code}")
                
        except Exception as e:
            print(f"Exception: {e}")
            
        time.sleep(1)

if __name__ == "__main__":
    test_eastmoney()
