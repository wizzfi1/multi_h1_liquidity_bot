# config/settings.py

import MetaTrader5 as mt5
from datetime import time

# =========================
# SYMBOL & TIMEFRAMES
# =========================
SYMBOL = "EURUSDm"

HTF = mt5.TIMEFRAME_H1
LTF = mt5.TIMEFRAME_M5

# =========================
# RISK MANAGEMENT
# =========================
RISK_PER_TRADE = 3000
MIN_RR = 5.0
BE_RR = 4.0

MAX_OPEN_TRADES = 1
ALLOW_FLIP = True
MAX_FLIPS_PER_EVENT = 1

# =========================
# SESSIONS (UTC) — FIXED
# =========================
LONDON_SESSION = (time(7, 0), time(13, 0))
NEWYORK_SESSION = (time(13, 0), time(21, 0))

# =========================
# EXECUTION
# =========================
ORDER_TYPE = "LIMIT"
SLIPPAGE = 5
PRIMARY_MAGIC = 91001
FLIP_MAGIC = 91002

# =========================
# SAFETY
# =========================
ONE_TIME_LIQUIDITY_EVENT = True  # PDH / PDL usable once per day
