from datetime import datetime

from claude_usage_indicator.fmt import bar, reset_at, status_dot, until
from claude_usage_indicator.icon import ICON_SIZE, render_icon
from claude_usage_indicator.view import build_view

DATA = {
    "five_hour": {"utilization": 23, "resets_at": "2030-01-01T00:00:00+00:00"},
    "seven_day": {"utilization": 64, "resets_at": "2030-01-02T00:00:00+00:00"},
}


def test_bar_bounds():
    assert bar(0, 10) == "░" * 10
    assert bar(100, 10) == "█" * 10
    assert bar(150, 10) == "█" * 10


def test_status_dot_thresholds():
    assert status_dot(59) == "🟢" and status_dot(60) == "🟡" and status_dot(85) == "🔴"


def test_until_and_reset_handle_garbage():
    assert until("nope") == "?" and reset_at("nope") == "?"


def test_view_label_and_rows():
    v = build_view(DATA, None, 300, now=datetime(2026, 1, 1, 12, 0, 0))
    assert v.label == "23% · 64%"
    assert (v.session, v.weekly) == (23, 64)
    texts = [t for _, t in v.rows]
    assert any("Current session" in t for t in texts)
    assert texts[-1] == "Updated 12:00:00  ·  every 5 minutes"


def test_view_error():
    v = build_view(None, "boom", 60)
    assert v.label == "!" and v.error == "boom" and v.session is None


def test_extra_usage_row():
    data = dict(DATA, extra_usage={"is_enabled": True, "monthly_limit": 5000, "used_credits": 320,
                                   "currency": "GBP", "decimal_places": 2})
    v = build_view(data, None, 60)
    assert any("£3.20 / £50.00" in t for _, t in v.rows)


def test_icon_size():
    assert len(render_icon(10, 90)) == ICON_SIZE * ICON_SIZE * 4
    assert len(render_icon(None)) == ICON_SIZE * ICON_SIZE * 4
