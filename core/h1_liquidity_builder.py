import MetaTrader5 as mt5
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from collections import defaultdict


# =============================
# DATA MODEL (LOCAL, EXPLICIT)
# =============================
@dataclass
class LiquidityLevel:
    price: float
    type: str          # "BUY_SIDE" or "SELL_SIDE"
    timestamp: datetime
    mitigated: bool = False
    day_tag: str | None = None


class H1LiquidityBuilder:
    """
    Builds REAL H1 liquidity from the last 5 completed UTC days.

    Liquidity definition (minimum viable institutional):
    1) Prior Day High / Low
    2) Multi-touch H1 clusters (>= 2 reactions within tolerance)
    """

    CLUSTER_TOLERANCE = 0.0005   # 5 pips
    MIN_TOUCHES = 2

    def __init__(self, symbol: str, reference_date: datetime | None = None):
        self.symbol = symbol
        self.reference_date = reference_date

    def build(self):
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

        if rates is None or len(rates) < 50:
            return {"BUY_SIDE": [], "SELL_SIDE": []}

        rates = list(rates)

        liquidity = {"BUY_SIDE": [], "SELL_SIDE": []}

        # -----------------------------
        # 1️⃣ PRIOR DAY HIGH / LOW
        # -----------------------------
        by_day = defaultdict(list)

        for candle in rates:
            ts = datetime.fromtimestamp(candle["time"], tz=timezone.utc)
            by_day[ts.date()].append(candle)

        for day, candles in by_day.items():
            day_diff = (today - day).days
            if day_diff <= 0 or day_diff > 5:
                continue

            high = max(c["high"] for c in candles)
            low = min(c["low"] for c in candles)

            tag = f"D-{day_diff}"

            # Prior Day High = BUY-SIDE liquidity (upside stops)
            liquidity["BUY_SIDE"].append(
                LiquidityLevel(
                    price=float(high),
                    type="BUY_SIDE",
                    timestamp=datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc),
                    day_tag=tag,
                )
            )

            # Prior Day Low = SELL-SIDE liquidity (downside stops)
            liquidity["SELL_SIDE"].append(
                LiquidityLevel(
                    price=float(low),
                    type="SELL_SIDE",
                    timestamp=datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc),
                    day_tag=tag,
                )
            )

        # -----------------------------
        # 2️⃣ MULTI-TOUCH CLUSTERS
        # -----------------------------
        highs = []
        lows = []

        for candle in rates:
            highs.append(candle["high"])
            lows.append(candle["low"])

        def cluster_levels(prices):
            clusters = []

            for p in prices:
                found = False
                for cluster in clusters:
                    if abs(cluster[0] - p) <= self.CLUSTER_TOLERANCE:
                        cluster.append(p)
                        found = True
                        break

                if not found:
                    clusters.append([p])

            return clusters

        high_clusters = cluster_levels(highs)
        low_clusters = cluster_levels(lows)

        for cluster in high_clusters:
            if len(cluster) >= self.MIN_TOUCHES:
                price = sum(cluster) / len(cluster)
                liquidity["BUY_SIDE"].append(
                    LiquidityLevel(
                        price=float(price),
                        type="BUY_SIDE",
                        timestamp=start,
                        day_tag="CLUSTER",
                    )
                )

        for cluster in low_clusters:
            if len(cluster) >= self.MIN_TOUCHES:
                price = sum(cluster) / len(cluster)
                liquidity["SELL_SIDE"].append(
                    LiquidityLevel(
                        price=float(price),
                        type="SELL_SIDE",
                        timestamp=start,
                        day_tag="CLUSTER",
                    )
                )

        # -----------------------------
        # 3️⃣ MITIGATION CHECK
        # -----------------------------
        for candle in rates:
            candle_time = datetime.fromtimestamp(candle["time"], tz=timezone.utc)

            for lvl in liquidity["BUY_SIDE"]:
                if not lvl.mitigated and candle_time > lvl.timestamp:
                    if candle["high"] >= lvl.price:
                        lvl.mitigated = True

            for lvl in liquidity["SELL_SIDE"]:
                if not lvl.mitigated and candle_time > lvl.timestamp:
                    if candle["low"] <= lvl.price:
                        lvl.mitigated = True

        # -----------------------------
        # 4️⃣ DEDUPE (KEEP MOST RECENT)
        # -----------------------------
        def dedupe(levels):
            by_bucket = {}
            for lvl in levels:
                if lvl.mitigated:
                    continue
                key = round(lvl.price, 4)
                if key not in by_bucket or lvl.timestamp > by_bucket[key].timestamp:
                    by_bucket[key] = lvl
            return list(by_bucket.values())

        return {
            "BUY_SIDE": dedupe(liquidity["BUY_SIDE"]),
            "SELL_SIDE": dedupe(liquidity["SELL_SIDE"]),
        }
