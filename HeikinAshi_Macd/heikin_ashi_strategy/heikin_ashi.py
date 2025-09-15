import os
import requests
import pandas as pd
import mplfinance as mpf
from datetime import datetime, timezone

class KucoinHeikinAshi:
    OUTDIR = "kucoin_heikin"
    BASE = "https://api.kucoin.com"

    INTERVAL_SECONDS = {
        "1min": 60, "3min": 180, "5min": 300, "15min": 900,
        "30min": 1800, "1hour": 3600, "2hour": 7200, "4hour": 14400,
        "6hour": 21600, "8hour": 28800, "12hour": 43200,
        "1day": 86400, "1week": 604800,
    }

    def __init__(self, symbol):
        self.symbol = symbol
        os.makedirs(self.OUTDIR, exist_ok=True)

    def get_klines(self, interval, days):
        if interval not in self.INTERVAL_SECONDS:
            raise ValueError(f"Unsupported interval {interval}. Supported: {list(self.INTERVAL_SECONDS.keys())}")

        end = int(datetime.now(timezone.utc).timestamp())
        # number of seconds for the requested number of days
        start = end - days * 86400  # 1 day = 86400s
        # This gives enough candles regardless of interval

        url = f"{self.BASE}/api/v1/market/candles"
        params = {"symbol": self.symbol, "type": interval, "startAt": start, "endAt": end}
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()["data"]
        data = data[::-1]  # reverse (KuCoin gives newest first)

        df = pd.DataFrame(data, columns=["time","open","close","high","low","volume","turnover"])
        df["time"] = pd.to_datetime(df["time"].astype(int), unit="s", utc=True).dt.tz_localize(None)
        df = df.set_index("time")
        df = df.astype(float)
        df = df[["open","high","low","close"]]
        df.columns = ["Open","High","Low","Close"]
        return df


    def heikin_ashi(self, df):
        ha = pd.DataFrame(index=df.index, columns=["Open","High","Low","Close"], dtype=float)
        ha["Close"] = (df["Open"] + df["High"] + df["Low"] + df["Close"]) / 4.0
        ha_open = [(df["Open"].iloc[0] + df["Close"].iloc[0]) / 2.0]
        for i in range(1, len(df)):
            ha_open.append((ha_open[i-1] + ha["Close"].iloc[i-1]) / 2.0)
        ha["Open"] = ha_open
        ha["High"] = pd.concat([df["High"], ha["Open"], ha["Close"]], axis=1).max(axis=1)
        ha["Low"]  = pd.concat([df["Low"],  ha["Open"], ha["Close"]], axis=1).min(axis=1)
        return ha

    def save_chart(self, ha_df, bollinger=None):
        """Save Heikin-Ashi chart with EMA20 + optional Bollinger Bands + BB% subplot"""
        
        # --- EMA20 overlay ---
        ema20 = ha_df["Low"].ewm(span=20, adjust=False).mean()
        apds = [mpf.make_addplot(ema20, color="blue", width=1.2, panel=0)]
        
        # --- Bollinger Bands overlay ---
        if bollinger:
            apds.append(mpf.make_addplot(bollinger.result["Top"], color="red", width=1.0, panel=0))
            apds.append(mpf.make_addplot(bollinger.result["Middle"], color="orange", width=1.0, panel=0))
            apds.append(mpf.make_addplot(bollinger.result["Bottom"], color="green", width=1.0, panel=0))
            # BB% subplot
            apds.append(mpf.make_addplot(bollinger.result["BB%"], color="purple", panel=1, ylabel="BB%"))

        # --- Plot settings ---
        save_path = os.path.join(self.OUTDIR, f"{self.symbol}_heikin.png")
        mpf.plot(
            ha_df,
            type="candle",
            style="charles",
            title=f"{self.symbol} Heikin-Ashi + EMA20 + BB{bollinger.period if bollinger else ''}",
            addplot=apds,
            volume=False,
            tight_layout=True,
            figratio=(16,9),
            figscale=1.5,
            savefig=save_path
        )
