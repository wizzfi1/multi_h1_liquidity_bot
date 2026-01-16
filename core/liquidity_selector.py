class LiquiditySelector:
    """
    Chooses the closest unmitigated liquidity level
    without mutating state.
    """

    def __init__(self, state):
        self.state = state

    def select(self, liquidity_map, mid_price):
        """
        Returns the closest liquidity level to current price.
        Does NOT lock state.
        """

        if self.state.locked:
            return self.state.active_level

        candidates = (
            liquidity_map.get("BUY", [])
            + liquidity_map.get("SELL", [])
        )

        if not candidates:
            return None

        chosen = min(
            candidates,
            key=lambda l: abs(l.price - mid_price)
        )

        return chosen
