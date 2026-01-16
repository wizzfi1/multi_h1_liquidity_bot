import sys
import os
import time
from datetime import datetime, timezone

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import MetaTrader5 as mt5
import pandas as pd

# =============================
# CONFIG / PLUMBING
# =============================
from config.settings import SYMBOL
from core.mt5_connector import connect
from core.session_filter import get_session
from core.news_blackout import in_news_blackout
from core.notifier import send
from core.risk_manager import RiskManager
from execution.orders import OrderExecutor

# =============================
# MODEL IMPORTS (FINAL)
# =============================
from core.h1_liquidity_builder import H1LiquidityBuilder
from core.failure_tracker import FailureTracker
from core.failure_detector import FailureDetector
from core.origin_candle_locator import OriginCandleLocator
from core.flip_origin_candle_locator import FlipOriginCandleLocator
from core.liquidity_event_state import LiquidityEventState
from integration.structure_resolution_gate import StructureResolutionGate
from integration.probe_entry_adapter import ProbeEntryAdapter
from integration.flip_entry_adapter import FlipEntryAdapter

# =============================
# CONFIG
# =============================
CHECK_INTERVAL = 10
ENABLE_TRADING = True
ENABLE_FLIP = True

# =============================
# INIT
# =============================
connect(SYMBOL)

risk_manager = RiskManager(SYMBOL)
executor = OrderExecutor(SYMBOL)

send(
    "🚀 *Live Demo Trading Started — Multi H1 Liquidity*\n"
    f"Symbol: {SYMBOL}\n"
    "Risk: $3000\n"
    "Model: Failure → Cleanup → Origin → Probe → Flip"
)

# =============================
# BUILD H1 LIQUIDITY (5 DAYS)
# =============================
liq_builder = H1LiquidityBuilder(SYMBOL)
h1_liquidity = liq_builder.build()

send(
    f"📏 {SYMBOL} — 5-DAY H1 LIQUIDITY\n"
    f"Highs: {[round(l.price, 5) for l in h1_liquidity['SELL']]}\n"
    f"Lows: {[round(l.price, 5) for l in h1_liquidity['BUY']]}"
)

# =============================
# CORE STATE
# =============================
state = LiquidityEventState()

failure_tracker = FailureTracker()
failure_detector = FailureDetector(failure_tracker)

origin_locator = OriginCandleLocator()
flip_origin_locator = FlipOriginCandleLocator()

structure_gate = StructureResolutionGate(state, send)

probe_adapter = ProbeEntryAdapter(risk_manager)
flip_adapter = FlipEntryAdapter(executor, risk_manager, send)

# =============================
# HELPERS
# =============================
def last_closed_deal():
    deals = mt5.history_deals_get(
        datetime.now(timezone.utc) - pd.Timedelta(hours=6),
        datetime.now(timezone.utc),
    )
    if not deals:
        return None
    deals = [d for d in deals if d.symbol == SYMBOL]
    return max(deals, key=lambda d: d.time) if deals else None

