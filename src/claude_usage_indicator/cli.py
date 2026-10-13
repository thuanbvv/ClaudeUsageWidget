"""Command-line entry point."""
import argparse
import json

from . import __version__
from .api import fetch_usage


def main(argv=None):
    ap = argparse.ArgumentParser(prog="claude-usage-indicator", description=__doc__)
    ap.add_argument("--once", action="store_true", help="print the raw usage JSON once and exit")
    ap.add_argument("--version", action="version", version=__version__)
    args = ap.parse_args(argv)
    if args.once:
        data, err = fetch_usage()
        print(err or json.dumps(data, indent=2))
        return 1 if err else 0

    from gi.repository import GLib  # imported late so --once/--version work without PyGObject
    from .indicator import Indicator
    loop = GLib.MainLoop()
    Indicator(loop).start()
    loop.run()
    return 0
