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
        self.assertEqual(len(observations), 22)
        self.assertEqual(len({row["address"] for row in observations}), 22)
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

    def test_goodman_exact_owner_amount_fails_closed_without_txids(self) -> None:
        goodman = next(
            row
            for row in self.data["public_owner_or_witness_reports"]
            if row["id"] == "goodman-three-coldcard-wallets"
        )
        self.assertEqual(goodman["owner_reported_amount_btc"], 18.25245043)
        self.assertEqual(goodman["transaction_ids"], [])
        self.assertEqual(goodman["public_source_addresses"], [])
        self.assertIsNone(goodman["spend_window_timezone"])
        self.assertIn("Do not add", goodman["double_counting_note"])

    def test_lamb_mk3_owner_amount_fails_closed_without_txids(self) -> None:
        lamb = next(
            row
            for row in self.data["public_owner_or_witness_reports"]
            if row["id"] == "lamb-mk3-two-bitcoin"
        )
        self.assertEqual(lamb["model"], "Mk3")
        self.assertEqual(lamb["owner_reported_amount_btc"], 2.0)
        self.assertEqual(lamb["transaction_ids"], [])
        self.assertEqual(lamb["public_source_addresses"], [])
        self.assertIsNone(lamb["generation_firmware"])
        self.assertIn("Do not add", lamb["double_counting_note"])

    def test_thorn_approximate_case_fails_closed_without_identifiers(self) -> None:
        thorn = next(
            row
            for row in self.data["public_owner_or_witness_reports"]
            if row["id"] == "thorn-nearly-thirty-bitcoin-coldcard-victim"
        )
        self.assertEqual(thorn["analyst_reported_victim_stack_btc_approx"], 30)
        self.assertEqual(thorn["analyst_reported_peeled_btc_approx"], 17)
        self.assertEqual(thorn["transaction_ids"], [])
        self.assertEqual(thorn["public_source_addresses"], [])
        self.assertIn("Do not add", thorn["double_counting_note"])

    def test_chainabuse_mk3_owner_loss_binds_to_wave3_without_double_counting(self) -> None:
        case = next(
            row
            for row in self.data["public_owner_or_witness_reports"]
            if row["id"] == "chainabuse-mk3-5.39099821-bitcoin"
        )
        self.assertEqual(case["owner_reported_amount_btc"], 5.39099821)
        self.assertEqual(case["initial_destination_received_sats"], 539099821)
        self.assertEqual(case["later_hop_fee_sats"], 1220)
        self.assertEqual(case["current_destination_received_sats"], 539098601)
        self.assertIn("not an additional loss", case["double_counting_note"])
        self.assertIn("Do not add", case["double_counting_note"])

    def test_chainabuse_p2tr_owner_amount_is_limited_to_identified_transactions(self) -> None:
        case = next(
            row
            for row in self.data["public_owner_or_witness_reports"]
            if row["id"] == "chainabuse-p2tr-three-transactions"
        )
        self.assertEqual(len(case["transaction_ids"]), 3)
        self.assertEqual(len(case["public_source_addresses"]), 3)
        self.assertEqual(case["owner_identified_destination_receipts_sats"], 17998515)
        self.assertEqual(case["owner_identified_source_inputs_sats"], 18000330)
        self.assertEqual(case["owner_identified_transaction_fees_sats"], 1815)
        self.assertEqual(case["destination_total_received_sats"], 50992489)
        self.assertIn("Only the three owner-identified", case["double_counting_note"])

    def test_p2tr_community_sample_is_not_promoted_to_a_full_wave(self) -> None:
        sample = self.data["community_reconstructed_clusters"][0]
        self.assertEqual(sample["id"], "kelbie-p2tr-sample")
        self.assertEqual(sample["reported_destinations"], 3)
        self.assertEqual(sum(sample["destination_receipts_sats"]), 4697389047)
        self.assertEqual(sample["sample_total_received_sats"], 4697389047)
        self.assertIn("not a complete wave census", sample["limitation"])
        self.assertIn("must not be added", sample["limitation"])

    def test_representative_transactions_are_unique_and_labeled(self) -> None:
        transactions = self.data["representative_onchain_transactions"]
        self.assertEqual(len(transactions), 9)
        self.assertEqual(
            len({row["transaction_id"] for row in transactions}),
            len(transactions),
        )
        for row in transactions:
            self.assertEqual(len(row["transaction_id"]), 64)
            self.assertGreater(row["received_sats"], 0)
            self.assertIn("role", row)

    def test_later_hops_are_not_counted_as_new_losses(self) -> None:
        rows = self.data["later_hop_observations"]
        self.assertEqual(len(rows), 3)
        wave4_rows = [
            row
            for row in rows
            if row["source_cluster"] == "potential-wave-4-community-reconstruction"
        ]
        self.assertEqual(sum(row["source_input_sats"] for row in wave4_rows), 561303754)
        self.assertEqual(len({row["transaction_id"] for row in rows}), 3)
        for row in rows:
            self.assertEqual(row["classification"], "later_hop_not_additional_loss")
            self.assertEqual(len(row["transaction_id"]), 64)
            self.assertGreater(row["source_input_sats"], 0)

    def test_post_mix_downstream_movement_is_not_source_attributed(self) -> None:
        rows = self.data["unassigned_downstream_observations"]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(
            row["classification"],
            "not_source_attributable_after_mixed_transaction",
        )
        self.assertEqual(row["immediate_source_input_sats"], 47797906)
        self.assertEqual(row["upstream_mixed_transaction_input_count"], 34)
        self.assertIn("not added", row["note"])

    def test_emerging_wave_fails_closed(self) -> None:
        emerging = self.data["emerging_unincluded_report"]
        self.assertEqual(
            emerging["classification"],
            "potential_not_included_in_verified_cumulative_total",
        )
        self.assertIn("did not independently reproduce", emerging["reason"])
        self.assertEqual(emerging["primary_reported_surviving_core_addresses"], 709)
        self.assertEqual(emerging["primary_reported_surviving_core_btc"], 448.73)
        self.assertIn("do not reconcile", emerging["arithmetic_limitation"])
        self.assertIn("no direct victim", emerging["victim_confirmation"])
        self.assertEqual(emerging["secondary_reconstruction"]["derived_btc"], 443.34)

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
