#!/usr/bin/env bash
# Build dist/claude-usage-indicator_<version>_all.deb (needs dpkg-deb, fakeroot).
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
version="$(sed -n 's/^__version__ = "\(.*\)"/\1/p' "$root/src/claude_usage_indicator/__init__.py")"
pkg="claude-usage-indicator"
stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT

install -d "$stage/usr/lib/python3/dist-packages" "$stage/usr/bin" \
  "$stage/usr/share/applications" "$stage/etc/xdg/autostart" \
  "$stage/usr/share/doc/$pkg" "$stage/DEBIAN"
cp -r "$root/src/claude_usage_indicator" "$stage/usr/lib/python3/dist-packages/"
find "$stage" -name __pycache__ -prune -exec rm -rf {} +
cat > "$stage/usr/bin/$pkg" <<'LAUNCH'
#!/usr/bin/python3
import sys
from claude_usage_indicator.cli import main
sys.exit(main())
LAUNCH
chmod 755 "$stage/usr/bin/$pkg"
install -m644 "$root/packaging/$pkg.desktop" "$stage/usr/share/applications/$pkg.desktop"
install -m644 "$root/packaging/$pkg.desktop" "$stage/etc/xdg/autostart/$pkg.desktop"
install -m644 "$root/README.md" "$stage/usr/share/doc/$pkg/README.md"
cat > "$stage/usr/share/doc/$pkg/copyright" <<COPY
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: $pkg
Files: *
Copyright: 2026 thuanbv
License: MIT
$(sed '1,2d; s/^$/./; s/^/ /' "$root/LICENSE")
COPY

chmod -R go-w,a+rX "$stage"
size="$(du -sk "$stage" | cut -f1)"
cat > "$stage/DEBIAN/control" <<CTRL
Package: $pkg
Version: $version
Section: utils
Priority: optional
Architecture: all
Depends: python3 (>= 3.8), python3-gi, gir1.2-glib-2.0
Recommends: gnome-shell-extension-appindicator
Installed-Size: $size
Maintainer: thuanbv <thuanbv2203@gmail.com>
Homepage: https://github.com/thuanbvv/ClaudeUsageWidget
Description: Top-bar indicator showing Claude Code plan usage
 Shows the 5-hour session and weekly usage of your Claude plan as a ring
 gauge in the GNOME/Ubuntu top bar, with exact reset times and a
 configurable refresh interval. Uses the same login as Claude Code.
CTRL
mkdir -p "$root/dist"
out="$root/dist/${pkg}_${version}_all.deb"
fakeroot dpkg-deb --build --root-owner-group "$stage" "$out" >/dev/null
echo "$out"
