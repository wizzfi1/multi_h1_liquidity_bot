class VirtualPosition:
    def __init__(self, direction, entry, sl, tp, open_time):
        self.direction = direction
        self.entry = entry
        self.sl = sl
        self.tp = tp
        self.open_time = open_time
        self.close_time = None
        self.result = None  # "TP" | "SL"


class VirtualExecutor:
    def __init__(self):
        self.position = None
        self.history = []

    def place_limit(self, direction, entry, sl, tp, time):
        self.position = VirtualPosition(direction, entry, sl, tp, time)
        return True

    def on_candle(self, candle):
        if not self.position:
            return None

        high = candle["high"]
        low = candle["low"]

        pos = self.position

        if pos.direction == "SELL":
            if high >= pos.sl:
                pos.result = "SL"
            elif low <= pos.tp:
                pos.result = "TP"
        else:
            if low <= pos.sl:
                pos.result = "SL"
            elif high >= pos.tp:
                pos.result = "TP"

        if pos.result:
            pos.close_time = candle["time"]
            self.history.append(pos)
            self.position = None
            return pos.result

        return None
