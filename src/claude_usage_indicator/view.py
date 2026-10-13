"""Turn an API response into the label, tooltip and menu rows (no GUI imports)."""
from collections import namedtuple
from datetime import datetime

from .fmt import bar, reset_at, status_dot
from .settings import fmt_interval

View = namedtuple("View", "label tooltip rows session weekly error")

EXTRA_LIMITS = (("seven_day_opus", "Current week (Opus)"), ("seven_day_sonnet", "Current week (Sonnet)"),
                ("seven_day_oauth_apps", "Current week (OAuth apps)"), ("seven_day_cowork", "Current week (Cowork)"))


def build_view(data, err, interval, now=None):
    if err:
        return View("!", err, [("item", "⚠  " + err)], None, None, err)
    rows, tip = [], []
    sess = data.get("five_hour") or {}
    week = data.get("seven_day") or {}
    sp, wp = sess.get("utilization"), week.get("utilization")
    label = " · ".join(f"{p:.0f}%" for p in (sp, wp) if p is not None) or "n/a"

    def limit(name, d):
        if d and d.get("utilization") is not None:
            p = d["utilization"]
            if tip:
                rows.append(("sep", ""))
            rows.append(("item", f"{status_dot(p)}  {name}"))
            rows.append(("item", f"{bar(p)}   {p:.0f}% used"))
            rows.append(("item", f"Resets {reset_at(d.get('resets_at'))}"))
            tip.append(f"{name}: {p:.0f}% (resets {reset_at(d.get('resets_at'))})")

    limit("Current session", sess)
    limit("Current week (all models)", week)
    for key, name in EXTRA_LIMITS:
        limit(name, data.get(key))
    ex = data.get("extra_usage") or {}
    if ex.get("is_enabled") and ex.get("monthly_limit"):
        cur = {"GBP": "£", "USD": "$", "EUR": "€"}.get(ex.get("currency"), "")
        div = 10 ** ex.get("decimal_places", 2)
        used, lim = ex["used_credits"] / div, ex["monthly_limit"] / div
        rows.append(("sep", ""))
        rows.append(("item", "💳  Extra usage"))
        rows.append(("item", f"{bar(used / lim * 100 if lim else 0)}   {cur}{used:.2f} / {cur}{lim:.2f}"))
        tip.append(f"Extra usage: {cur}{used:.2f} / {cur}{lim:.2f}")
    rows.append(("sep", ""))
    stamp = (now or datetime.now()).strftime("%H:%M:%S")
    rows.append(("item", f"Updated {stamp}  ·  every {fmt_interval(interval)}"))
    return View(label, "\n".join(tip) or "No usage data", rows, sp, wp, None)
