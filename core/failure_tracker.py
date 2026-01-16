from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass
class Failure:
    defensive_level: float   # ← canonical name
    time: datetime
    direction: str           # "BUY" or "SELL"


class FailureTracker:
    """
    Tracks the last TWO failures only.
    """

    def __init__(self):
        self.failures: List[Failure] = []

    def reset(self):
        self.failures = []

    def add_failure(self, failure: Failure):
        self.failures.append(failure)

        # Keep only the last two failures
        if len(self.failures) > 2:
            self.failures = self.failures[-2:]

    def get_failures(self) -> List[Failure]:
        return list(self.failures)