# =============================
# MAIN LOOP
# =============================
while True:
    now = datetime.now(timezone.utc)

    if in_news_blackout():
        time.sleep(CHECK_INTERVAL)
        continue

    # -----------------------------
    # LOAD M5 DATA
    # -----------------------------
    m5 = pd.DataFrame(
        mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M5, 0, 300)
    )

    if m5.empty:
        time.sleep(CHECK_INTERVAL)
        continue

    m5["time"] = pd.to_datetime(m5["time"], unit="s", utc=True)
    last = m5.iloc[-1]

    # -----------------------------
    # LIQUIDITY SWEEP (ONE LEVEL ONLY)
    # -----------------------------
    if state.active_liquidity is None:
        tick = mt5.symbol_info_tick(SYMBOL)
        if tick:
            # BUY liquidity (price sweeps down)
            buy_lvls = sorted(h1_liquidity["BUY"], key=lambda x: x.price, reverse=True)
            for lvl in buy_lvls:
                if tick.bid <= lvl.price:
                    state.mark_sweep(lvl, last["time"])
                    send(
                        f"🌙 LIQUIDITY SWEPT\n"
                        f"Type: BUY\n"
                        f"Level: {lvl.price:.5f}\n"
                        f"Session: {get_session(last['time'])}"
                    )
                    break

            # SELL liquidity (price sweeps up)
            sell_lvls = sorted(h1_liquidity["SELL"], key=lambda x: x.price)
            for lvl in sell_lvls:
                if tick.ask >= lvl.price:
                    state.mark_sweep(lvl, last["time"])
                    send(
                        f"🌙 LIQUIDITY SWEPT\n"
                        f"Type: SELL\n"
                        f"Level: {lvl.price:.5f}\n"
                        f"Session: {get_session(last['time'])}"
                    )
                    break

    # -----------------------------
    # FAILURE DETECTION
    # -----------------------------
    if state.active_liquidity:
        probing_sell = state.active_liquidity.type == "BUY"

        failure_detector.on_candle(
            candle=last,
            probing_sell=probing_sell
        )

        state.update_failures(failure_tracker.get_failures())

    # -----------------------------
    # STRUCTURE RESOLUTION
    # -----------------------------
    structure_gate.on_price(
        high=last["high"],
        low=last["low"]
    )

    # -----------------------------
    # ORIGIN CANDLE (AFTER 1ST BREAK)
    # -----------------------------
    if state.break_count == 1 and state.origin_candle is None:
        origin = origin_locator.locate(
            m5_df=m5,
            break_index=len(m5) - 1,
            direction=state.direction
        )

        if origin:
            state.origin_candle = origin
            send(
                f"🧠 ORIGIN CANDLE SET\n"
                f"Time: {origin.time}\n"
                f"Open: {origin.open:.5f}\n"
                f"High: {origin.high:.5f}\n"
                f"Low: {origin.low:.5f}"
            )

    # -----------------------------
    # PROBE ENTRY
    # -----------------------------
    if (
        ENABLE_TRADING
        and state.structure_confirmed
        and state.origin_candle
        and not state.probe_placed
    ):
        probe_plan = probe_adapter.build(
            direction=state.direction,
            origin=state.origin_candle,
            failures=state.failures,
        )

        if probe_plan and probe_plan.valid:
            from execution.target_resolver import TargetResolver

            resolver = TargetResolver(min_rr=5.0)
            tp = resolver.resolve(
                direction=probe_plan.direction,
                entry=probe_plan.entry,
                stop_loss=probe_plan.stop_loss,
                liquidity_map=h1_liquidity,
            )

            if not tp:
                send("❌ PROBE CANCELLED — RR < 5")
                state.resolve()
            else:
                lot = risk_manager.calculate_lot_size(
                    probe_plan.entry,
                    probe_plan.stop_loss
                )

                ticket = executor.place_limit(
                    probe_plan.direction,
                    lot,
                    probe_plan.entry,
                    probe_plan.stop_loss,
                    tp,
                )

                if ticket:
                    state.mark_probe_placed(ticket=ticket, sl=probe_plan.stop_loss)

                    send(
                        f"🎯 PROBE PLACED\n"
                        f"Direction: {probe_plan.direction}\n"
                        f"Entry: {probe_plan.entry:.5f}\n"
                        f"SL: {probe_plan.stop_loss:.5f}\n"
                        f"TP: {tp:.5f}\n"
                        f"Risk: $3000\n"
                        f"SL Source: {probe_plan.sl_source.upper()}"
                    )

    # -----------------------------
    # PROBE SL DETECTION
    # -----------------------------
    if state.probe_placed and not state.probe_stopped:
        deal = last_closed_deal()

        if (
            deal
            and deal.reason == mt5.DEAL_REASON_SL
            and deal.position_id == state.probe_ticket
        ):
            state.mark_probe_stopped()

            send(
                "❌ PROBE STOPPED\n"
                f"Ticket: {deal.position_id}\n"
                f"Time: {datetime.fromtimestamp(deal.time, timezone.utc)}"
            )

    # -----------------------------
    # FLIP ENTRY
    # -----------------------------
    if ENABLE_FLIP and state.probe_stopped and not state.flip_used:
        deal = last_closed_deal()

        if deal and deal.reason == mt5.DEAL_REASON_SL:
            sl_time = datetime.fromtimestamp(deal.time, timezone.utc)
            sl_idx = m5.index[m5["time"] >= sl_time]

            if not sl_idx.empty:
                flip_origin = flip_origin_locator.locate(
                    m5_df=m5,
                    sl_index=sl_idx[0],
                    direction=state.direction
                )

                if flip_origin:
                    ticket = flip_adapter.execute(
                        direction=state.direction,
                        flip_origin=flip_origin,
                        liquidity_map=h1_liquidity
                    )

                    if ticket:
                        state.mark_flip_used()

    time.sleep(CHECK_INTERVAL)
