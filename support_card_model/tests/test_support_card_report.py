import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
MODEL = ROOT / "support_card_model"
SPEC = importlib.util.spec_from_file_location("support_report", MODEL / "build_support_card_report.py")
REPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPORT)


class SupportCardReportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        catalog = json.loads((MODEL / "support_card_catalog.json").read_text(encoding="utf-8"))
        cls.report = REPORT.build_report(catalog)
        cls.committed = json.loads((MODEL / "support_card_effect_report.json").read_text(encoding="utf-8"))
        cls.by_id = {card["support_card_id"]: card for card in cls.report["cards"]}

    def test_report_is_reproducible_and_has_every_card(self):
        self.assertEqual(self.report, self.committed)
        self.assertEqual(self.report["card_count"], 541)
        self.assertEqual(len(self.by_id), 541)
        self.assertEqual(self.report["coverage"]["cards_with_normal_effect_table"], 541)

    def test_every_unique_has_official_description_and_raw(self):
        unique_cards = [card for card in self.report["cards"] if card["unique_effect"]]
        self.assertEqual(len(unique_cards), 399)
        self.assertTrue(all(card["unique_effect"]["description_ja"] for card in unique_cards))
        self.assertTrue(all(card["unique_effect"]["raw"] for card in unique_cards))

    def test_report_never_claims_fully_resolved(self):
        raw = json.dumps(self.report, ensure_ascii=False)
        self.assertNotIn("fully_resolved", raw)
        evaluation = self.report["coverage"]["unique_slot_evaluation"]
        self.assertEqual(evaluation["non_empty_slots"], 573)
        self.assertEqual(evaluation["structurally_decoded_slots"], 532)
        self.assertEqual(evaluation["numerically_evaluable_slots"], 530)
        self.assertEqual(evaluation["action_only_not_numerically_evaluable_slots"], 2)
        self.assertEqual(evaluation["action_only_type_distribution"], {"112": 1, "118": 1})
        self.assertEqual(
            evaluation["numerically_evaluable_slots"]
            + evaluation["action_only_not_numerically_evaluable_slots"],
            evaluation["structurally_decoded_slots"])
        self.assertIn("unknown_formula", evaluation["definitions"])
        self.assertEqual(evaluation["unknown_formula_slots"], 41)
        self.assertEqual(evaluation["structurally_decoded_slots"] + evaluation["unknown_formula_slots"],
                         evaluation["non_empty_slots"])
        self.assertGreater(evaluation["unknown_formula_slots"], 0)
        self.assertTrue(all(item["unresolved_reason"] for item in evaluation["unknown_detail"]))

    def test_coverage_matrix_boundaries(self):
        matrix = self.report["coverage"]["coverage_matrix"]
        self.assertEqual(matrix["support_card_events"]["coverage"], "unknown")
        self.assertEqual(matrix["support_card_group"]["coverage"], "raw_membership_only")
        self.assertEqual(matrix["friend_and_group_card_behaviors"]["coverage"], "unknown")
        self.assertEqual(matrix["support_card_team_score_bonus"]["coverage"], "raw_only")
        self.assertEqual(matrix["scenario_specific_effects"]["coverage"], "excluded")

    def test_card_report_has_all_uncap_profiles_and_breakpoints(self):
        card = self.by_id[30001]
        self.assertEqual(len(card["normal_effect_profiles"]), 5)
        self.assertEqual(card["normal_effect_profiles"][-1]["effects"]["training_bonus"], 10)
        self.assertGreaterEqual(len(card["level_breakpoints"]), 10)
        self.assertIn("絆ゲージ", self.by_id[30160]["unique_effect"]["description_ja"])

    def test_naming_blacklist(self):
        raw = json.dumps(self.report, ensure_ascii=False)
        for banned in ("基础加成", "属性直接+1", "B95", "probability_percent",
                       "umasim", "UmaAI", "BWIKI", "candidate_formula"):
            self.assertNotIn(banned, raw)


if __name__ == "__main__":
    unittest.main()
