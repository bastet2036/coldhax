#!/usr/bin/env python3
"""Validation tests for public incident accounting."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INCIDENTS = ROOT / "evidence" / "public-incidents.json"


class PublicIncidentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = json.loads(INCIDENTS.read_text())

    def test_latest_total_is_cumulative_not_additive(self) -> None:
        rows = self.data["reported_aggregate"]
        self.assertEqual(
            [row["id"] for row in rows],
            [
                "galaxy-wave-1",
                "galaxy-waves-1-2-cumulative",
                "galaxy-waves-1-3-cumulative",
            ],
        )
        self.assertEqual(rows[-1]["reported_unauthorized_spend_btc"], 1367.05)
        self.assertEqual(rows[-1]["reported_source_addresses"], 4585)
        self.assertIn("must not be summed", rows[-1]["basis"])

    def test_balances_are_timestamped_and_separate(self) -> None:
        self.assertRegex(
            self.data["onchain_observed_at_utc"],
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$",
        )
        observations = self.data["destination_balance_observations"]
        self.assertEqual(len(observations), 9)
        self.assertEqual(len({row["address"] for row in observations}), 9)
        for row in observations:
            self.assertIsInstance(row["current_balance_sats"], int)
            self.assertGreaterEqual(row["current_balance_sats"], 0)

    def test_owner_case_does_not_double_count_consolidation(self) -> None:
        erik = next(
            row
            for row in self.data["public_owner_or_witness_reports"]
            if row["id"] == "erik-mk3-testing-wallet"
        )
        self.assertEqual(erik["owner_reported_amount_sats"], 9000)
        self.assertIn("subset", erik["double_counting_note"])
        self.assertEqual(
            erik["attributed_exploitation"],
            "suspected_not_computationally_confirmed",
        )

    def test_representative_transactions_are_unique_and_labeled(self) -> None:
        transactions = self.data["representative_onchain_transactions"]
        self.assertEqual(len(transactions), 5)
        self.assertEqual(
            len({row["transaction_id"] for row in transactions}),
            len(transactions),
        )
        for row in transactions:
            self.assertEqual(len(row["transaction_id"]), 64)
            self.assertGreater(row["received_sats"], 0)
            self.assertIn("role", row)

    def test_emerging_wave_fails_closed(self) -> None:
        emerging = self.data["emerging_unincluded_report"]
        self.assertEqual(
            emerging["classification"],
            "potential_not_included_in_verified_cumulative_total",
        )
        self.assertIn("did not independently reproduce", emerging["reason"])

    def test_public_artifacts_contain_no_obvious_secret_material(self) -> None:
        patterns = (
            r"\b(?:xprv|yprv|zprv|tprv)[1-9A-HJ-NP-Za-km-z]+",
            r"(?i)seed phrase\s*[:=]\s*(?:[a-z]+\s+){11,23}[a-z]+",
            r"(?i)private key\s*[:=]\s*[0-9a-f]{64}",
        )
        for relative in ("PUBLIC_INCIDENTS.md", "evidence/public-incidents.json"):
            text = (ROOT / relative).read_text()
            for pattern in patterns:
                self.assertIsNone(re.search(pattern, text), (relative, pattern))


if __name__ == "__main__":
    unittest.main()
