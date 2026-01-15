from utils.formatting import fmt


class PrimaryEntryAdapter:
    """
    Places the primary trade after structure confirmation.
    TP is derived from next opposing liquidity.
    """

    def __init__(self, liq_state, entry_engine, executor, risk_manager, notifier):
        self.state = liq_state
        self.engine = entry_engine
        self.executor = executor
        self.risk = risk_manager
        self.notifier = notifier

    def try_place_entry(self):
        if not self.state.structure_confirmed or self.state.entry_placed:
            return False

        payload = self.state.structure_payload
        active_lvl = self.state.active_level

        # -----------------------------
        # Determine TP from opposing liquidity
        # -----------------------------
        opposing_levels = self.state.opposing_levels
        if not opposing_levels:
            self.notifier("❌ No opposing liquidity for TP")
            self.state.unlock()
            return False

        take_profit = opposing_levels[0].price  # closest opposing level

        # -----------------------------
        # Build signal
        # -----------------------------
        signal = type(
            "Signal",
            (),
            {"direction": payload["direction"]}
        )()

        plan = self.engine.build_trade_plan(
            signal,
            take_profit
        )

        if not plan or not plan.valid:
            self.state.unlock()
            return False

        # -----------------------------
        # RR check
        # -----------------------------
        rr = abs(plan.take_profit - plan.entry_price) / abs(
            plan.entry_price - plan.stop_loss
        )

        if rr < 5:
            self.notifier(
                f"❌ Entry Rejected (RR < 5)\nRR: {rr:.2f}"
            )
            self.state.unlock()
            return False

        # -----------------------------
        # Lot sizing
        # -----------------------------
        lot = self.risk.calculate_lot_size(
            plan.entry_price,
            plan.stop_loss
        )

        # -----------------------------
        # Place limit order
        # -----------------------------
        ticket = self.executor.place_limit(
            plan.direction,
            lot,
            plan.entry_price,
            plan.stop_loss,
            plan.take_profit,
            is_flip=False
        )

        if not ticket:
            self.notifier("❌ Entry placement failed")
            self.state.unlock()
            return False

        # -----------------------------
        # Success
        # -----------------------------
        self.state.mark_entry()

        self.notifier(
            f"🎯 PRIMARY ENTRY PLACED\n"
            f"Direction: {plan.direction}\n"
            f"Entry: {fmt(plan.entry_price)}\n"
            f"SL: {fmt(plan.stop_loss)}\n"
            f"TP: {fmt(plan.take_profit)}\n"
            f"RR: {rr:.2f}"
        )

        return True
