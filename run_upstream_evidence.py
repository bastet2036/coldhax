#!/usr/bin/env python3
"""Build and execute the TEST-ONLY exact-upstream entropy harnesses."""

from __future__ import annotations

import hashlib
import json
import platform
import re
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FW = ROOT / "sources" / "firmware"
BUILD = ROOT / "harness" / "build"
EVIDENCE = ROOT / "evidence"
LOGS = ROOT / "logs"
LINE = re.compile(
    r"^TEST-ONLY raw_entropy=([0-9a-f]{64}) sha256_seed_entropy=([0-9a-f]{64})$"
)
AFFECTED_REGISTERS = (0x00543210, 0x54455354, 0x00123456, 0x00000123)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(FW), *args], text=True).strip()


def version_line(*command: str) -> str:
    """Capture one stable identifying line for the local native toolchain."""
    output = subprocess.check_output(command, text=True, stderr=subprocess.STDOUT)
    return output.splitlines()[0].strip()


def synthetic_words(case: int) -> list[int]:
    return [((0x54455354 + case * 0x9E3779B9 + index) & 0xFFFFFFFF) for index in range(8)]


def execute(binary: Path, values: Sequence[int]) -> dict[str, str]:
    command = [str(binary), *(f"0x{value:08x}" for value in values)]
    output = subprocess.check_output(command, text=True).strip()
    match = LINE.fullmatch(output)
    if not match:
        raise ValueError(f"unexpected harness output: {output!r}")
    return {"raw_entropy": match.group(1), "sha256_seed_entropy": match.group(2)}


def controls(binary: Path, affected: bool) -> dict[str, object]:
    baseline: list[int] = list(AFFECTED_REGISTERS) if affected else synthetic_words(0)
    repeated = [execute(binary, baseline) for _ in range(256)]
    if affected:
        varied_inputs = [
            [AFFECTED_REGISTERS[0] ^ case, *AFFECTED_REGISTERS[1:]] for case in range(256)
        ]
    else:
        varied_inputs = [synthetic_words(case) for case in range(256)]
    varied = [execute(binary, values) for values in varied_inputs]

    contribution = []
    baseline_output = execute(binary, baseline)["sha256_seed_entropy"]
    for index in range(len(baseline)):
        changed = baseline.copy()
        # Flip one high bit without making adjacent synthetic hardware words equal;
        # exact libngu intentionally faults on consecutive equal provider words.
        changed[index] ^= 0x80000000
        contribution.append(
            execute(binary, changed)["sha256_seed_entropy"] != baseline_output
        )

    return {
        "provider_input_kind": (
            "SysTick/UID/RTC synthetic register tuple"
            if affected
            else "synthetic hardware RNG word stream"
        ),
        "identical_input_control": {
            "runs_in_fresh_processes": 256,
            "unique_raw_outputs": len({item["raw_entropy"] for item in repeated}),
            "unique_sha256_outputs": len(
                {item["sha256_seed_entropy"] for item in repeated}
            ),
            "passed": len({item["sha256_seed_entropy"] for item in repeated}) == 1,
        },
        "varied_input_control": {
            "runs_in_fresh_processes": 256,
            "unique_raw_outputs": len({item["raw_entropy"] for item in varied}),
            "unique_sha256_outputs": len(
                {item["sha256_seed_entropy"] for item in varied}
            ),
            "passed": len({item["sha256_seed_entropy"] for item in varied}) == 256,
        },
        "each_provider_input_high_bit_flip_changes_sha256": contribution,
        "sample": repeated[0],
    }


def main() -> None:
    EVIDENCE.mkdir(exist_ok=True)
    LOGS.mkdir(exist_ok=True)
    build = subprocess.run(
        [str(ROOT / "harness" / "build.sh")],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=True,
    )
    (LOGS / "upstream-harness-build.txt").write_text(build.stdout)

    affected_binary = BUILD / "affected" / "upstream-entropy"
    fixed_binary = BUILD / "fixed" / "upstream-entropy"
    source_paths = {
        "libngu_random": FW / "external" / "libngu" / "ngu" / "random.c",
        "micropython_affected_provider": (
            FW / "external" / "micropython" / "ports" / "stm32" / "rng.c"
        ),
        "v4_legacy_fixed_provider": FW / "stm32" / "COLDCARD" / "rng.c",
    }
    result = {
        "label": "TEST-ONLY synthetic entropy bytes; never wallet material",
        "evidence_tier": "b: exact pinned upstream C entropy components executed with narrow synthetic register shims",
        "boundaries": [
            "No device, wallet, mnemonic, key derivation, or physical RNG is used.",
            "MicroPython object plumbing is stubbed; executed entropy generation is upstream libngu random.c and the selected upstream rng.c provider.",
            "OpenSSL SHA-256 stands in for the unchanged Python ngu.hash.sha256s call after the 32 upstream bytes are produced.",
            "Each run is a fresh process so upstream static PRNG initialization matches a cold start.",
        ],
        "revisions": {
            "firmware_affected_commit": git("rev-parse", "2023-06-26T1241-v4.1.9^{}"),
            "firmware_fixed_revision": git("rev-parse", "HEAD"),
            "libngu": git("rev-parse", "HEAD:external/libngu"),
            "micropython": git("rev-parse", "HEAD:external/micropython"),
        },
        "compiled_source_sha256": {
            name: sha256_file(path) for name, path in source_paths.items()
        },
        "execution_environment": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "python": sys.version.splitlines()[0],
            "gcc": version_line("gcc", "--version"),
            "linker": version_line("ld", "--version"),
            "openssl": version_line("openssl", "version"),
        },
        "binary_hash_semantics": (
            "Run identifiers for this local build, not portable reproducible-build "
            "expectations across architectures, toolchains, paths, or OpenSSL builds."
        ),
        "binary_sha256": {
            "affected": sha256_file(affected_binary),
            "fixed": sha256_file(fixed_binary),
        },
        "affected_4_1_9": controls(affected_binary, affected=True),
        "fixed_v4_legacy_4_2_0": controls(fixed_binary, affected=False),
    }
    (EVIDENCE / "upstream-execution.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
