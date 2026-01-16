class TradePlan:
    def __init__(self, direction, entry_price, stop_loss, take_profit):
        self.direction = direction
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.valid = True


class EntryEngine:
    def __init__(self, symbol):
        self.symbol = symbol

    def build_trade_plan(self, direction: str, take_profit: float):
        """
        Build entry + SL from M5 structure direction.
        TP is provided externally (liquidity-based).
        """

        # -----------------------------
        # Get latest M5 structure prices
        # -----------------------------
        import MetaTrader5 as mt5
        import pandas as pd

        m5 = pd.DataFrame(
            mt5.copy_rates_from_pos(self.symbol, mt5.TIMEFRAME_M5, 0, 50)
        )

        if m5.empty or len(m5) < 3:
            return None

        last = m5.iloc[-1]

        # -----------------------------
        # Entry / SL logic (unchanged)
        # -----------------------------
        if direction == "BUY":
            entry = last["low"]
            sl = min(m5.iloc[-3]["low"], m5.iloc[-2]["low"])
        else:
            entry = last["high"]
            sl = max(m5.iloc[-3]["high"], m5.iloc[-2]["high"])

        if entry == sl:
            return None

        return TradePlan(
            direction=direction,
            entry_price=float(entry),
            stop_loss=float(sl),
            take_profit=float(take_profit),
        )
