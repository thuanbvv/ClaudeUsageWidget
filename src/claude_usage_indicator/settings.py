"""User settings, persisted as JSON under ~/.config."""
import json
import os
import sys

SETTINGS_PATH = os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"),
                             "claude-usage-indicator", "settings.json")
INTERVALS = [(30, "30 seconds"), (60, "1 minute"), (120, "2 minutes"), (300, "5 minutes"),
             (600, "10 minutes"), (900, "15 minutes"), (1800, "30 minutes")]
DEFAULT_INTERVAL = 60


def load_settings():
    try:
        with open(SETTINGS_PATH) as f:
            iv = int(json.load(f).get("interval", DEFAULT_INTERVAL))
        return {"interval": iv if iv >= 30 else DEFAULT_INTERVAL}
    except Exception:
        return {"interval": DEFAULT_INTERVAL}


def save_settings(st):
    try:
        os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
        with open(SETTINGS_PATH, "w") as f:
            json.dump(st, f)
    except OSError as e:
        print("Could not save settings:", e, file=sys.stderr)


def fmt_interval(secs):
    return next((n for v, n in INTERVALS if v == secs), f"{secs}s")
