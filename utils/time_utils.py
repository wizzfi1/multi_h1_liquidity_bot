from datetime import datetime, timedelta, timezone

def previous_utc_day_range():
    now = datetime.now(timezone.utc)
    day = now.date() - timedelta(days=1)

    start = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)
    end = datetime.combine(day, datetime.max.time(), tzinfo=timezone.utc)

    return start, end
