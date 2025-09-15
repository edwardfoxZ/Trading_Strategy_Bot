import os
import requests
import pandas as pd
import mplfinance as mpf
from datetime import datetime, timezone


class KucoinCandles:
    OUTDIR = "kucoin_candles"
    BASE = "https://api.kucoin.com"

    INTERVAL_SECONDS = {
        "1min": 60,
        "3min": 180,
        "5min": 300,
        "15min": 900,
        "30min": 1800,
        "1hour": 3600,
        "2hour": 7200,
        "4hour": 14400,
        "6hour": 21600,
        "8hour": 28800,
        "12hour": 43200,
        "1day": 86400,
        "1week": 604800,
    }

    def __init__(self, symbol):
        self.symbol = symbol
        os.makedirs(self.OUTDIR, exist_ok=True)

    def get_klines(self, interval, days):
        if interval not in self.INTERVAL_SECONDS:
            raise ValueError(
                f"Unsupported interval {interval}. Supported: {list(self.INTERVAL_SECONDS.keys())}"
            )

        end = int(datetime.now(timezone.utc).timestamp())
        start = end - days * 86400  # number of seconds for N days

        url = f"{self.BASE}/api/v1/market/candles"
        params = {
            "symbol": self.symbol,
            "type": interval,
            "startAt": start,
            "endAt": end,
        }
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()["data"]
        data = data[::-1]  # KuCoin gives newest first, reverse for chronological

        df = pd.DataFrame(
            data, columns=["time", "open", "close", "high", "low", "volume", "turnover"]
        )
        df["time"] = pd.to_datetime(
            df["time"].astype(int), unit="s", utc=True
        ).dt.tz_localize(None)
        df = df.set_index("time")
        df = df.astype(float)
        df = df[["open", "high", "low", "close"]]
        df.columns = ["Open", "High", "Low", "Close"]

        # === Add EMA50 and EMA200 ===
        df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()
        df["EMA200"] = df["Close"].ewm(span=200, adjust=False).mean()

        return df

    def candles(self, df):
        """Return OHLC candles (with EMA columns included)"""
        return df

    def save_chart(self, df):
        """Save candlestick chart with EMA50 + EMA200"""
        save_path = os.path.join(self.OUTDIR, f"{self.symbol}_candlestick.png")

        # Define EMA lines for mplfinance
        add_plots = [
            mpf.make_addplot(df["EMA50"], color="blue", width=1.0),
            mpf.make_addplot(df["EMA200"], color="red", width=1.0),
        ]

        mpf.plot(
            df,
            type="candle",
            style="charles",
            title=f"{self.symbol} Candlestick",
            volume=False,
            tight_layout=True,
            figratio=(16, 9),
            figscale=1.5,
            addplot=add_plots,
            savefig=save_path,
        )
        return save_path
