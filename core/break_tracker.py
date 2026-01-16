from dataclasses import dataclass
from typing import Optional, List
import pandas as pd

from core.failure_tracker import Failure


@dataclass
class BreakEvent:
    """
    Represents a confirmed cleanup break.
    """
    break_number: int           # 1 or 2
    level: float                # level that was broken
    candle_index: int
    candle_time: pd.Timestamp


class BreakTracker:
    """
    Tracks cleanup breaks AFTER failures.

    Rules:
    - Requires TWO failures (from FailureTracker)
    - Breaks must occur IN ORDER:
        1st break = nearest failure
        2nd break = older failure
    - Breaks are confirmed ONLY on candle close
    - If price invalidates before 2nd break → RESET
    """

    def __init__(self):
        self.failures: List[Failure] = []
        self.break_count = 0
        self.active = False

    # =============================
    # LIFECYCLE
    # =============================
    def reset(self):
        self.failures.clear()
        self.break_count = 0
        self.active = False

    def arm(self, failures: List[Failure]):
        """
        Called when FailureTracker reports ready() == True.
        """
        self.reset()
        self.failures = list(failures)   # oldest → newest
        self.active = True

    # =============================
    # CORE LOGIC
    # =============================
    def update(self, df: pd.DataFrame) -> Optional[BreakEvent]:
        """
        Call on every NEW closed candle.
        """
        if not self.active or len(self.failures) != 2:
            return None

        if len(df) < 2:
            return None

        cur = df.iloc[-1]

        # -----------------------------
        # Determine expected break
        # -----------------------------
        # 1st break = MOST RECENT failure
        # 2nd break = OLDER failure
        target_failure = (
            self.failures[1] if self.break_count == 0 else self.failures[0]
        )

        # -----------------------------
        # BUY cleanup (breaking UP)
        # -----------------------------
        if target_failure.direction == "BUY":
            if cur["close"] > target_failure.level:
                self.break_count += 1
                return BreakEvent(
                    break_number=self.break_count,
                    level=target_failure.level,
                    candle_index=len(df) - 1,
                    candle_time=cur["time"],
                )

            # ❌ Invalidation: breaks down before 2nd break
            if self.break_count == 1 and cur["close"] < self.failures[1].level:
                self.reset()
                return None

        # -----------------------------
        # SELL cleanup (breaking DOWN)
        # -----------------------------
        if target_failure.direction == "SELL":
            if cur["close"] < target_failure.level:
                self.break_count += 1
                return BreakEvent(
                    break_number=self.break_count,
                    level=target_failure.level,
                    candle_index=len(df) - 1,
                    candle_time=cur["time"],
                )

            # ❌ Invalidation: breaks up before 2nd break
            if self.break_count == 1 and cur["close"] > self.failures[1].level:
                self.reset()
                return None

        return None

    # =============================
    # ACCESSORS
    # =============================
    def complete(self) -> bool:
        """
        True when both breaks are confirmed.
        """
        return self.break_count == 2
