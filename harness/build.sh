#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
FW="$ROOT/sources/firmware"
OUT="$ROOT/harness/build"
INCLUDE="$ROOT/harness/include"
LIBNGU="$FW/external/libngu/ngu/random.c"
MP_RNG="$FW/external/micropython/ports/stm32/rng.c"
BOARD_RNG="$FW/stm32/COLDCARD/rng.c"

mkdir -p "$OUT/affected" "$OUT/fixed"
COMMON="-std=c11 -O2 -Wall -Wextra -Werror -Wno-unused-function -Wno-unused-const-variable -ffunction-sections -fdata-sections -I$INCLUDE -I$ROOT/harness"

# Compile the pinned libngu implementation itself, rather than a copied transcription.
gcc $COMMON -U__linux__ -DMICROPY_PY_STM=1 -DMICROPY_HW_ENABLE_RNG=0 -c "$LIBNGU" -o "$OUT/libngu-random.o"
gcc $COMMON -c "$ROOT/harness/micropython_stubs.c" -o "$OUT/micropython-stubs.o"
gcc $COMMON -c "$ROOT/harness/main.c" -o "$OUT/main.o"

# Affected provider: the pinned MicroPython fallback with four synthetic register shims.
gcc $COMMON -DUPSTREAM_PROVIDER_SOURCE='"'"$MP_RNG"'"' \
    -c "$ROOT/harness/affected_provider.c" -o "$OUT/affected/provider.o"
gcc -Wl,--gc-sections "$OUT/main.o" "$OUT/micropython-stubs.o" \
    "$OUT/libngu-random.o" "$OUT/affected/provider.o" -lcrypto \
    -o "$OUT/affected/upstream-entropy"

# Fixed provider: v4-legacy board rng.c with synthetic RNG-register delivery in HAL_GetTick.
gcc $COMMON -DUPSTREAM_PROVIDER_SOURCE='"'"$BOARD_RNG"'"' \
    -c "$ROOT/harness/fixed_provider.c" -o "$OUT/fixed/provider.o"
gcc -Wl,--gc-sections "$OUT/main.o" "$OUT/micropython-stubs.o" \
    "$OUT/libngu-random.o" "$OUT/fixed/provider.o" -lcrypto \
    -o "$OUT/fixed/upstream-entropy"

sha256sum "$LIBNGU" "$MP_RNG" "$BOARD_RNG" \
    "$OUT/affected/upstream-entropy" "$OUT/fixed/upstream-entropy"
