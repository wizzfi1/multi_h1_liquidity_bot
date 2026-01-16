import pandas as pd
from dataclasses import dataclass
from typing import Optional


@dataclass
class FlipOriginCandle:
    index: int
    time: pd.Timestamp
    open: float
    high: float
    low: float
    close: float


class FlipOriginCandleLocator:
    """
    Locates the LAST pullback candle before probe SL is hit.
    """

    def locate(
        self,
        m5_df: pd.DataFrame,
        sl_index: int,
        direction: str,
    ) -> Optional[FlipOriginCandle]:

        # Walk backwards from SL candle
        for i in range(sl_index - 1, 0, -1):
            candle = m5_df.iloc[i]
            prev = m5_df.iloc[i - 1]

            if direction == "SELL":
                # pullback = bullish candle
                if candle["close"] > candle["open"]:
                    return FlipOriginCandle(
                        index=i,
                        time=candle["time"],
                        open=candle["open"],
                        high=candle["high"],
                        low=candle["low"],
                        close=candle["close"],
                    )

            else:  # BUY
                # pullback = bearish candle
                if candle["close"] < candle["open"]:
                    return FlipOriginCandle(
                        index=i,
                        time=candle["time"],
                        open=candle["open"],
                        high=candle["high"],
                        low=candle["low"],
                        close=candle["close"],
                    )

        return None
