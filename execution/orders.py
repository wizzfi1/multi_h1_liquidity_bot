# execution/orders.py

import MetaTrader5 as mt5
from typing import Optional

from config.settings import PRIMARY_MAGIC, FLIP_MAGIC, SLIPPAGE, MAX_OPEN_TRADES


class OrderExecutor:
    def __init__(self, symbol: str):
        self.symbol = symbol

    # -------------------------------------------------
    def _has_open_trade(self) -> bool:
        positions = mt5.positions_get(symbol=self.symbol)
        return positions is not None and len(positions) >= MAX_OPEN_TRADES

    # -------------------------------------------------
    def place_limit(
        self,
        direction: str,
        lot: float,
        entry: float,
        sl: float,
        tp: float,
        is_flip: bool = False,
    ) -> Optional[int]:

        if self._has_open_trade():
            print("⛔ Open trade exists. Skipping execution.")
            return None

        order_type = (
            mt5.ORDER_TYPE_SELL_LIMIT
            if direction == "SELL"
            else mt5.ORDER_TYPE_BUY_LIMIT
        )

        magic = FLIP_MAGIC if is_flip else PRIMARY_MAGIC

        request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": self.symbol,
            "volume": lot,
            "type": order_type,
            "price": entry,
            "sl": sl,
            "tp": tp,
            "deviation": SLIPPAGE,
            "magic": magic,
            "comment": "DoubleB Bot",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_RETURN,
        }

        result = mt5.order_send(request)

        if result is None:
            print("❌ order_send returned None")
            return None

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"❌ Order failed: {result.retcode}")
            return None

        print(f"✅ LIMIT ORDER ACCEPTED | Ticket: {result.order}")
        return result.order
