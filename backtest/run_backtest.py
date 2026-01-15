import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)



import MetaTrader5 as mt5


from datetime import datetime, timedelta, timezone
from config.settings import SYMBOL
from core.mt5_connector import connect
from backtest.data_loader import load_data
from backtest.replay_engine import ReplayEngine
from backtest.metrics import summarize


connect(SYMBOL)

end = datetime.now(timezone.utc)
start = end - timedelta(days=0)

h1, m5 = load_data(SYMBOL, start, end)

engine = ReplayEngine(SYMBOL, h1, m5)

for d in sorted(set(m5["time"].dt.date)):
    engine.run_day(d)

stats = summarize(engine.trades)
print(stats)

mt5.shutdown()
