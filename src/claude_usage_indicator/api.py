"""Fetch plan usage from the Anthropic OAuth usage endpoint (same data as `claude /usage`)."""
import json
import os
import time
import urllib.error
import urllib.request

from . import __version__

CRED_PATH = os.path.expanduser("~/.claude/.credentials.json")
USAGE_URL = "https://api.anthropic.com/api/oauth/usage"


def fetch_usage():
    """Return (data, error). Re-reads credentials each call so CLI token refreshes are picked up."""
    try:
        with open(CRED_PATH) as f:
            oauth = json.load(f)["claudeAiOauth"]
    except Exception as e:
        return None, f"No Claude login found ({e.__class__.__name__}). Run `claude` to sign in."
    if oauth.get("expiresAt", 0) / 1000 < time.time() - 5:
        return None, "Login token expired. Use Claude Code once to refresh it."
    req = urllib.request.Request(USAGE_URL, headers={
        "Authorization": "Bearer " + oauth["accessToken"],
        "anthropic-beta": "oauth-2025-04-20",
        "User-Agent": "claude-usage-indicator/" + __version__,
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code} from usage API" + (" (token expired?)" if e.code == 401 else "")
    except Exception as e:
        return None, f"Network error: {e}"
