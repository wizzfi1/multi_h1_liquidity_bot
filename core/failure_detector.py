from datetime import datetime
from core.failure_tracker import Failure, FailureTracker


class FailureDetector:
    """
    Detects failed BUY or SELL attempts on M5.
    """

    def __init__(self, tracker: FailureTracker):
        self.tracker = tracker

    def on_candle(self, candle, probing_sell: bool):
        """
        probing_sell = True  → looking for BUY failures
        probing_sell = False → looking for SELL failures
        """
        time = candle["time"]

        if probing_sell:
            self._detect_buy_failure(candle, time)
        else:
            self._detect_sell_failure(candle, time)

    # ----------------------------------------
    # BUY FAILURE
    # Price tries to go up → rejected → closes down
    # ----------------------------------------
    def _detect_buy_failure(self, candle, time: datetime):
        if candle["high"] > candle["open"] and candle["close"] < candle["open"]:
            self.tracker.add_failure(
                Failure(
                    defensive_level=candle["high"],
                    time=time,
                    direction="BUY",
                )
            )


    # ----------------------------------------
    # SELL FAILURE
    # Price tries to go down → rejected → closes up
    # ----------------------------------------
    def _detect_sell_failure(self, candle, time: datetime):
        if candle["low"] < candle["open"] and candle["close"] > candle["open"]:
            self.tracker.add_failure(
                Failure(
                    defensive_level=candle["low"],
                    time=time,
                    direction="SELL",
                )
            )

