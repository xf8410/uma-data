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

    def test_only_explicit_candidate_remains(self):
        self.assertEqual(self.report["coverage"]["non_confirmed_unique_slots"], [
            {"support_card_id": 30094, "type": 107, "status": "candidate_formula"}
        ])

    def test_card_report_has_all_uncap_profiles_and_breakpoints(self):
        card = self.by_id[30001]
        self.assertEqual(len(card["normal_effect_profiles"]), 5)
        self.assertEqual(card["normal_effect_profiles"][-1]["effects"]["training_bonus"], 10)
        self.assertGreaterEqual(len(card["level_breakpoints"]), 10)
        self.assertIn("絆ゲージ", self.by_id[30160]["unique_effect"]["description_ja"])


if __name__ == "__main__":
    unittest.main()
