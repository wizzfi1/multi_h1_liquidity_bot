from dataclasses import dataclass


@dataclass
class TradePlan:
    valid: bool
    direction: str
    entry_price: float
    stop_loss: float


class EntryEngine:
    """
    Converts structure confirmation into a limit entry plan.
    """

    def __init__(self, symbol: str):
        self.symbol = symbol

    def build_trade_plan(self, structure_payload: dict, take_profit: float) -> TradePlan:
        """
        Uses last break for entry logic.
        This mirrors the behavior of the original bot, minus PDH/PDL coupling.
        """
        direction = structure_payload["direction"]
        breaks = structure_payload["breaks"]

        if not breaks:
            return TradePlan(False, direction, 0.0, 0.0)

        last_break = breaks[-1]

        if direction == "SELL":
            entry = last_break
            sl = max(breaks)
        else:  # BUY
            entry = last_break
            sl = min(breaks)

        if entry == sl:
            return TradePlan(False, direction, entry, sl)

        return TradePlan(
            valid=True,
            direction=direction,
            entry_price=entry,
            stop_loss=sl,
        )
