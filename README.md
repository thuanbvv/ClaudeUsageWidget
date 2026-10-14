# Claude Usage Indicator

A GNOME/Ubuntu top-bar indicator that shows your **Claude Code plan usage** (the same data as `claude /usage`).

- Two concentric ring gauges: outer = 5-hour session, inner = weekly. Green / amber / red by usage.
- Menu with progress bars and the **exact reset time** for each limit (session, weekly, per-model, extra usage).
- Configurable auto-refresh interval (30 s – 30 min), saved between runs.
- Reuses the login of Claude Code (`~/.claude/.credentials.json`). Nothing is sent anywhere except `api.anthropic.com`.

## Install (Ubuntu / Debian)

Download the `.deb` from the [latest release](../../releases/latest) and run:

```bash
sudo apt install ./claude-usage-indicator_*_all.deb
```

On GNOME you also need the AppIndicator extension (installed as a recommended package on Ubuntu):
`gnome-shell-extension-appindicator`. Log out and in once, then start **Claude Usage Indicator** from the app menu. It autostarts on login afterwards.

## From source

```bash
sudo apt install python3-gi
PYTHONPATH=src python3 -m claude_usage_indicator          # runs detached in the background (-f to stay in foreground)
PYTHONPATH=src python3 -m claude_usage_indicator --once   # print raw usage JSON
pip install pytest && python -m pytest                    # tests
./scripts/build-deb.sh                                    # build dist/*.deb
```

## Releasing

Bump `__version__` in `src/claude_usage_indicator/__init__.py`, then `git tag vX.Y.Z && git push --tags`;
GitHub Actions builds the `.deb` and attaches it to the release.

## Disclaimer

Unofficial project, not affiliated with Anthropic. It uses an undocumented usage endpoint that may change.

## License

MIT
