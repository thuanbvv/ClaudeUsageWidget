"""Pure text/colour formatting helpers."""
import os
from datetime import datetime, timezone


def bar(pct, width=14):
    n = max(0, min(width, round(pct / 100 * width)))
    return "█" * n + "░" * (width - n)


def status_dot(pct):
    return "🟢" if pct < 60 else "🟡" if pct < 85 else "🔴"


def until(iso):
    try:
        secs = (datetime.fromisoformat(iso) - datetime.now(timezone.utc)).total_seconds()
    except Exception:
        return "?"
    if secs <= 0:
        return "now"
    d, rem = divmod(int(secs), 86400)
    h, rem = divmod(rem, 3600)
    m = rem // 60
    return f"{d}d {h}h" if d else (f"{h}h {m:02d}m" if h else f"{m}m")


def tz_name():
    try:
        return os.path.realpath("/etc/localtime").split("zoneinfo/")[1]
    except Exception:
        return datetime.now().astimezone().tzname() or ""


def reset_at(iso):
    """Absolute local reset time, e.g. '2:19am (Asia/Bangkok)' or 'Oct 14, 12:59pm (Asia/Bangkok)'."""
    try:
        t = datetime.fromisoformat(iso).astimezone()
    except Exception:
        return "?"
    clock = f"{t.hour % 12 or 12}:{t:%M}{'am' if t.hour < 12 else 'pm'}"
    when = clock if t.date() == datetime.now().astimezone().date() else f"{t:%b} {t.day}, {clock}"
    return f"{when} ({tz_name()})"


def color_for(pct):
    return (76, 175, 80) if pct < 60 else (255, 179, 0) if pct < 85 else (229, 57, 53)
