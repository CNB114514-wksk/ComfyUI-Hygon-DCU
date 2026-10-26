#!/usr/bin/env bash
# Apply the Hygon DCU patch set to a ComfyUI checkout.
#
#   ./scripts/apply.sh [--with-autodownload] [target-dir]
#
# target-dir defaults to the current directory. The checkout must be at the
# pinned upstream commit, otherwise the patches will not apply cleanly.
set -euo pipefail

COMMIT=daeb5e53
WITH_AD=0
if [ "${1:-}" = "--with-autodownload" ]; then WITH_AD=1; shift; fi
DEST=${1:-.}

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

if [ ! -d "$DEST/.git" ]; then
  echo "error: $DEST is not a git checkout" >&2
  exit 1
fi

HEAD=$(git -C "$DEST" rev-parse --short HEAD)
if [ "$HEAD" != "$COMMIT" ]; then
  echo "error: $DEST is at $HEAD, expected $COMMIT" >&2
  echo "       git -C $DEST checkout $COMMIT" >&2
  exit 1
fi

apply_dir() {
  local dir=$1
  for p in "$dir"/*.patch; do
    [ -e "$p" ] || continue
    if patch -p1 -R -f -s --dry-run -d "$DEST" < "$p" >/dev/null 2>&1; then
      echo "skip   $(basename "$p") (already applied)"
    else
      patch -p1 -f -s -d "$DEST" < "$p"
      echo "apply  $(basename "$p")"
    fi
  done
}

apply_dir "$HERE/patches"
if [ "$WITH_AD" = "1" ]; then
  apply_dir "$HERE/patches-autodownload"
else
  echo "note: patches-autodownload/ skipped (needs hook_by_xu)"
fi

echo "done"
