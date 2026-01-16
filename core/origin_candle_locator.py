from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from core.liquidity_event_state import CleanupConfirmed, OriginConfirmed


class Direction(Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class OriginContext:
    origin_direction: Direction
    cleanup_time: datetime
    origin_candle: dict | None = None


class OriginLocator:
    """
    Locates exactly ONE origin candle AFTER cleanup.
    """

    def __init__(self):
        self.context: OriginContext | None = None

    # ─────────────────────────────────────────────
    # EVENT: Cleanup confirmed
    # ─────────────────────────────────────────────
    def on_cleanup_confirmed(self, event: CleanupConfirmed):
        if self.context is not None:
            return

        origin_direction = (
            Direction.BUY if event.failure_direction == Direction.SELL
            else Direction.SELL
        )

        self.context = OriginContext(
            origin_direction=origin_direction,
            cleanup_time=event.cleanup_time
        )

    # ─────────────────────────────────────────────
    # EVENT: Candle closed
    # ─────────────────────────────────────────────
    def on_candle_closed(self, candle):
        if not self._armed():
            return

        if candle["time"] <= self.context.cleanup_time:
            return

        if self._is_valid_origin(candle):
            self.context.origin_candle = candle
            self._emit_origin(candle)
            self.context = None  # 🔒 LOCK

    # ─────────────────────────────────────────────
    # Rules
    # ─────────────────────────────────────────────
    def _is_valid_origin(self, candle):
        if self.context.origin_direction == Direction.BUY:
            return candle["close"] > candle["open"]
        else:
            return candle["close"] < candle["open"]

    def _armed(self):
        return self.context is not None and self.context.origin_candle is None

    def _emit_origin(self, candle):
        OriginConfirmed.emit(
            direction=self.context.origin_direction.value,
            candle=candle,
            cleanup_time=self.context.cleanup_time
        )
