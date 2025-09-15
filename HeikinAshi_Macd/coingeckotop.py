import requests

def get_top_100_coins():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 100,
        "page": 1,
        "sparkline": False
    }
    r = requests.get(url, params=params)
    data = r.json()
    return [coin['symbol'].upper() + "-USDT" for coin in data]
