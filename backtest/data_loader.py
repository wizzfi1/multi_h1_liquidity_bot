import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timezone, timedelta

def load_data(symbol, start_date, end_date):
    """
    Returns (h1_df, m5_df)
    """
    h1 = mt5.copy_rates_range(
        symbol,
        mt5.TIMEFRAME_H1,
        start_date,
        end_date
    )

    m5 = mt5.copy_rates_range(
        symbol,
        mt5.TIMEFRAME_M5,
        start_date,
        end_date
    )

    if h1 is None or m5 is None:
        raise RuntimeError("Failed to load historical data")

    h1 = pd.DataFrame(h1)
    m5 = pd.DataFrame(m5)

    h1["time"] = pd.to_datetime(h1["time"], unit="s", utc=True)
    m5["time"] = pd.to_datetime(m5["time"], unit="s", utc=True)

    return h1, m5
