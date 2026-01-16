import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


import pandas as pd


from datetime import timezone

from core.h1_liquidity_builder import H1LiquidityBuilder
from core.failure_tracker import FailureTracker
from core.failure_detector import FailureDetector
from core.origin_candle_locator import OriginCandleLocator
from core.flip_origin_candle_locator import FlipOriginCandleLocator
from core.liquidity_event_state import LiquidityEventState
from integration.structure_resolution_gate import StructureResolutionGate
from integration.probe_entry_adapter import ProbeEntryAdapter
from integration.flip_entry_adapter import FlipEntryAdapter


from backtest.virtual_executor import VirtualExecutor
from execution.target_resolver import TargetResolver
from core.risk_manager import RiskManager




def run_backtest(symbol, m5_df):
    # -----------------------------
    # INIT
    # -----------------------------
    h1_liquidity = H1LiquidityBuilder(symbol).build()

    state = LiquidityEventState()

    failure_tracker = FailureTracker()
    failure_detector = FailureDetector(failure_tracker)

    origin_locator = OriginCandleLocator()
    flip_origin_locator = FlipOriginCandleLocator()

    structure_gate = StructureResolutionGate(state, lambda x: None)

    risk_manager = RiskManager(symbol)
    probe_adapter = ProbeEntryAdapter(risk_manager)
    flip_adapter = FlipEntryAdapter(None, risk_manager, lambda x: None)

    executor = VirtualExecutor()
    resolver = TargetResolver(min_rr=5.0)

    # -----------------------------
    # LOOP CANDLE BY CANDLE
    # -----------------------------
    for i in range(len(m5_df)):
        candle = m5_df.iloc[i]

        # -------- LIQUIDITY SWEEP --------
        if state.active_liquidity is None:
            for lvl in h1_liquidity["SELL"]:
                if candle["high"] >= lvl.price:
                    state.mark_sweep(lvl, candle["time"])
                    break

            for lvl in h1_liquidity["BUY"]:
                if candle["low"] <= lvl.price:
                    state.mark_sweep(lvl, candle["time"])
                    break

        # -------- FAILURE DETECTION --------
        if state.active_liquidity:
            probing_sell = state.active_liquidity.type == "BUY"

            failure_detector.on_candle(
                candle=candle,
                probing_sell=probing_sell
            )

            state.update_failures(failure_tracker.get_failures())

        # -------- STRUCTURE RESOLUTION --------
        structure_gate.on_price(
            high=candle["high"],
            low=candle["low"]
        )

        # -------- ORIGIN CANDLE --------
        if state.break_count == 1 and state.origin_candle is None:
            origin = origin_locator.locate(
                m5_df=m5_df.iloc[: i + 1],
                break_index=i,
                direction=state.direction
            )
            state.origin_candle = origin

        # -------- PROBE ENTRY --------
        if (
            state.structure_confirmed
            and state.origin_candle
            and not state.probe_placed
        ):
            plan = probe_adapter.build(
                direction=state.direction,
                origin=state.origin_candle,
                failures=state.failures
            )

            if plan:
                tp = resolver.resolve(
                    plan.direction,
                    plan.entry,
                    plan.stop_loss,
                    h1_liquidity
                )

                if tp:
                    executor.place_limit(
                        plan.direction,
                        plan.entry,
                        plan.stop_loss,
                        tp,
                        candle["time"]
                    )
                    state.probe_placed = True

        # -------- POSITION UPDATE --------
        result = executor.on_candle(candle)

        # -------- FLIP --------
        if result == "SL" and not state.flip_used:
            flip_origin = flip_origin_locator.locate(
                m5_df=m5_df,
                sl_index=i,
                direction=state.direction
            )

            if flip_origin:
                tp = resolver.resolve(
                    state.direction,
                    flip_origin.open,
                    flip_origin.high if state.direction == "SELL" else flip_origin.low,
                    h1_liquidity
                )

                if tp:
                    executor.place_limit(
                        state.direction,
                        flip_origin.open,
                        flip_origin.high,
                        tp,
                        candle["time"]
                    )
                    state.flip_used = True

        # -------- RESET AFTER TP OR FLIP SL --------
        if result in ("TP", "SL") and state.flip_used:
            state.reset_event()
            failure_tracker.reset()

    return executor.history
