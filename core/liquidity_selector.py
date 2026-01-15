class LiquiditySelector:
    def __init__(self, state):
        self.state = state

    def select(self, liquidity_map, current_price):
        # ❌ DO NOT select new liquidity during active event
        if self.state.locked:
            return self.state.active_level

        candidates = liquidity_map["BUY"] + liquidity_map["SELL"]
        if not candidates:
            return None

        chosen = min(candidates, key=lambda l: abs(l.price - current_price))
        self.state.lock(chosen)
        return chosen
