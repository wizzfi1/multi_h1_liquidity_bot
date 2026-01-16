import json
import os
from datetime import datetime

STATE_DIR = "state"
STATE_FILE = os.path.join(STATE_DIR, "runtime_state.json")


def _ensure_dir():
    if not os.path.exists(STATE_DIR):
        os.makedirs(STATE_DIR)


def save_state(liquidity_levels, active_lifecycle):
    """
    Persist liquidity levels + lifecycle lock.
    """
    _ensure_dir()

    data = {
        "active_lifecycle": active_lifecycle,
        "liquidity": {
            side: [
                {
                    "price": lvl.price,
                    "type": lvl.type,
                    "timestamp": lvl.timestamp.isoformat(),
                    "mitigated": lvl.mitigated,
                    "day_tag": lvl.day_tag,
                }
                for lvl in levels
            ]
            for side, levels in liquidity_levels.items()
        },
        "saved_at": datetime.utcnow().isoformat(),
    }

    with open(STATE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def load_state():
    """
    Load persisted state.
    Returns (liquidity_data, active_lifecycle) or (None, False)
    """
    if not os.path.exists(STATE_FILE):
        return None, False

    with open(STATE_FILE, "r") as f:
        data = json.load(f)

    return data, data.get("active_lifecycle", False)
