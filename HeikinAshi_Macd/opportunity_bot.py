import time
import pandas as pd
import requests
import json
import os
from heikin_ashi_strategy.heikin_ashi import KucoinHeikinAshi
from heikin_ashi_strategy.bolling_band import BollingerBands
from dotenv import load_dotenv

load_dotenv()

# === CONFIG ===
TIMEFRAMES = ["1hour", "30min", "15min", "5min"]
EMA_PERIOD = 20
BB_PERIOD = 200
SLEEP_SECONDS = 60
BB_THRESHOLDS = [0.0, 0.5, 1.0]  # key BB% levels to trigger alert

# === TELEGRAM CONFIG ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_IDS = list(map(int, os.getenv("TELEGRAM_CHAT_IDS").split(",")))

# Tracks last alerted candle per symbol + interval + BB level
last_alerted = {}

# === LOAD LAST ALERTED ===
if os.path.exists("last_alerted.json"):
    if os.path.getsize("last_alerted.json") > 0:
        with open("last_alerted.json") as f:
            data = json.load(f)
            last_alerted = {k: (pd.Timestamp(v[0]), v[1]) for k, v in data.items()}
    else:
        last_alerted = {}


# === FUNCTIONS ===
def save_last_alerted():
    with open("last_alerted.json", "w") as f:
        json.dump({k: [str(v[0]), v[1]] for k, v in last_alerted.items()}, f)


def send_telegram_message(bot_token, chat_ids, message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    for chat_id in chat_ids:
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        try:
            requests.post(url, data=payload, timeout=10)
        except Exception as e:
            print(f"Telegram send error: {e}")


def get_top_100_coins():
    """Get top 100 coins in USDT from CoinGecko"""
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 100,
        "page": 1,
        "sparkline": False,
    }
    r = requests.get(url, params=params, timeout=10)
    data = r.json()
    # Filter only USDT pairs
    return [coin["symbol"].upper() + "-USDT" for coin in data]


def check_shadow(candle, bullish=True):
    """Return shadow length for next candle"""
    if bullish:
        return (
            candle["Open"] - candle["Low"]
            if candle["Close"] >= candle["Open"]
            else candle["Close"] - candle["Low"]
        )
    else:
        return (
            candle["High"] - candle["Open"]
            if candle["Close"] <= candle["Open"]
            else candle["High"] - candle["Close"]
        )


def check_bb_threshold(bb_pct):
    """Check if BB% is breaking key levels"""
    for t in BB_THRESHOLDS:
        if abs(bb_pct - t) <= 0.02:  # small tolerance
            return True, t
    return False, None


# === MAIN BOT ===
def opportunity_finder_bot():
    top_coins = get_top_100_coins()
    print(f"Monitoring top 100 USDT coins: {len(top_coins)} coins")

    while True:
        for symbol in top_coins:
            try:
                kha = KucoinHeikinAshi(symbol)
                for interval in TIMEFRAMES:
                    max_period = max(EMA_PERIOD, BB_PERIOD)
                    seconds_per_candle = KucoinHeikinAshi.INTERVAL_SECONDS[interval]
                    required_candles = max_period + 50
                    days_needed = (required_candles * seconds_per_candle) // 86400 + 1

                    df = kha.get_klines(interval, days_needed)
                    ha_df = kha.heikin_ashi(df)
                    ha_df["EMA20"] = (
                        ha_df["Low"].ewm(span=EMA_PERIOD, adjust=False).mean()
                    )

                    # Bollinger Bands
                    bb = BollingerBands(ha_df, BB_PERIOD)
                    bb.calculate()
                    ha_df = ha_df.join(bb.result)

                    # Only check the last candle per interval to avoid duplicate alerts
                    i = (
                        len(ha_df) - 2
                    )  # check second-to-last candle (last one may be incomplete)
                    current = ha_df.iloc[i]
                    next_candle = ha_df.iloc[i + 1]
                    bb_pct = current["BB%"]
                    if pd.isna(bb_pct):
                        continue

                    bb_break, bb_level = check_bb_threshold(bb_pct)
                    if not bb_break:
                        continue

                    key = f"{symbol}_{interval}"

                    # Skip if already alerted
                    if last_alerted.get(key) == bb_level:
                        continue

                    # === Bullish EMA hit inside body ===
                    if (
                        current["Close"] > current["Open"]
                        and current["Open"] <= current["EMA20"] <= current["Close"]
                    ):
                        if check_shadow(next_candle, bullish=True) == 0:
                            message = f"*{symbol}* [{interval}] ✅ BULLISH opportunity!\nEMA hit body | BB%={bb_pct:.2f} (~{bb_level})\nTime: {ha_df.index[i]}"
                            print(message)
                            send_telegram_message(
                                TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_IDS, message
                            )
                            last_alerted[key] = bb_level
                            save_last_alerted()

                    # === Bearish EMA hit inside body ===
                    if (
                        current["Close"] < current["Open"]
                        and current["Close"] <= current["EMA20"] <= current["Open"]
                    ):
                        if check_shadow(next_candle, bullish=False) == 0:
                            message = f"*{symbol}* [{interval}] ❌ BEARISH opportunity!\nEMA hit body | BB%={bb_pct:.2f} (~{bb_level})\nTime: {ha_df.index[i]}"
                            print(message)
                            send_telegram_message(
                                TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_IDS, message
                            )
                            last_alerted[key] = bb_level
                            save_last_alerted()

            except Exception as e:
                pass  # skip coins causing errors to speed up the bot

        time.sleep(SLEEP_SECONDS)


# === RUN BOT ===
if __name__ == "__main__":
    opportunity_finder_bot()
