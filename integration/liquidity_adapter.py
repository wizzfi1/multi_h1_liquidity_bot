class LiquidityAdapter:
    def __init__(self, selector, liquidity_map):
        self.selector = selector
        self.map = liquidity_map

    def get_active_liquidity(self, price):
        return self.selector.select(self.map, price)
