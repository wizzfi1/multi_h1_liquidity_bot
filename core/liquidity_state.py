import datetime
from core.session_filter import get_session


class LiquidityState:
    def __init__(self):
        self.active_level = None
        self.opposing_levels = []     # ✅ ADD THIS
        self.locked = False
        self.swept = False
        self.structure_confirmed = False
        self.structure_payload = None
        self.entry_placed = False
        self.flip_active = False

        self.sweep_time = None
        self.sweep_session = None

    def lock(self, level, opposing_levels):
        self.active_level = level
        self.opposing_levels = opposing_levels  # ✅ SET HERE
        self.locked = True
        self.swept = False
        self.structure_confirmed = False
        self.structure_payload = None
        self.entry_placed = False
        self.flip_active = False

    def mark_swept(self):
        self.swept = True
        if self.active_level:
            self.active_level.mitigated = True

        self.sweep_time = datetime.datetime.utcnow()
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
