class LiquidityAdapter:
    """
    Selects and locks a single liquidity level
    and stores opposing liquidity in state.
    """

    def __init__(self, selector, liquidity_map):
        self.selector = selector
        self.liquidity_map = liquidity_map

    def get_active_liquidity(self, mid_price):
        state = self.selector.state

        if state.locked:
            return state.active_level

        level = self.selector.select(self.liquidity_map, mid_price)
        if not level:
            return None

        # -----------------------------
        # Determine opposing liquidity
        # -----------------------------
        if level.type == "BUY":
            opposing = sorted(
                self.liquidity_map["SELL"],
                key=lambda l: l.price
            )
        else:
            opposing = sorted(
                self.liquidity_map["BUY"],
                key=lambda l: l.price,
                reverse=True
            )

        # -----------------------------
        # LOCK STATE (THIS WAS MISSING)
        # -----------------------------
        state.lock(level, opposing)

        return level
