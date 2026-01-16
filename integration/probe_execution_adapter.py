from typing import Optional

from integration.probe_entry_adapter import ProbePlan


class ProbeExecutionAdapter:
    """
    Executes the probe LIMIT order using fixed risk.
    """

    def __init__(self, executor, risk_manager, notifier):
        self.executor = executor
        self.risk_manager = risk_manager
        self.notifier = notifier
        self.placed = False
        self.ticket: Optional[int] = None

    def execute(self, plan: ProbePlan) -> Optional[int]:
        if self.placed:
            return None

        # -------------------------
        # Lot sizing (fixed $ risk)
        # -------------------------
        lot = self.risk_manager.calculate_lot_size(
            plan.entry,
            plan.stop_loss
        )

        if lot <= 0:
            self.notifier("❌ Probe aborted — invalid lot size")
            self.placed = True
            return None

        # -------------------------
        # Place LIMIT
        # -------------------------
        ticket = self.executor.place_limit(
            plan.direction,
            lot,
            plan.entry,
            plan.stop_loss,
            None  # TP comes later
        )

        if not ticket:
            self.notifier("❌ Probe LIMIT rejected")
            self.placed = True
            return None

        self.ticket = ticket
        self.placed = True

        # -------------------------
        # Telegram log
        # -------------------------
        self.notifier(
            f"🎯 PROBE PLACED\n"
            f"Direction: {plan.direction}\n"
            f"Entry: {plan.entry:.5f}\n"
            f"SL: {plan.stop_loss:.5f}\n"
            f"Risk: $3000\n"
            f"SL Source: {plan.sl_source.upper()}"
        )

        return ticket
