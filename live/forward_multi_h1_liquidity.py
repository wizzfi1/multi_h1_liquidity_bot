import sys
import os
import time
from datetime import datetime, timezone

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import MetaTrader5 as mt5
import pandas as pd

from config.settings import SYMBOL
from core.mt5_connector import connect
from core.news_blackout import in_news_blackout
from core.notifier import send

from core.persistence import load_state, save_state

# ─────────────────────────────────────────────
# CORE ENGINE IMPORTS
# ─────────────────────────────────────────────
from core.h1_liquidity_builder import H1LiquidityBuilder, LiquidityLevel
from core.failure_detector import FailureDetector
from core.cleanup_detector import CleanupDetector
from core.origin_candle_locator import OriginLocator
from core.entry_engine import EntryEngine
from core.flip_executor import FlipExecutor

from integration.structure_resolution_gate import StructureResolutionGate
from core.liquidity_event_state import LifecycleResolved, ProbeTriggered

from datetime import time as dtime

NY_CLOSE_UTC = dtime(hour=21, minute=0)  # 21:00 UTC

def is_trading_session(now_utc):
    return dtime(8, 0) <= now_utc.time() < dtime(21, 0)


# ─────────────────────────────────────────────
# SESSION HELPERS
# ─────────────────────────────────────────────
def is_trading_session(now_utc):
    """
    Only trade London + New York.
    Asia is explicitly excluded.
    """
    return dtime(8, 0) <= now_utc.time() < dtime(21, 0)


# ─────────────────────────────────────────────
# INIT
# ─────────────────────────────────────────────
connect(SYMBOL)

send(
    "🚀 Live Demo — Multi-H1 Liquidity (Event-Driven)\n"
    f"Symbol: {SYMBOL}\n"
    "Model: Sweep → Failure → Cleanup → Origin → Probe → Flip"
)

# ─────────────────────────────────────────────
# LOAD OR BUILD H1 LIQUIDITY (PERSISTENT)
# ─────────────────────────────────────────────
persisted, active_lifecycle = load_state()

if persisted:
    send("♻️ Restoring persisted state")

    h1_liquidity = {"BUY": [], "SELL": []}

    for side, levels in persisted["liquidity"].items():
        for raw in levels:
            h1_liquidity[side].append(
                LiquidityLevel(
                    price=raw["price"],
                    type=raw["type"],
                    timestamp=datetime.fromisoformat(raw["timestamp"]),
                    mitigated=raw["mitigated"],
                    day_tag=raw["day_tag"],
                )
            )
else:
    liq_builder = H1LiquidityBuilder(SYMBOL)
    h1_liquidity = liq_builder.build()
    active_lifecycle = False
    save_state(h1_liquidity, active_lifecycle)

# ─────────────────────────────────────────────
# ENGINE COMPONENTS
# ─────────────────────────────────────────────
failure_detector = FailureDetector()
cleanup_detector = CleanupDetector()
origin_locator = OriginLocator()
probe_engine = EntryEngine()
flip_executor = FlipExecutor(SYMBOL)

structure_gate = StructureResolutionGate(
    failure_detector=failure_detector,
    cleanup_detector=cleanup_detector
)

# ─────────────────────────────────────────────
# EVENT WIRING
# ─────────────────────────────────────────────
ProbeTriggered._handler = flip_executor.on_probe_triggered


# ─────────────────────────────────────────────
# LIFECYCLE RESOLUTION HANDLER (PERSISTENT)
# ─────────────────────────────────────────────
def handle_lifecycle_resolved(reason, time):
    global active_lifecycle
    active_lifecycle = False

    save_state(h1_liquidity, active_lifecycle)

    send(
        "🔓 LIFECYCLE RESOLVED\n"
        f"Reason: {reason}\n"
        f"Time: {time}"
    )


LifecycleResolved._handler = handle_lifecycle_resolved


# ─────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────
CHECK_INTERVAL = 10

while True:
    if in_news_blackout():
        time.sleep(CHECK_INTERVAL)
        continue

    # -----------------------------
    # LOAD M5 DATA
    # -----------------------------
    m5 = pd.DataFrame(
        mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M5, 0, 5)
    )

    if m5.empty:
        time.sleep(CHECK_INTERVAL)
        continue

    m5["time"] = pd.to_datetime(m5["time"], unit="s", utc=True)
    candle = m5.iloc[-1]

    tick = mt5.symbol_info_tick(SYMBOL)
    if not tick:
        time.sleep(CHECK_INTERVAL)
        continue

    # --------------------------------------------------
    # NEW YORK CLOSE — FORCE LIFECYCLE RESOLUTION
    # --------------------------------------------------
    now = datetime.now(timezone.utc)

    if active_lifecycle and now.time() >= NY_CLOSE_UTC:
        from core.liquidity_event_state import LifecycleResolved

        LifecycleResolved.emit(
            reason="NY_SESSION_END",
            time=now
        )

        active_lifecycle = False

        # Persist state immediately
        save_state(
            active_lifecycle=active_lifecycle,
            h1_liquidity=h1_liquidity
        )

        send(
            "⏱️ NY SESSION CLOSED\n"
            "Lifecycle auto-resolved\n"
            "Engine unlocked for next London session"
        )

        time.sleep(CHECK_INTERVAL)
        continue

    # -----------------------------
    # LIQUIDITY SWEEP (GLOBAL + PERSISTENT)
    # -----------------------------
    if not active_lifecycle:

        # BUY liquidity
        for lvl in h1_liquidity["BUY"]:
            if lvl.mitigated:
                continue

            if tick.bid <= lvl.price:
                lvl.mitigated = True
                active_lifecycle = True

                save_state(h1_liquidity, active_lifecycle)

                failure_detector.on_liquidity_swept(
                    direction="BUY",
                    time=candle["time"]
                )

                send(f"🌙 BUY liquidity swept @ {lvl.price}")
                break

        # SELL liquidity
        for lvl in h1_liquidity["SELL"]:
            if lvl.mitigated:
                continue

            if tick.ask >= lvl.price:
                lvl.mitigated = True
                active_lifecycle = True

                save_state(h1_liquidity, active_lifecycle)

                failure_detector.on_liquidity_swept(
                    direction="SELL",
                    time=candle["time"]
                )

                send(f"🌙 SELL liquidity swept @ {lvl.price}")
                break

    # -----------------------------
    # STRUCTURE → FAILURE / CLEANUP
    # -----------------------------
    structure_gate.on_candle(candle)

    # -----------------------------
    # ORIGIN & PROBE
    # -----------------------------
    origin_locator.on_candle_closed(candle)
    probe_engine.on_candle_closed(candle)

    time.sleep(CHECK_INTERVAL)
