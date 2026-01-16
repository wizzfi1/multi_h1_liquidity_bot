from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from core.liquidity_event_state import FailureConfirmed


class Direction(Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class LiquidityAttempt:
    direction: Direction
    sweep_time: datetime
    failed: bool = False


class FailureDetector:
    """
    Declares failure ONLY on structural contradiction.
    """

    def __init__(self):
        self.attempt: LiquidityAttempt | None = None
        self.last_sweep_time: datetime | None = None

    def on_liquidity_swept(self, direction: str, time: datetime):
        if self.last_sweep_time == time:
            return
        if self.attempt is not None:
            return

        self.attempt = LiquidityAttempt(
            direction=Direction(direction),
            sweep_time=time
        )
        self.last_sweep_time = time

    def on_structure_break(self, direction: str, time: datetime):
        if not self.attempt or self.attempt.failed:
            return

        # 🔴 STRUCTURAL CONTRADICTION
        if direction != self.attempt.direction.value:
            self.attempt.failed = True

            FailureConfirmed.emit(
                direction=self.attempt.direction.value,
                sweep_time=self.attempt.sweep_time,
                failure_time=time
            )

            self.attempt = None  # lock
