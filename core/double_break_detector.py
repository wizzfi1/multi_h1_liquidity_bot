class DoubleBreakDetector:
    """
    Confirms a double break of structure on M5.
    Direction is enforced externally (by liquidity type).
    """

    def __init__(self, direction: str):
        self.direction = direction  # "BUY" or "SELL"
        self.breaks = []
        self.confirmed = False

    def update(self, m5_df, idx: int):
        """
        Call on every new M5 close.
        Returns payload dict once double break is confirmed, else None.
        """
        if self.confirmed or idx < 2:
            return None

        prev = m5_df.iloc[idx - 1]
        curr = m5_df.iloc[idx]

        if self.direction == "SELL":
            if curr["low"] < prev["low"]:
                self.breaks.append(curr["low"])
        else:  # BUY
            if curr["high"] > prev["high"]:
                self.breaks.append(curr["high"])

        if len(self.breaks) >= 2:
            self.confirmed = True
            return {
                "direction": self.direction,
                "breaks": self.breaks.copy(),
                "index": idx,
            }

        return None
