#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
DEST="$ROOT/sources/firmware"
FIXED_REV=43770339b0b97753b883c58764ce17f081350b30
LIBNGU_REV=356b9137cf7ddf5de66ec4cdc0a4d757b2e42790
MICROPYTHON_REV=f3b2a8c2e988fc9cdf16812bb48a9964911329a9

if [ -e "$DEST" ]; then
    echo "refusing to overwrite existing path: $DEST" >&2
    exit 1
fi

mkdir -p "$ROOT/sources"
git clone --filter=blob:none https://github.com/Coldcard/firmware.git "$DEST"
git -C "$DEST" checkout --detach "$FIXED_REV"
git -C "$DEST" submodule update --init external/libngu external/micropython

actual_fw=$(git -C "$DEST" rev-parse HEAD)
actual_libngu=$(git -C "$DEST/external/libngu" rev-parse HEAD)
actual_micropython=$(git -C "$DEST/external/micropython" rev-parse HEAD)

[ "$actual_fw" = "$FIXED_REV" ] || { echo "firmware revision mismatch" >&2; exit 1; }
[ "$actual_libngu" = "$LIBNGU_REV" ] || { echo "libngu revision mismatch" >&2; exit 1; }
[ "$actual_micropython" = "$MICROPYTHON_REV" ] || { echo "MicroPython revision mismatch" >&2; exit 1; }

git -C "$DEST" cat-file -e '2023-06-26T1241-v4.1.9^{commit}'
printf 'Pinned sources ready:\n  firmware %s\n  libngu %s\n  MicroPython %s\n' \
    "$actual_fw" "$actual_libngu" "$actual_micropython"
