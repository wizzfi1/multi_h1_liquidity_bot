import MetaTrader5 as mt5
from datetime import datetime
from dataclasses import dataclass

from core.liquidity_event_state import LifecycleResolved


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
RISK_USD = 3000          # fixed risk for now
RR_RATIO = 3.0           # risk : reward
SL_BUFFER_PIPS = 2       # buffer beyond origin
PIP = 0.0001             # EURUSD


@dataclass
class FlipContext:
    direction: str
    origin_high: float
    origin_low: float
    trigger_time: datetime


class FlipExecutor:
    """
    Executes the flip trade on MT5.
    Pure execution layer.
    """

    def __init__(self, symbol: str):
        self.symbol = symbol

    # ─────────────────────────────────────────────
    # EVENT: Probe triggered
    # ─────────────────────────────────────────────
    def on_probe_triggered(self, event):
        ctx = FlipContext(
            direction=event.direction,
            origin_high=event.origin_high,
            origin_low=event.origin_low,
            trigger_time=event.trigger_time
        )

        self._execute(ctx)

    # ─────────────────────────────────────────────
    # EXECUTION
    # ─────────────────────────────────────────────
    def _execute(self, ctx: FlipContext):
        tick = mt5.symbol_info_tick(self.symbol)
        if not tick:
            return

        if ctx.direction == "BUY":
            entry = tick.ask
            stop_loss = ctx.origin_low - SL_BUFFER_PIPS * PIP
            risk_per_lot = abs(entry - stop_loss)
            take_profit = entry + RR_RATIO * risk_per_lot
            order_type = mt5.ORDER_TYPE_BUY
        else:
            entry = tick.bid
            stop_loss = ctx.origin_high + SL_BUFFER_PIPS * PIP
            risk_per_lot = abs(stop_loss - entry)
            take_profit = entry - RR_RATIO * risk_per_lot
            order_type = mt5.ORDER_TYPE_SELL

        volume = self._calculate_lot_size(risk_per_lot)

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": volume,
            "type": order_type,
            "price": entry,
            "sl": stop_loss,
            "tp": take_profit,
            "deviation": 20,
            "magic": 20260116,
            "comment": "MultiH1 Flip",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)

        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            print("🟢 FLIP EXECUTED")
            print(f"Ticket: {result.order}")
            print(f"Direction: {ctx.direction}")
            print(f"Entry: {entry}")
            print(f"SL: {stop_loss}")
            print(f"TP: {take_profit}")

            LifecycleResolved.emit(
                reason="FLIP_EXECUTED",
                time=datetime.utcnow()
            )
        else:
            print("❌ FLIP EXECUTION FAILED")
            print(result)

            LifecycleResolved.emit(
                reason="FLIP_FAILED",
                time=datetime.utcnow()
            )

    # ─────────────────────────────────────────────
    # RISK
    # ─────────────────────────────────────────────
    def _calculate_lot_size(self, risk_per_lot):
        symbol_info = mt5.symbol_info(self.symbol)
        if not symbol_info:
            return 0.01

        tick_value = symbol_info.trade_tick_value
        lot = RISK_USD / (risk_per_lot / PIP * tick_value)

        lot = max(symbol_info.volume_min, lot)
        lot = min(symbol_info.volume_max, lot)
        return round(lot, 2)
