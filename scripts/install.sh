#!/bin/bash
# install sc CLI to a directory in PATH
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${1:-$HOME/.local/bin}"

mkdir -p "$TARGET"
ln -sf "$ROOT/bin/sc" "$TARGET/sc"

echo "Installed: $TARGET/sc → $ROOT/bin/sc"
echo "Add to PATH if needed: export PATH=\"$TARGET:\$PATH\""
