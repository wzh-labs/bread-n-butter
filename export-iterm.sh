#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ITERM_PLIST_SRC="$HOME/Library/Preferences/com.googlecode.iterm2.plist"
ITERM_PLIST_DEST="$REPO_DIR/iterm/com.googlecode.iterm2.plist"

# cfprefsd caches plist writes in memory; restart it so the on-disk file is current.
killall cfprefsd 2>/dev/null || true

cp "$ITERM_PLIST_SRC" "$ITERM_PLIST_DEST"
echo "exported $ITERM_PLIST_DEST"
