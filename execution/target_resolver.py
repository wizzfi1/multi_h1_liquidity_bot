from typing import Optional


class TargetResolver:
    """
    Resolves TP using opposing liquidity and enforces RR constraint.
    """

    def __init__(self, min_rr: float = 5.0):
        self.min_rr = min_rr

    def resolve(
        self,
        direction: str,
        entry: float,
        stop_loss: float,
        liquidity_map: dict,
    ) -> Optional[float]:

        opposing = liquidity_map["BUY"] if direction == "SELL" else liquidity_map["SELL"]

        if not opposing:
            return None

        # -------------------------
        # Select nearest opposing
        # -------------------------
        if direction == "SELL":
            candidates = [l for l in opposing if l.price < entry]
            if not candidates:
                return None
            tp = max(l.price for l in candidates)

        else:  # BUY
            candidates = [l for l in opposing if l.price > entry]
            if not candidates:
                return None
            tp = min(l.price for l in candidates)

        # -------------------------
        # RR check
        # -------------------------
        risk = abs(entry - stop_loss)
        reward = abs(tp - entry)

        if risk == 0:
            return None

        rr = reward / risk

        if rr < self.min_rr:
            return None

        return tp
