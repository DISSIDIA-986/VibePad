#!/bin/zsh
REPO="$(cd "$(dirname "$0")/.." && pwd)"
exec "$REPO/bin/spike-lb-watch.sh"
