import requests
import json
import os
from dotenv import load_dotenv

# load_dotenv()

def test_cryptopanic_media():
    print("\n--- Testing CryptoPanic Media ---")
    # Using key from user screenshot for testing
    api_key = "c89c7f390ac3fab7edd7e30cfb3c7d10163d14c0" 
    
    url = "https://cryptopanic.com/api/v1/posts/"
    params = {
        "auth_token": api_key,
        "kind": "media", 
        "public": "true",
        "filter": "important"
    }
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        print(f"Status: {resp.status_code}")
        try:
            data = resp.json()
            if 'results' in data and data['results']:
                for item in data['results'][:2]:
                    print(f"Title: {item['title']}")
                    print(f"Link: {item['url']}")
            else:
                print("No results found or empty list.")
                print(f"Raw: {resp.text[:200]}")
        except json.JSONDecodeError:
            print("Failed to decode JSON.")
            print(f"Response Text: {resp.text[:500]}")
            
    except Exception as e:
        print(f"Error: {e}")

def test_cointelegraph_rss():
    print("\n--- Testing CoinTelegraph Price Analysis RSS ---")
    url = "https://cointelegraph.com/rss/tag/price-analysis"
    headers = {
        'User-Agent': 'Mozilla/5.0'
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            print("Success! Found RSS Feed.")
            print(f"Content Preview: {resp.text[:500]}")
        else:
            print(f"Error: {resp.status_code}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_cointelegraph_rss()

