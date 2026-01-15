# core/mt5_connector.py

import MetaTrader5 as mt5
import sys

def connect(symbol: str):
    if not mt5.initialize():
        print("❌ MT5 initialization failed")
        sys.exit(1)

    if not mt5.symbol_select(symbol, True):
        print(f"❌ Failed to select symbol: {symbol}")
        sys.exit(1)

    account = mt5.account_info()
    if account is None:
        print("❌ Failed to fetch account info")
        sys.exit(1)

    print("✅ MT5 CONNECTED")
    print(f"Account: {account.login}")
    print(f"Broker : {account.company}")
