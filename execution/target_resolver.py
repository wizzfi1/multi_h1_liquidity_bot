def resolve_target(active_level, daily_map):
    """
    Returns TP price or None
    """
    if active_level.type == "SELL":
        # target nearest BUY liquidity below
        buys = sorted(daily_map["BUY"], key=lambda x: x.price, reverse=True)
        for lvl in buys:
            if lvl.price < active_level.price:
                return lvl.price

    if active_level.type == "BUY":
        # target nearest SELL liquidity above
        sells = sorted(daily_map["SELL"], key=lambda x: x.price)
        for lvl in sells:
            if lvl.price > active_level.price:
                return lvl.price

    return None
