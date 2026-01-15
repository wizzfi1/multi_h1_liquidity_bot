import sys
import os
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import MetaTrader5 as mt5

from config.settings import SYMBOL
from core.mt5_connector import connect
from core.notifier import send
from execution.orders import OrderExecutor

# =============================
# CONFIG (SAFE TEST VALUES)
# =============================
LOT_SIZE = 0.01          # very small
ENTRY_OFFSET = 0.0005   # 5 pips
SL_OFFSET = 0.0010      # 10 pips
TP_OFFSET = 0.0050      # 50 pips

# =============================
# CONNECT
# =============================
connect(SYMBOL)

send(
    f"🧪 EXECUTION SMOKE TEST STARTED\n"
    f"Symbol: {SYMBOL}\n"
    f"Lot: {LOT_SIZE}"
)

executor = OrderExecutor(SYMBOL)

tick = mt5.symbol_info_tick(SYMBOL)
if tick is None:
    send("❌ No tick data — aborting execution test")
    sys.exit(1)

# =============================
# BUILD TEST ORDER (BUY LIMIT)
# =============================
entry_price = tick.bid - ENTRY_OFFSET
stop_loss = entry_price - SL_OFFSET
take_profit = entry_price + TP_OFFSET

ticket = executor.place_limit(
    "BUY",
    LOT_SIZE,
    entry_price,
    stop_loss,
    take_profit,
    False  # is_flip
)

# =============================
# RESULT
# =============================
if ticket:
    send(
        f"✅ EXECUTION TEST PASSED\n"
        f"BUY LIMIT placed\n"
        f"Ticket: {ticket}\n"
        f"Entry: {entry_price}\n"
        f"SL: {stop_loss}\n"
        f"TP: {take_profit}"
    )
else:
    send("❌ EXECUTION TEST FAILED — order not placed")

time.sleep(5)
mt5.shutdown()
