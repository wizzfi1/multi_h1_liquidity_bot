class VirtualTrade:
    def __init__(self, direction, entry, sl, tp, is_flip):
        self.direction = direction
        self.entry = entry
        self.sl = sl
        self.tp = tp
        self.is_flip = is_flip
        self.open = True
        self.result = None  # "TP" or "SL"


class VirtualExecutor:
    def __init__(self):
        self.active_trade = None
        self.closed_trades = []

    def place_limit(self, direction, entry, sl, tp, is_flip=False):
        if self.active_trade:
            return False
        self.active_trade = VirtualTrade(direction, entry, sl, tp, is_flip)
        return True

    def on_price(self, high, low):
        if not self.active_trade:
            return None

        t = self.active_trade

        if t.direction == "BUY":
            if low <= t.sl:
                t.result = "SL"
            elif high >= t.tp:
                t.result = "TP"
        else:
            if high >= t.sl:
                t.result = "SL"
            elif low <= t.tp:
                t.result = "TP"

        if t.result:
            t.open = False
            self.closed_trades.append(t)
            self.active_trade = None
            return t.result

        return None
