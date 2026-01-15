import sys
import os
import time
from datetime import datetime, timezone

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import MetaTrader5 as mt5
import pandas as pd

# =============================
# CORE BOT IMPORTS (UNCHANGED)
# =============================
from config.settings import SYMBOL
from core.mt5_connector import connect
from core.session_filter import in_session, get_session
from core.news_blackout import in_news_blackout
from core.double_break_detector import DoubleBreakDetector
from core.entry_engine import EntryEngine
from core.risk_manager import RiskManager
from execution.orders import OrderExecutor
from core.event_context import EventContext
from core.notifier import send



# =============================
# MULTI-H1 LIQUIDITY IMPORTS
# =============================
from core.h1_liquidity_builder import H1LiquidityBuilder
from core.liquidity_state import LiquidityState
from core.liquidity_selector import LiquiditySelector
from core.liquidity_sweep_detector import LiquiditySweepDetector
from integration.liquidity_adapter import LiquidityAdapter
from integration.m5_structure_gate import M5StructureGate
from integration.primary_entry_adapter import PrimaryEntryAdapter


def log_state(state, tag="STATE"):
    send(
        f"🧠 {tag}\n"
        f"locked={state.locked}\n"
        f"swept={state.swept}\n"
        f"structure={state.structure_confirmed}\n"
        f"entry_placed={state.entry_placed}\n"
        f"flip_active={state.flip_active}"
    )

# =============================
# CONFIG
# =============================
ENABLE_TRADING = True   
ENABLE_FLIP = True
CHECK_INTERVAL = 10

# =============================
# INIT
# =============================
connect(SYMBOL)

entry_engine = EntryEngine(SYMBOL)
risk_manager = RiskManager(SYMBOL)
executor = OrderExecutor(SYMBOL)
event = EventContext()

send(
    "🚀 *Live Demo Trading Started — Multi H1 Liquidity*\n"
    f"Symbol: {SYMBOL}\n"
    "Risk: $3000\n"
    "Liquidity: Multi Unmitigated H1 (Previous Day)\n"
    "Flip: LIMIT | RR ≥ 5"
)

# =============================
# BUILD DAILY LIQUIDITY MAP
# =============================
builder = H1LiquidityBuilder(SYMBOL)
liquidity_map = builder.build()

send(
    f"📏 {SYMBOL} — PREVIOUS DAY LIQUIDITY\n"
    f"Highs: {[l.price for l in liquidity_map['SELL']]}\n"
    f"Lows: {[l.price for l in liquidity_map['BUY']]}"
)

liq_state = LiquidityState()
liq_selector = LiquiditySelector(liq_state)
liq_adapter = LiquidityAdapter(liq_selector, liquidity_map)
sweep_detector = LiquiditySweepDetector(liq_state, send)

structure_gate = M5StructureGate(
    liq_state,
    DoubleBreakDetector,
    send
)

primary_adapter = PrimaryEntryAdapter(
    liq_state,
    entry_engine,
    executor,
    risk_manager,
    send
)

# =============================
# HELPERS
# =============================
def last_closed_trade():
    deals = mt5.history_deals_get(
        datetime.now(timezone.utc) - pd.Timedelta(hours=12),
        datetime.now(timezone.utc),
    )
    if not deals:
        return None
    deals = [d for d in deals if d.symbol == SYMBOL]
    return sorted(deals, key=lambda d: d.time, reverse=True)[0] if deals else None

# =============================
# MAIN LOOP
# =============================
while True:
    now = datetime.now(timezone.utc)

    if not in_session(now) or in_news_blackout():
        time.sleep(CHECK_INTERVAL)
        continue

    m5 = pd.DataFrame(mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M5, 0, 300))
    if m5.empty:
        time.sleep(CHECK_INTERVAL)
        continue

    m5["time"] = pd.to_datetime(m5["time"], unit="s", utc=True)
    last = m5.iloc[-1]

    # =============================
    # LIQUIDITY SELECTION (LOCKS ONCE)
    # =============================
    mid_price = (last["high"] + last["low"]) / 2
    active_liquidity = liq_adapter.get_active_liquidity(mid_price)

    # =============================
    # SWEEP DETECTION
    # =============================
    tick = mt5.symbol_info_tick(SYMBOL)
    if tick and active_liquidity:
        sweep_detector.check(tick.bid, tick.ask)

    # =============================
    # STRUCTURE CONFIRMATION
    # =============================
    structure_gate.on_tick(m5)

    # =============================
    # PRIMARY ENTRY
    # =============================
    if ENABLE_TRADING:
        placed = primary_adapter.try_place_entry()
        if placed:
            payload = liq_state.structure_payload
            send(
                f"✅ Entry Placed\n"
                f"Type: {payload['type']}\n"
                f"Entry: {payload['entry']}\n"
                f"SL: {payload['stop_loss']}\n"
                f"TP: {payload['take_profit']}\n"
                f"RR: {payload['risk_reward']:.2f}"
            )
    # =============================
    # FLIP LOGIC (UNCHANGED)
    # =============================
    if ENABLE_FLIP and event.allow_flip:
        deal = last_closed_trade()
        if deal and deal.position_id == event.primary_ticket:
            if deal.reason == mt5.DEAL_REASON_SL and get_session(
                datetime.fromtimestamp(deal.time, timezone.utc)
            ) == event.session:

                plan = entry_engine.build_trade_plan(
                    type("Signal", (), {"direction": event.flip_direction})(),
                    event.tp_level,
                )

                rr = abs(event.tp_level - plan.entry_price) / abs(
                    plan.entry_price - plan.stop_loss
                )

                if plan.valid and rr >= 5:
                    lot = risk_manager.calculate_lot_size(
                        plan.entry_price, plan.stop_loss
                    )
                    ticket = executor.place_limit(
                        plan.direction,
                        lot,
                        plan.entry_price,
                        plan.stop_loss,
                        event.tp_level,
                    )

                    if ticket:
                        liq_state.mark_flip_active()
                        send(
                            f"🔄 Flip Executed\n"
                            f"Type: {plan.direction}\n"
                            f"Entry: {plan.entry_price}\n"
                            f"SL: {plan.stop_loss}\n"
                            f"TP: {event.tp_level}\n"
                            f"RR: {rr:.2f}"
                        )

                event.resolve()
                liq_state.unlock()

    time.sleep(CHECK_INTERVAL)
