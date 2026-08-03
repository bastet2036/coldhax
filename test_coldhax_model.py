#!/usr/bin/env python3
"""Automated tests for the safe Coldcard Mk3 source and execution models."""

import json
import unittest
from pathlib import Path
from subprocess import check_output
from tempfile import TemporaryDirectory

from coldhax_model import (
    AffectedRegisterInputs,
    TEST_ONLY_AFFECTED_INPUTS,
    Yasmarang,
    affected_seed_entropy,
    fixed_seed_entropy,
    synthetic_hardware_words,
)
from generate_evidence import stable_generated_at


class YasmarangTests(unittest.TestCase):
    def test_transition_vector_is_stable(self):
        # TEST-ONLY regression vector generated from the transcribed transition.
        rng = Yasmarang(pad=0x0A8CE26F, n=69, d=233)
        self.assertEqual(
            [rng.word() for _ in range(4)],
            [0x12F99F10, 0x1E0841DF, 0x8F794C6C, 0x94014480],
        )

    def test_cold_boot_repeats_affected_output(self):
        outputs = {affected_seed_entropy(TEST_ONLY_AFFECTED_INPUTS) for _ in range(64)}
        self.assertEqual(len(outputs), 1)

    def test_affected_model_matches_compiled_upstream_path(self):
        evidence = json.loads(Path("evidence/upstream-execution.json").read_text())
        expected = bytes.fromhex(
            evidence["affected_4_1_9"]["sample"]["sha256_seed_entropy"]
        )
        self.assertEqual(affected_seed_entropy(TEST_ONLY_AFFECTED_INPUTS), expected)

    def test_each_initializer_register_can_change_output(self):
        baseline = TEST_ONLY_AFFECTED_INPUTS
        original = affected_seed_entropy(baseline)
        for field in ("systick_current", "uid_word", "rtc_time", "rtc_subsecond"):
            values = baseline.__dict__.copy()
            values[field] ^= 1
            self.assertNotEqual(
                affected_seed_entropy(AffectedRegisterInputs(**values)), original
            )


class FixedPathTests(unittest.TestCase):
    def test_fixed_path_uses_all_eight_hardware_words(self):
        baseline = synthetic_hardware_words(0)
        original = fixed_seed_entropy(baseline)
        for index in range(8):
            changed = baseline.copy()
            changed[index] ^= 0x80000000
            self.assertNotEqual(fixed_seed_entropy(changed), original)

    def test_distinct_synthetic_inputs_do_not_repeat_in_bounded_gate(self):
        outputs = {
            fixed_seed_entropy(synthetic_hardware_words(case)) for case in range(256)
        }
        self.assertEqual(len(outputs), 256)

    def test_fixed_path_rejects_short_input(self):
        with self.assertRaises(ValueError):
            fixed_seed_entropy(range(1, 8))


class EvidenceTests(unittest.TestCase):
    def test_generation_time_is_preserved_on_rerun(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "provenance.json"
            expected = "2026-08-01T15:49:03+00:00"
            path.write_text('{"generated_at_utc": "' + expected + '"}\n')
            self.assertEqual(stable_generated_at(path), expected)

    def test_fixed_model_matches_compiled_upstream_path(self):
        words = synthetic_hardware_words(0)
        command = [
            "harness/build/fixed/upstream-entropy",
            *(f"0x{word:08x}" for word in words),
        ]
        output = check_output(command, text=True)
        compiled = output.strip().split("sha256_seed_entropy=")[1]
        self.assertEqual(fixed_seed_entropy(words).hex(), compiled)


if __name__ == "__main__":
    unittest.main(verbosity=2)
