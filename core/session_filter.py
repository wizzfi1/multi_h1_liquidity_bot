# core/session_filter.py
from datetime import datetime, timezone
from config.settings import LONDON_SESSION, NEWYORK_SESSION


def _in_session(dt: datetime, session):
    start, end = session
    t = dt.astimezone(timezone.utc).time()
    return start <= t < end


def in_session(dt: datetime) -> bool:
    return (
        _in_session(dt, LONDON_SESSION)
        or _in_session(dt, NEWYORK_SESSION)
    )


def get_session(dt: datetime):
    if _in_session(dt, LONDON_SESSION):
        return "LONDON"
    if _in_session(dt, NEWYORK_SESSION):
        return "NEWYORK"
    return None
