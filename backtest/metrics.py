def summarize(trades):
    total = len(trades)
    wins = trades.count("TP")
    losses = trades.count("SL")

    return {
        "trades": total,
        "wins": wins,
        "losses": losses,
        "winrate": wins / total if total else 0
    }
