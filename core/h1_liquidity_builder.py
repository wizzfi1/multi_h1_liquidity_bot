import MetaTrader5 as mt5
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass


# =============================
# DATA MODEL (LOCAL, EXPLICIT)
# =============================
@dataclass
class LiquidityLevel:
    price: float
    type: str          # "BUY" or "SELL"
    timestamp: datetime
    mitigated: bool = False
    day_tag: str | None = None  # e.g. D-1, D-2


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
        # DATE WINDOW
        # -----------------------------
        today = (
            self.reference_date.date()
            if self.reference_date
            else datetime.now(timezone.utc).date()
        )

        start_day = today - timedelta(days=5)
        start = datetime.combine(start_day, datetime.min.time(), tzinfo=timezone.utc)
        end = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)

        rates = mt5.copy_rates_range(
            self.symbol,
            mt5.TIMEFRAME_H1,
            start,
            end
        )

        if rates is None or len(rates) < 5:
            return {"BUY": [], "SELL": []}

        rates = list(rates)

        raw_buy: list[LiquidityLevel] = []
        raw_sell: list[LiquidityLevel] = []

        # -----------------------------
        # SWING DETECTION
        # -----------------------------
        for i in range(1, len(rates) - 1):
            prev = rates[i - 1]
            cur = rates[i]
            nxt = rates[i + 1]

            ts = datetime.fromtimestamp(cur["time"], tz=timezone.utc)
            day_diff = (today - ts.date()).days

            if day_diff <= 0 or day_diff > 5:
                continue

            tag = f"D-{day_diff}"

            # SELL liquidity (swing high)
            if cur["high"] > prev["high"] and cur["high"] > nxt["high"]:
                raw_sell.append(
                    LiquidityLevel(
                        price=float(cur["high"]),
                        type="SELL",
                        timestamp=ts,
                        day_tag=tag
                    )
                )

            # BUY liquidity (swing low)
            if cur["low"] < prev["low"] and cur["low"] < nxt["low"]:
                raw_buy.append(
                    LiquidityLevel(
                        price=float(cur["low"]),
                        type="BUY",
                        timestamp=ts,
                        day_tag=tag
                    )
                )

        # -----------------------------
        # MITIGATION CHECK
        # -----------------------------
        for candle in rates:
            candle_time = datetime.fromtimestamp(candle["time"], tz=timezone.utc)

            for lvl in raw_sell:
                if not lvl.mitigated and candle_time > lvl.timestamp:
                    if candle["high"] >= lvl.price:
                        lvl.mitigated = True

            for lvl in raw_buy:
                if not lvl.mitigated and candle_time > lvl.timestamp:
                    if candle["low"] <= lvl.price:
                        lvl.mitigated = True

        # -----------------------------
        # DEDUPE (KEEP MOST RECENT)
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
