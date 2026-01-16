from typing import Optional

from core.flip_origin_candle_locator import FlipOriginCandle
from execution.target_resolver import TargetResolver

PIP = 0.00010


class FlipEntryAdapter:
    """
    Executes ONE flip using last pullback candle before probe SL.
    """

    def __init__(self, executor, risk_manager, notifier):
        self.executor = executor
        self.risk_manager = risk_manager
        self.notifier = notifier
        self.used = False

    def execute(
        self,
        direction: str,
        flip_origin: FlipOriginCandle,
        liquidity_map: dict,
    ) -> Optional[int]:

        if self.used:
            return None

        # -------------------------
        # Entry = body of flip origin
        # -------------------------
        if direction == "SELL":
            entry = max(flip_origin.open, flip_origin.close)
            sl = flip_origin.high + 2 * PIP
        else:
            entry = min(flip_origin.open, flip_origin.close)
            sl = flip_origin.low - 2 * PIP

        # -------------------------
        # Resolve TP (unchanged rule)
        # -------------------------
        resolver = TargetResolver(min_rr=5.0)
        tp = resolver.resolve(
            direction,
            entry,
            sl,
            liquidity_map,
        )

        if not tp:
            self.notifier("❌ Flip cancelled — RR < 5")
            self.used = True
            return None

        # -------------------------
        # Lot sizing ($3000 risk)
        # -------------------------
        lot = self.risk_manager.calculate_lot_size(entry, sl)

        if lot <= 0:
            self.used = True
            return None

        ticket = self.executor.place_limit(
            direction,
            lot,
            entry,
            sl,
            tp,
            is_flip=True
        )

        if not ticket:
            self.used = True
            return None

        self.used = True

        self.notifier(
            f"🔁 FLIP PLACED\n"
            f"Direction: {direction}\n"
            f"Entry: {entry:.5f}\n"
            f"SL: {sl:.5f}\n"
            f"TP: {tp:.5f}\n"
            f"Risk: $3000\n"
            f"Source: Last pullback before SL"
        )

        return ticket
