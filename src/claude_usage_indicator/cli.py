"""Command-line entry point."""
import argparse
import fcntl
import json
import os
import sys

from . import __version__
from .api import fetch_usage


def _detach():
    """Fork into the background so the launching terminal can be closed."""
    if os.fork():
        os._exit(0)
    os.setsid()
    if os.fork():
        os._exit(0)
    devnull = os.open(os.devnull, os.O_RDWR)
    for fd in (0, 1, 2):
        os.dup2(devnull, fd)


def _single_instance():
    """Hold an exclusive lock for the process lifetime; False if already running."""
    path = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "claude-usage-indicator.lock")
    lock = open(path, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return None
    return lock


def main(argv=None):
    ap = argparse.ArgumentParser(prog="claude-usage-indicator", description=__doc__)
    ap.add_argument("--once", action="store_true", help="print the raw usage JSON once and exit")
    ap.add_argument("--version", action="version", version=__version__)
    ap.add_argument("-f", "--foreground", action="store_true", help="don't detach from the terminal")
    args = ap.parse_args(argv)
    if args.once:
        data, err = fetch_usage()
        print(err or json.dumps(data, indent=2))
        return 1 if err else 0

    lock = _single_instance()
    if lock is None:
        print("claude-usage-indicator is already running", file=sys.stderr)
        return 0
    if not args.foreground:
        _detach()

    from gi.repository import GLib  # imported late so --once/--version work without PyGObject
    from .indicator import Indicator
    loop = GLib.MainLoop()
    Indicator(loop).start()
    loop.run()
    return 0
