from dataclasses import dataclass
from typing import Optional

from core.origin_candle_locator import OriginCandle
from core.failure_tracker import Failure


PIP = 0.00010  # EURUSD


@dataclass
class ProbePlan:
    direction: str
    entry: float
    stop_loss: float
    valid: bool
    sl_source: str  # "origin" | "structure"


class ProbeEntryAdapter:
    """
    Builds the PROBE entry once structure + origin candle exist.
    """

    def __init__(self, risk_manager):
        self.risk_manager = risk_manager
        self.plan: Optional[ProbePlan] = None

    def build(
        self,
        direction: str,
        origin: OriginCandle,
        failures: list[Failure],
    ) -> Optional[ProbePlan]:

        older_failure = failures[0]

        # -------------------------
        # ENTRY (origin candle body)
        # -------------------------
        if direction == "SELL":
            entry = max(origin.open, origin.close)
        else:  # BUY
            entry = min(origin.open, origin.close)

        # -------------------------
        # SL — primary (origin)
        # -------------------------
        if direction == "SELL":
            origin_sl = origin.high + 2 * PIP
            boundary_ok = origin.high < older_failure.level
        else:
            origin_sl = origin.low - 2 * PIP
            boundary_ok = origin.low > older_failure.level

        # -------------------------
        # SL fallback (structure)
        # -------------------------
        if boundary_ok:
            stop_loss = origin_sl
            sl_source = "origin"
        else:
            stop_loss = (
                older_failure.level + 2 * PIP
                if direction == "SELL"
                else older_failure.level - 2 * PIP
            )
            sl_source = "structure"

        self.plan = ProbePlan(
            direction=direction,
            entry=entry,
            stop_loss=stop_loss,
            valid=True,
            sl_source=sl_source,
        )

        return self.plan
