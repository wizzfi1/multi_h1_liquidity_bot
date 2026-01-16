from dataclasses import dataclass
from typing import Optional
import pandas as pd


@dataclass
class OriginCandle:
    time: pd.Timestamp
    open: float
    high: float
    low: float
    close: float
    index: int


class OriginCandleLocator:
    """
    Finds the origin candle:
    → the first candle of the impulse leg
    that caused the FIRST cleanup break.
    """

    def locate(
        self,
        m5_df: pd.DataFrame,
        break_index: int,
        direction: str,
    ) -> Optional[OriginCandle]:

        if break_index <= 0:
            return None

        # We walk backward from the break candle
        # until we find the candle that STARTED the impulse
        i = break_index - 1

        while i > 0:
            curr = m5_df.iloc[i]
            prev = m5_df.iloc[i - 1]

            if direction == "SELL":
                # Impulse down started when a candle makes
                # a lower low than previous
                if curr["low"] < prev["low"]:
                    i -= 1
                    continue
                break

            else:  # BUY
                if curr["high"] > prev["high"]:
                    i -= 1
                    continue
                break

        c = m5_df.iloc[i]

        return OriginCandle(
            time=c["time"],
            open=float(c["open"]),
            high=float(c["high"]),
            low=float(c["low"]),
            close=float(c["close"]),
            index=i,
        )
