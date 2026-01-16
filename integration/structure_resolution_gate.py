# integration/structure_resolution_gate.py

class StructureResolutionGate:
    """
    Emits raw structure break events.
    No state resolution, no levels, no failures.
    """

    def __init__(self, failure_detector, cleanup_detector):
        self.failure_detector = failure_detector
        self.cleanup_detector = cleanup_detector

        self.last_high = None
        self.last_low = None

    def on_candle(self, candle):
        high = candle["high"]
        low = candle["low"]
        time = candle["time"]

        # Initialize
        if self.last_high is None or self.last_low is None:
            self.last_high = high
            self.last_low = low
            return

        # -----------------------------
        # BUY structure break
        # -----------------------------
        if high > self.last_high:
            # Emit to Failure + Cleanup
            self.failure_detector.on_structure_break(
                direction="BUY",
                time=time
            )

            self.cleanup_detector.on_structure_break(
                direction="BUY",
                time=time
            )

            self.last_high = high

        # -----------------------------
        # SELL structure break
        # -----------------------------
        if low < self.last_low:
            # Emit to Failure + Cleanup
            self.failure_detector.on_structure_break(
                direction="SELL",
                time=time
            )

            self.cleanup_detector.on_structure_break(
                direction="SELL",
                time=time
            )

            self.last_low = low
