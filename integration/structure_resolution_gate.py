# integration/structure_resolution_gate.py

from core.liquidity_event_state import LiquidityEventState
from core.failure_tracker import Failure


class StructureResolutionGate:
    """
    Confirms structure by sequentially cleaning the
    defensive levels of the TWO most recent failures.
    """

    def __init__(self, state: LiquidityEventState, notifier):
        self.state = state
        self.notifier = notifier

    # --------------------------------------------------
    # Main update
    # --------------------------------------------------

    def on_price(self, high: float, low: float):
        """
        Call on every candle / tick.
        """

        # Preconditions
        if not self.state.active_liquidity:
            return

        if not self.state.has_two_failures():
            return

        if not self.state.has_post_sweep_failure():
            return

        if self.state.structure_confirmed:
            return

        # Determine which failures we are resolving
        f1, f2 = self.state.failures

        # Nearest defensive level first
        defensive_levels = sorted(
            [f1.defensive_level, f2.defensive_level],
            key=lambda x: abs(x - ((high + low) / 2))
        )

        nearest = defensive_levels[0]
        second = defensive_levels[1]

        # Direction logic (mirror-safe)
        probing_sell = self.state.active_liquidity.type == "BUY"

        # --------------------------------------------------
        # BREAK LOGIC
        # --------------------------------------------------

        if self.state.break_count == 0:
            if probing_sell and low < nearest:
                self.state.register_break(nearest)
                self.notifier(f"🔹 1st defensive level cleaned: {nearest}")
            elif not probing_sell and high > nearest:
                self.state.register_break(nearest)
                self.notifier(f"🔹 1st defensive level cleaned: {nearest}")

        elif self.state.break_count == 1:
            # Invalidation check
            if probing_sell and high > self.state.last_broken_level:
                self.notifier("❌ Break invalidated — reset break count")
                self.state.reset_break_progress()
                return

            if not probing_sell and low < self.state.last_broken_level:
                self.notifier("❌ Break invalidated — reset break count")
                self.state.reset_break_progress()
                return

            # Second break
            if probing_sell and low < second:
                self.state.register_break(second)
                self.notifier("✅ Structure confirmed (2nd break)")

            elif not probing_sell and high > second:
                self.state.register_break(second)
                self.notifier("✅ Structure confirmed (2nd break)")
