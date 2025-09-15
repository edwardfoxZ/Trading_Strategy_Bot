from heikin_ashi_strategy.heikin_ashi import KucoinHeikinAshi
from heikin_ashi_strategy.bolling_band import BollingerBands
from macd_strategy.candle_sticks import KucoinCandles

import math

symbol = input("Symbol (e.g., BTC-USDT): ")
interval = input("Interval (1day, 1hour, 30min, 15min, 5min, etc.): ")

EMA_PERIOD = 20
BB_PERIOD = 200
MAX_PERIOD = max(EMA_PERIOD, BB_PERIOD)

kha = KucoinHeikinAshi(symbol)
kha2 = KucoinCandles(symbol)

seconds_per_candle = KucoinHeikinAshi.INTERVAL_SECONDS.get(interval, 3600)
required_candles = MAX_PERIOD + 50
days_needed = math.ceil(required_candles * seconds_per_candle / 86400)

print(f"Fetching {days_needed} days of data for EMA{EMA_PERIOD} + BB{BB_PERIOD}...")

df = kha.get_klines(interval, days_needed)
ha_df = kha.heikin_ashi(df)

bb = BollingerBands(ha_df, period=BB_PERIOD)
bb.calculate()

df2 = kha2.get_klines(interval, days_needed)
ca_df = kha2.candles(df2)

# --- Save detailed chart ---
kha.save_chart(ha_df, bollinger=bb)
kha2.save_chart(
    ca_df,
)

print(f"Saved chart: {kha.OUTDIR}/{symbol}_heikin.png")
print(f"Bollinger Band period used: {bb.period}")
print("BB% (last 5 rows):")
print(bb.result.tail())

print(f"Saved chart: {kha2.OUTDIR}/{symbol}_candles.png")
print("Standard Candlestick chart (no indicators).")
