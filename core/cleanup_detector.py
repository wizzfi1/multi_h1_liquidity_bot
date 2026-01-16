from datetime import datetime
from core.liquidity_event_state import CleanupConfirmed


class CleanupDetector:
    """
    Confirms cleanup AFTER a failure when structure breaks
    in the OPPOSITE direction of the failed attempt.
    """

    def __init__(self):
        self.failure_direction = None
        self.failure_time = None
        self.cleaned = False

    # ─────────────────────────────────────────────
    # EVENT: Failure confirmed
    # ─────────────────────────────────────────────
    def on_failure_confirmed(self, event):
        if self.failure_direction is not None:
            return  # already tracking a failure

        self.failure_direction = event.direction
        self.failure_time = event.failure_time

    # ─────────────────────────────────────────────
    # EVENT: Structure break
    # ─────────────────────────────────────────────
    def on_structure_break(self, direction: str, time: datetime):
        if self.failure_direction is None:
            return

        if self.cleaned:
            return

        # Cleanup occurs when structure breaks
        # in the OPPOSITE direction of the failure
        if direction != self.failure_direction:
            self.cleaned = True

            CleanupConfirmed.emit(
                failure_direction=self.failure_direction,
                failure_time=self.failure_time,
                cleanup_time=time
            )

            # lock
            self._reset()

    # ─────────────────────────────────────────────
    # INTERNAL
    # ─────────────────────────────────────────────
    def _reset(self):
        self.failure_direction = None
        self.failure_time = None
        self.cleaned = False
