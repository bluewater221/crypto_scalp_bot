import requests
import asyncio

async def test_search():
    symbol = "PEPE"
    print(f"🚀 Testing Dynamic Search for {symbol}...")
    
    search_url = f"https://api.coingecko.com/api/v3/search?query={symbol}"
    resp = requests.get(search_url)
    
    if resp.status_code == 200:
        data = resp.json()
        coins = data.get('coins', [])
        if coins:
            best = coins[0]
            print(f"✅ Found Coin: {best['name']} ({best['symbol']}) ID: {best['id']}")
            
            price_url = f"https://api.coingecko.com/api/v3/simple/price?ids={best['id']}&vs_currencies=usd&include_24hr_change=true"
            p_resp = requests.get(price_url)
            print(f"✅ Price API Status: {p_resp.status_code}")
            if p_resp.status_code == 200:
                print(f"✅ Data: {p_resp.json()}")
        else:
            print("❌ No coins found")
    else:
        print(f"❌ Search API Failed: {resp.status_code}")

if __name__ == "__main__":
    asyncio.run(test_search())
