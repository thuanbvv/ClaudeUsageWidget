"""Fetch plan usage from the Anthropic OAuth usage endpoint (same data as `claude /usage`)."""
import json
import os
import time
import urllib.error
import urllib.request

from . import __version__

CRED_PATH = os.path.expanduser("~/.claude/.credentials.json")
USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
TOKEN_URL = "https://platform.claude.com/v1/oauth/token"
CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"  # Claude Code's public OAuth client id


def _refresh_token(creds, oauth):
    """Exchange the refresh token for a new access token and persist it. Return error string or None."""
    body = json.dumps({"grant_type": "refresh_token", "refresh_token": oauth.get("refreshToken"),
                       "client_id": CLIENT_ID}).encode()
    req = urllib.request.Request(TOKEN_URL, data=body, headers={
        "Content-Type": "application/json",
        "User-Agent": "claude-usage-indicator/" + __version__,
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            tok = json.load(r)
        oauth["accessToken"] = tok["access_token"]
        oauth["refreshToken"] = tok.get("refresh_token", oauth["refreshToken"])
        oauth["expiresAt"] = int((time.time() + tok["expires_in"]) * 1000)
        # Write atomically (refresh tokens rotate, so a torn write would log the CLI out too).
        tmp = CRED_PATH + ".tmp"
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(creds, f)
        os.replace(tmp, CRED_PATH)
    except Exception as e:
        return str(e)
    return None


def fetch_usage():
    """Return (data, error). Re-reads credentials each call so CLI token refreshes are picked up."""
    try:
        with open(CRED_PATH) as f:
            creds = json.load(f)
        oauth = creds["claudeAiOauth"]
    except Exception as e:
        return None, f"No Claude login found ({e.__class__.__name__}). Run `claude` to sign in."
    if oauth.get("expiresAt", 0) / 1000 < time.time() + 60:
        if not oauth.get("refreshToken") or _refresh_token(creds, oauth):
            return None, "Login token expired and auto-refresh failed. Use Claude Code once to sign in again."
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
