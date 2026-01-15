import MetaTrader5 as mt5
from datetime import datetime, timedelta, timezone
from core.liquidity_models import LiquidityLevel


class H1LiquidityBuilder:
    """
    Builds H1 structural liquidity from the last 5 completed UTC days (excluding today).

    Liquidity definition:
    - H1 swing highs / lows
    - Formed on D-1 ... D-5
    - Not mitigated at any point after formation
    """

    def __init__(self, symbol: str, reference_date: datetime | None = None):
        self.symbol = symbol
        self.reference_date = reference_date

    def build(self):
        # -----------------------------
        # Define date window
        # -----------------------------
        today = (
            self.reference_date.date()
            if self.reference_date
            else datetime.now(timezone.utc).date()
        )

        start_day = today - timedelta(days=5)
        start = datetime.combine(start_day, datetime.min.time(), tzinfo=timezone.utc)
        end = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)  # today excluded

        rates = mt5.copy_rates_range(
            self.symbol,
            mt5.TIMEFRAME_H1,
            start,
            end
        )

        if rates is None or len(rates) < 5:
            return {"BUY": [], "SELL": []}

        rates = list(rates)

        raw_sell: list[LiquidityLevel] = []
        raw_buy: list[LiquidityLevel] = []

        # -----------------------------
        # H1 SWING DETECTION
        # -----------------------------
        for i in range(1, len(rates) - 1):
            prev = rates[i - 1]
            cur = rates[i]
            nxt = rates[i + 1]

            candle_time = datetime.fromtimestamp(cur["time"], tz=timezone.utc)
            candle_day = candle_time.date()

            # ❌ ignore current day
            if candle_day >= today:
                continue

            # SELL-side liquidity (swing high)
            if cur["high"] > prev["high"] and cur["high"] > nxt["high"]:
                raw_sell.append(
                    LiquidityLevel(
                        price=float(cur["high"]),
                        type="SELL",
                        timestamp=candle_time
                    )
                )

            # BUY-side liquidity (swing low)
            if cur["low"] < prev["low"] and cur["low"] < nxt["low"]:
                raw_buy.append(
                    LiquidityLevel(
                        price=float(cur["low"]),
                        type="BUY",
                        timestamp=candle_time
                    )
                )

        # -----------------------------
        # MITIGATION CHECK
        # -----------------------------
        for candle in rates:
            candle_time = datetime.fromtimestamp(candle["time"], tz=timezone.utc)

            for lvl in raw_sell:
                if lvl.mitigated:
                    continue
                if candle_time > lvl.timestamp and candle["high"] >= lvl.price:
                    lvl.mitigated = True

            for lvl in raw_buy:
                if lvl.mitigated:
                    continue
                if candle_time > lvl.timestamp and candle["low"] <= lvl.price:
                    lvl.mitigated = True

        # -----------------------------
        # DEDUPLICATE (KEEP MOST RECENT)
        # -----------------------------
        def dedupe(levels):
            by_price = {}
            for lvl in levels:
                if lvl.mitigated:
                    continue
                if lvl.price not in by_price or lvl.timestamp > by_price[lvl.price].timestamp:
                    by_price[lvl.price] = lvl
            return list(by_price.values())

        return {
            "SELL": dedupe(raw_sell),
            "BUY": dedupe(raw_buy),
        }
