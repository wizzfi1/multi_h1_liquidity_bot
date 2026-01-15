from core.session_filter import get_session


class LiquiditySweepDetector:
    def __init__(self, liq_state, notifier):
        self.state = liq_state
        self.notifier = notifier

    def check(self, bid, ask):
        if not self.state.locked or self.state.swept:
            return

        lvl = self.state.active_level

        if lvl.type == "BUY" and bid <= lvl.price:
            self._on_sweep(lvl)

        elif lvl.type == "SELL" and ask >= lvl.price:
            self._on_sweep(lvl)

    def _on_sweep(self, level):
        self.state.mark_swept()

        self.notifier(
            f"🌙 LIQUIDITY SWEPT\n"
            f"Liquidity Type: {level.type}\n"
            f"Level: {level.price}\n"
            f"Sweep Session: {self.state.sweep_session}\n"
            f"Status: Waiting for London/NY structure"
        )
