import MetaTrader5 as mt5


class RiskManager:
    def __init__(self, symbol: str, risk_usd: float = 3000):
        self.symbol = symbol
        self.risk_usd = risk_usd
        self.info = mt5.symbol_info(symbol)

    def calculate_lot_size(self, entry: float, stop: float) -> float:
        distance = abs(entry - stop)
        if distance <= 0:
            return 0.0

        tick_value = self.info.trade_tick_value
        tick_size = self.info.trade_tick_size

        risk_per_lot = (distance / tick_size) * tick_value
        if risk_per_lot <= 0:
            return 0.0

        lots = self.risk_usd / risk_per_lot

        # Respect broker limits
        lots = max(self.info.volume_min, min(lots, self.info.volume_max))
        return round(lots, 2)
