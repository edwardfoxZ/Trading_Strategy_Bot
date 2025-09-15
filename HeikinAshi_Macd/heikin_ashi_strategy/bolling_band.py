import pandas as pd
import mplfinance as mpf

class BollingerBands:
    def __init__(self, df, period=200):
        self.df = df
        self.period = min(period, len(df))
        self.result = pd.DataFrame(index=df.index)

    def calculate(self):
        close = self.df["Close"]
        self.result["Middle"] = close.rolling(self.period).mean()
        std = close.rolling(self.period).std()
        self.result["Top"] = self.result["Middle"] + 2 * std
        self.result["Bottom"] = self.result["Middle"] - 2 * std
        self.result["BB%"] = (close - self.result["Bottom"]) / (self.result["Top"] - self.result["Bottom"])
        return self.result

    def get_addplot(self):
        apds = []
        for col, color in zip(["Top","Middle","Bottom"], ["red","orange","green"]):
            if self.result[col].notna().any():
                apds.append(mpf.make_addplot(self.result[col], color=color, width=1))
        return apds
