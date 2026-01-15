from datetime import datetime, timezone
from core.session_filter import get_session


class LiquidityState:
    def __init__(self):
        self.active_level = None
        self.locked = False
        self.swept = False
        self.structure_confirmed = False
        self.structure_payload = None
        self.entry_placed = False
        self.flip_active = False

        # observability
        self.sweep_time = None
        self.sweep_session = None

    def lock(self, level):
        self.active_level = level
        self.locked = True
        self.swept = False
        self.structure_confirmed = False
        self.structure_payload = None
        self.entry_placed = False
        self.flip_active = False
        self.sweep_time = None
        self.sweep_session = None

    def mark_swept(self):
        self.swept = True
        if self.active_level:
            self.active_level.mitigated = True

        self.sweep_time = datetime.now(timezone.utc)
        self.sweep_session = get_session(self.sweep_time)

    def mark_structure(self, payload):
        self.structure_confirmed = True
        self.structure_payload = payload

    def mark_entry(self):
        self.entry_placed = True

    def mark_flip_active(self):
        self.flip_active = True

    def unlock(self):
        self.__init__()
