from datetime import datetime
from typing import Optional, List
from core.failure_tracker import Failure


class LiquidityEventState:
    """
    Holds the full state of ONE liquidity event.
    """

    def __init__(self):
        self.reset_event()

    # --------------------------------------------------
    # Event lifecycle
    # --------------------------------------------------

    def reset_event(self):
        # Liquidity
        self.active_liquidity = None
        self.sweep_time: Optional[datetime] = None

        # Failures
        self.failures: List[Failure] = []

        # Structure resolution
        self.break_count = 0
        self.last_broken_level: Optional[float] = None
        self.structure_confirmed = False
        self.direction: Optional[str] = None  # "BUY" or "SELL"

        # Execution
        self.origin_candle = None
        self.probe_placed = False
        self.probe_stopped = False
        self.flip_used = False

    # --------------------------------------------------
    # Liquidity sweep
    # --------------------------------------------------

    def mark_sweep(self, level, time: datetime):
        self.active_liquidity = level
        self.sweep_time = time

        # Direction is opposite of swept liquidity
        # BUY liquidity swept → expect SELL probe
        self.direction = "SELL" if level.type == "BUY" else "BUY"

    # --------------------------------------------------
    # Failure handling
    # --------------------------------------------------

    def update_failures(self, failures: List[Failure]):
        self.failures = failures

    def has_two_failures(self) -> bool:
        return len(self.failures) == 2

    def has_post_sweep_failure(self) -> bool:
        if self.sweep_time is None:
            return False

        return any(f.time > self.sweep_time for f in self.failures)

    # --------------------------------------------------
    # Break handling
    # --------------------------------------------------

    def reset_break_progress(self):
        self.break_count = 0
        self.last_broken_level = None

    def register_break(self, level: float):
        # Reset if price breaks the wrong way
        if self.last_broken_level is not None:
            if (
                self.direction == "SELL" and level > self.last_broken_level
            ) or (
                self.direction == "BUY" and level < self.last_broken_level
            ):
                self.reset_break_progress()
                return

        self.break_count += 1
        self.last_broken_level = level

        if self.break_count >= 2:
            self.structure_confirmed = True

    # --------------------------------------------------
    # Execution markers
    # --------------------------------------------------

    def mark_probe_placed(self):
        self.probe_placed = True

    def mark_probe_stopped(self):
        self.probe_stopped = True

    def mark_flip_used(self):
        self.flip_used = True


# core/liquidity_event_state.py

class FailureConfirmed:
    @staticmethod
    def emit(direction, sweep_time, failure_time):
        print("❌ FAILURE CONFIRMED")
        print(f"Direction: {direction}")
        print(f"Swept at: {sweep_time}")
        print(f"Failed at: {failure_time}")


class OriginConfirmed:
    @staticmethod
    def emit(direction, candle):
        print("🎯 ORIGIN CONFIRMED")
        print(f"Direction: {direction}")
        print(f"Time: {candle['time']}")
        print(
            f"O:{candle['open']} H:{candle['high']} "
            f"L:{candle['low']} C:{candle['close']}"
        )


class ProbeTriggered:
    @staticmethod
    def emit(direction, origin_high, origin_low, origin_time, trigger_time):
        print("🎯 PROBE TRIGGERED")
        print(f"Direction: {direction}")
        print(f"Origin range: {origin_low} → {origin_high}")
        print(f"Origin time: {origin_time}")
        print(f"Trigger time: {trigger_time}")

class CleanupConfirmed:
    @staticmethod
    def emit(failure_direction, cleanup_time):
        print("🧹 CLEANUP CONFIRMED")
        print(f"Failure Direction: {failure_direction}")
        print(f"Cleanup Time: {cleanup_time}")

class LifecycleResolved:
    @staticmethod
    def emit(reason: str, time):
        print("🔓 LIFECYCLE RESOLVED")
        print(f"Reason: {reason}")
        print(f"Time: {time}")

class LifecycleResolved:
    _handler = None

    @staticmethod
    def emit(reason: str, time):
        print("🔓 LIFECYCLE RESOLVED")
        print(f"Reason: {reason}")
        print(f"Time: {time}")

        if LifecycleResolved._handler:
            LifecycleResolved._handler(reason, time)


class ProbeTriggered:
    _handler = None

    @staticmethod
    def emit(direction, origin_high, origin_low, origin_time, trigger_time):
        print("🎯 PROBE TRIGGERED")
        print(f"Direction: {direction}")
        print(f"Origin range: {origin_low} → {origin_high}")

        if ProbeTriggered._handler:
            ProbeTriggered._handler(
                direction,
                origin_high,
                origin_low,
                trigger_time
            )
