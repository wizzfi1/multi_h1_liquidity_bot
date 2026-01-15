from core.session_filter import in_session, get_session


class M5StructureGate:
    def __init__(self, liq_state, detector_cls, notifier):
        self.state = liq_state
        self.detector_cls = detector_cls
        self.notifier = notifier
        self.detector = None

    def on_tick(self, m5_df):
        now = m5_df.iloc[-1]["time"]

        # 🚫 Structure only allowed London / NY
        if not in_session(now):
            return

        if not self.state.swept or self.state.structure_confirmed:
            return

        # -----------------------------
        # ARM STRUCTURE (once)
        # -----------------------------
        if self.detector is None:
            self.detector = self.detector_cls(
                self.state.active_level.type
            )

            self.notifier(
                f"☀️ {get_session(now).upper()} STRUCTURE ARMED\n"
                f"Liquidity Type: {self.state.active_level.type}\n"
                f"Level: {self.state.active_level.price}\n"
                f"Sweep Session: {self.state.sweep_session}\n"
                f"Waiting for M5 double break…"
            )

        # -----------------------------
        # CHECK STRUCTURE
        # -----------------------------
        idx = len(m5_df) - 1
        payload = self.detector.update(m5_df, idx)

        if payload:
            self.state.mark_structure(payload)

            self.notifier(
                f"✅ STRUCTURE CONFIRMED\n"
                f"Direction: {payload['direction']}\n"
                f"Breaks: {payload['breaks']}\n"
                f"Sweep Session: {self.state.sweep_session}\n"
                f"Structure Session: {get_session(now)}"
            )
