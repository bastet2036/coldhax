#!/usr/bin/env python3
"""Generate machine-readable, TEST-ONLY evidence from local inputs."""

from __future__ import annotations

import hashlib
import json
import struct
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from coldhax_model import (
    TEST_ONLY_AFFECTED_INPUTS,
    affected_seed_entropy,
    fixed_seed_entropy,
    synthetic_hardware_words,
)

ROOT = Path(__file__).resolve().parent
SOURCES = ROOT / "sources"
EVIDENCE = ROOT / "evidence"
FIRMWARE = SOURCES / "firmware"

ARTIFACT_PATHS = (
    ".gitignore",
    "LICENSE",
    "README.md",
    "REPORT.md",
    "METHODOLOGY.md",
    "setup_sources.sh",
    "coldhax_model.py",
    "generate_evidence.py",
    "run_upstream_evidence.py",
    "test_coldhax_model.py",
    "harness/affected_provider.c",
    "harness/fixed_provider.c",
    "harness/main.c",
    "harness/micropython_stubs.c",
    "harness/provider.h",
    "harness/build.sh",
    "harness/include/py/obj.h",
    "harness/include/py/runtime.h",
    "harness/include/py/mperrno.h",
    "evidence/analysis.json",
    "evidence/commands.txt",
    "evidence/proof-gates.json",
    "evidence/provenance.json",
    "evidence/source-dfu-mapping.json",
    "evidence/upstream-execution.json",
    "evidence/test-results.txt",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(FIRMWARE), *args], text=True
    ).strip()


def stable_generated_at(path: Path) -> str:
    """Preserve the first valid generation time across reproducible reruns."""
    try:
        value = json.loads(path.read_text()).get("generated_at_utc")
        if isinstance(value, str) and value:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            return value
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        pass
    return datetime.now(timezone.utc).isoformat()


def write_artifact_hashes() -> None:
    lines = []
    for relative in ARTIFACT_PATHS:
        path = ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(f"required artifact missing: {relative}")
        lines.append(f"{sha256_file(path)}  {relative}")
    (EVIDENCE / "artifact-hashes.txt").write_text("\n".join(lines) + "\n")


def dfu_elements(path: Path) -> list[dict[str, object]]:
    image = path.read_bytes()
    if image[:5] != b"DfuSe":
        raise ValueError(f"not DfuSe: {path}")
    target_count = image[10]
    offset = 11
    result = []
    for target_index in range(target_count):
        signature, alternate, named, name, size, count = struct.unpack_from(
            "<6sBI255sII", image, offset
        )
        if signature != b"Target":
            raise ValueError("invalid target signature")
        offset += 274
        elements = []
        for _ in range(count):
            address, length = struct.unpack_from("<II", image, offset)
            offset += 8
            data = image[offset : offset + length]
            offset += length
            elements.append(
                {
                    "address": f"0x{address:08x}",
                    "size": length,
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            )
        result.append(
            {
                "target_index": target_index,
                "alternate": alternate,
                "named": bool(named),
                "name": name.rstrip(b"\0").decode("ascii", "replace"),
                "declared_size": size,
                "elements": elements,
            }
        )
    return result


def main() -> None:
    EVIDENCE.mkdir(exist_ok=True)
    inputs = {}
    for path in sorted(SOURCES.iterdir()):
        if path.is_file():
            inputs[path.name] = {"size": path.stat().st_size, "sha256": sha256_file(path)}

    affected = SOURCES / "2023-06-26T1241-v4.1.9-coldcard.dfu"
    fixed = SOURCES / "2026-07-31T1248-v4.2.0-coldcard.dfu"
    provenance = {
        "generated_at_utc": stable_generated_at(EVIDENCE / "provenance.json"),
        "scope": "local authoritative inputs only",
        "source_urls": [
            "https://coldcard.com/downloads/mk3",
            "https://github.com/Coldcard/firmware/tree/v4-legacy",
            "https://blog.coinkite.com/coldcard-mk3-seed-generation-warning/",
            "https://github.com/Coldcard/firmware/blob/621e808712464688584fdffad9eba132cc7c27cd/shared/seed.py#L276-L332",
        ],
        "firmware_repository": {
            "head": git("rev-parse", "HEAD"),
            "branch": git("branch", "--show-current"),
            "affected_tag": "2023-06-26T1241-v4.1.9",
            "affected_tag_object": git("rev-parse", "2023-06-26T1241-v4.1.9^{tag}"),
            "affected_commit": git("rev-parse", "2023-06-26T1241-v4.1.9^{}"),
            "fixed_revision": git("rev-parse", "HEAD"),
            "fix_commit": git("rev-parse", "4543629^{}"),
            "libngu_gitlink": git("rev-parse", "HEAD:external/libngu"),
            "micropython_gitlink": git("rev-parse", "HEAD:external/micropython"),
        },
        "inputs": inputs,
        "dfu": {
            affected.name: dfu_elements(affected),
            fixed.name: dfu_elements(fixed),
        },
    }
    (EVIDENCE / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")

    affected_outputs = [
        affected_seed_entropy(TEST_ONLY_AFFECTED_INPUTS) for _ in range(256)
    ]
    fixed_outputs = [
        fixed_seed_entropy(synthetic_hardware_words(case)) for case in range(256)
    ]
    baseline = synthetic_hardware_words(0)
    contribution_gate = []
    for index in range(8):
        changed = baseline.copy()
        changed[index] ^= 0x80000000
        contribution_gate.append(fixed_seed_entropy(changed) != fixed_seed_entropy(baseline))
    proof = {
        "label": "TEST-ONLY source/model-level proof; not hardware emulation",
        "sample_count": 256,
        "positive_control": {
            "identical_register_tuple_resets": 256,
            "cold_boot_model_unique_outputs": len(set(affected_outputs)),
            "pass_condition": "exactly one unique output",
            "passed": len(set(affected_outputs)) == 1,
        },
        "negative_control": {
            "distinct_injected_hardware_inputs": 256,
            "unique_outputs": len(set(fixed_outputs)),
            "each_of_eight_words_high_bit_flip_changes_result": contribution_gate,
            "pass_condition": "256 unique outputs and every input word contributes",
            "passed": len(set(fixed_outputs)) == 256 and all(contribution_gate),
        },
        "interpretation_limit": (
            "A bounded deterministic collision/contribution check only; it is not a "
            "randomness test and makes no estimate of physical RNG entropy."
        ),
    }
    (EVIDENCE / "proof-gates.json").write_text(json.dumps(proof, indent=2) + "\n")
    write_artifact_hashes()


if __name__ == "__main__":
    main()
