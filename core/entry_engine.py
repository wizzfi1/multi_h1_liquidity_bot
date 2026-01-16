from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from core.liquidity_event_state import OriginConfirmed, ProbeTriggered

from core.liquidity_event_state import ProbeTriggered, LifecycleResolved


class Direction(Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class ProbeContext:
    direction: Direction
    origin_high: float
    origin_low: float
    origin_time: datetime
    armed_time: datetime
    triggered: bool = False


class EntryEngine:
    """
    ProbeEngine.
    Arms ONLY on OriginConfirmed.
    Triggers exactly once.
    """

    def __init__(self, timeout_minutes=120):
        self.context: ProbeContext | None = None
        self.timeout = timedelta(minutes=timeout_minutes)

    # ─────────────────────────────────────────────
    # EVENT: Origin confirmed
    # ─────────────────────────────────────────────
    def on_origin_confirmed(self, event: OriginConfirmed):
        if self.context is not None:
            return  # 🔒 already armed

        candle = event.candle

        self.context = ProbeContext(
            direction=Direction(event.direction),
            origin_high=candle["high"],
            origin_low=candle["low"],
            origin_time=candle["time"],
            armed_time=datetime.utcnow()
        )

    # ─────────────────────────────────────────────
    # EVENT: Candle closed (retrace only)
    # ─────────────────────────────────────────────
    def on_candle_closed(self, candle):
        if not self._armed():
            return

        # Timeout
        if datetime.utcnow() - self.context.armed_time > self.timeout:
            self._cancel("TIMEOUT")
            return

        # Retrace into origin range
        if self._inside_origin_range(candle):
            self._trigger(candle)

    # ─────────────────────────────────────────────
    # Rules
    # ─────────────────────────────────────────────
    def _inside_origin_range(self, candle):
        return (
            candle["low"] <= self.context.origin_high
            and candle["high"] >= self.context.origin_low
        )

    def _armed(self):
        return self.context is not None and not self.context.triggered

    def _trigger(self, candle):
        self.context.triggered = True

        ProbeTriggered.emit(
            direction=self.context.direction.value,
            origin_high=self.context.origin_high,
            origin_low=self.context.origin_low,
            origin_time=self.context.origin_time,
            trigger_time=candle["time"]
        )

        self.context = None  # 🔒 LOCK

    def _cancel(self, reason):
        print(f"🚫 PROBE CANCELLED — {reason}")

        LifecycleResolved.emit(
            reason=f"PROBE_{reason}",
            time=datetime.utcnow()
        )

        self.context = None
