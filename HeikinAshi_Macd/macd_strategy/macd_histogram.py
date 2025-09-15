import pandas as pd


class MACDHistogram:
    def __init__(self, df, fast=12, slow=26, signal=9):
        """
        df: DataFrame with 'Close'
        fast, slow, signal: EMA periods for MACD
        """
        self.df = df.copy()
        self.fast = fast
        self.slow = slow
        self.signal = signal
        self.result = None

    def calculate(self):
        # Calculate EMAs
        self.df["EMA_fast"] = self.df["Close"].ewm(span=self.fast, adjust=False).mean()
        self.df["EMA_slow"] = self.df["Close"].ewm(span=self.slow, adjust=False).mean()

        # MACD line
        self.df["MACD"] = self.df["EMA_fast"] - self.df["EMA_slow"]

        # Signal line
        self.df["Signal"] = self.df["MACD"].ewm(span=self.signal, adjust=False).mean()

        # Histogram
        self.df["Histogram"] = self.df["MACD"] - self.df["Signal"]

        self.result = self.df[["EMA_fast", "EMA_slow", "MACD", "Signal", "Histogram"]]
        return self.result
