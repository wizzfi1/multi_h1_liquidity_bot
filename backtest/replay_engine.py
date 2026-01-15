from core.h1_liquidity_builder import H1LiquidityBuilder
from core.liquidity_state import LiquidityState
from core.liquidity_selector import LiquiditySelector
from core.double_break_detector import DoubleBreakDetector
from backtest.virtual_executor import VirtualExecutor
from core.session_filter import in_session
from core.entry_engine import EntryEngine


class ReplayEngine:
    def __init__(self, symbol, h1_df, m5_df):
        self.symbol = symbol
        self.h1 = h1_df
        self.m5 = m5_df
        self.executor = VirtualExecutor()
        self.trades = []

    def run_day(self, day):
        day_m5 = self.m5[self.m5["time"].dt.date == day]
        prev_h1 = self.h1[self.h1["time"].dt.date == day]

        if day_m5.empty or prev_h1.empty:
            return

        # ✅ Option A+ — build liquidity from correct historical day
        builder = H1LiquidityBuilder(self.symbol, reference_date=day_m5.iloc[0]["time"])
        liquidity = builder.build()

        state = LiquidityState()
        selector = LiquiditySelector(state)
        entry_engine = EntryEngine(self.symbol)

        detector = None

        for _, candle in day_m5.iterrows():
            now = candle["time"]
            if not in_session(now):
                continue

            # -----------------------------
            # Liquidity selection
            # -----------------------------
            mid = (candle["high"] + candle["low"]) / 2
            selector.select(liquidity, mid)

            # -----------------------------
            # Sweep detection
            # -----------------------------
            if state.locked and not state.swept:
                lvl = state.active_level

                if lvl.type == "BUY" and candle["low"] <= lvl.price:
                    state.mark_swept()
                    detector = None

                elif lvl.type == "SELL" and candle["high"] >= lvl.price:
                    state.mark_swept()
                    detector = None

            # -----------------------------
            # Structure confirmation
            # -----------------------------
            if state.swept and not state.structure_confirmed:
                if detector is None:
                    detector = DoubleBreakDetector(state.active_level.type)

                window = day_m5[day_m5["time"] <= now]
                if len(window) < 3:
                    continue

                idx = len(window) - 1
                payload = detector.update(window, idx)

                if payload:
                    state.mark_structure(payload)

            # -----------------------------
            # Primary entry
            # -----------------------------
            if state.structure_confirmed and not state.entry_placed:
                structure = state.structure_payload
                direction = structure["direction"]

                if direction == "BUY":
                    opposing = liquidity["SELL"]
                    if not opposing:
                        continue
                    take_profit = min(l.price for l in opposing)
                else:
                    opposing = liquidity["BUY"]
                    if not opposing:
                        continue
                    take_profit = max(l.price for l in opposing)

                plan = entry_engine.build_trade_plan(
                    structure,
                    take_profit
                )

                if plan and plan.valid:
                    self.executor.place_limit(
                        plan.direction,
                        plan.entry_price,
                        plan.stop_loss,
                        take_profit
                    )
                    state.mark_entry()

            # -----------------------------
            # Trade resolution
            # -----------------------------
            result = self.executor.on_price(
                candle["high"],
                candle["low"]
            )

            if result:
                self.trades.append(result)
                state.unlock()
                detector = None
