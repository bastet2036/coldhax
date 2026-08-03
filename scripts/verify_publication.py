#!/usr/bin/env python3
"""Fail closed when the tracked public tree contains forbidden artifacts or key material."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PATHS = re.compile(
    r"^(?:sources/|state/|logs/|harness/build/|__pycache__/)|"
    r"\.(?:dfu|bin|elf|o|pyc)$",
    re.IGNORECASE,
)
SECRET_PATTERNS = {
    "PEM private key": re.compile(rb"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----"),
    "extended private key": re.compile(rb"\b(?:xprv|tprv)[1-9A-HJ-NP-Za-km-z]{40,}\b"),
    "WIF private key": re.compile(
        rb"\b(?:5[HJK][1-9A-HJ-NP-Za-km-z]{49,50}|[KL][1-9A-HJ-NP-Za-km-z]{51})\b"
    ),
    "GitHub token": re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    "AWS access key": re.compile(rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
}
MAX_TRACKED_BYTES = 1_048_576


def tracked_files() -> list[str]:
    output = subprocess.check_output(
        ["git", "-C", str(ROOT), "ls-files", "-z"]
    )
    return [item.decode() for item in output.rstrip(b"\0").split(b"\0") if item]


def main() -> None:
    failures: list[str] = []
    files = tracked_files()
    for relative in files:
        if FORBIDDEN_PATHS.search(relative):
            failures.append(f"forbidden tracked path: {relative}")
            continue
        path = ROOT / relative
        if not path.is_file():
            failures.append(f"tracked path is not a regular file: {relative}")
            continue
        size = path.stat().st_size
        if size >= MAX_TRACKED_BYTES:
            failures.append(f"tracked file is at least 1 MiB: {relative} ({size} bytes)")
        data = path.read_bytes()
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(data):
                failures.append(f"{label} pattern in tracked file: {relative}")
    if failures:
        raise SystemExit("publication verification failed:\n- " + "\n- ".join(failures))
    print(f"publication verification passed: {len(files)} tracked files")


if __name__ == "__main__":
    main()
