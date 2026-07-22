import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
MODEL = ROOT / "support_card_model"
SPEC = importlib.util.spec_from_file_location("extract_support_cards", MODEL / "extract_support_card_catalog.py")
EXTRACT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXTRACT)


class SupportCardCatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = EXTRACT.build_catalog(ROOT / "master.mdb")
        cls.committed = json.loads((MODEL / "support_card_catalog.json").read_text(encoding="utf-8"))
        cls.by_id = {card["support_card_id"]: card for card in cls.catalog["cards"]}

    def test_committed_catalog_is_reproducible(self):
        self.assertEqual(self.catalog, self.committed)

    def test_all_cards_and_effect_tables_are_covered(self):
        self.assertEqual(self.catalog["card_count"], 541)
        self.assertEqual(len(self.by_id), 541)
        self.assertTrue(all(len(card["uncap_profiles"]) == 5 for card in self.catalog["cards"]))

    def test_r_sr_ssr_max_levels(self):
        self.assertEqual([p["max_level"] for p in self.by_id[10001]["uncap_profiles"]],
                         [20, 25, 30, 35, 40])
        self.assertEqual([p["max_level"] for p in self.by_id[20001]["uncap_profiles"]],
                         [25, 30, 35, 40, 45])
        self.assertEqual([p["max_level"] for p in self.by_id[30001]["uncap_profiles"]],
                         [30, 35, 40, 45, 50])

    def test_latest_non_negative_level_value_is_used(self):
        card = self.by_id[30001]
        self.assertEqual(card["uncap_profiles"][0]["effects"]["friendship_bonus"], 15)
        self.assertEqual(card["uncap_profiles"][4]["effects"]["friendship_bonus"], 20)
        self.assertEqual(card["uncap_profiles"][4]["effects"]["motivation_bonus"], 60)
        self.assertEqual(card["uncap_profiles"][4]["effects"]["training_bonus"], 10)

    def test_training_friend_and_group_types_are_scenario_neutral(self):
        self.assertEqual(self.by_id[30001]["support_card_type_name"], "training")
        self.assertEqual(self.by_id[30001]["training_type"], "guts")
        self.assertEqual(self.by_id[30160]["support_card_type_name"], "friend")
        self.assertIsNone(self.by_id[30160]["training_type"])

    def test_simple_unique_effect_is_mapped(self):
        unique = self.by_id[30001]["unique_effect"]
        self.assertTrue(unique["fully_resolved"])
        self.assertEqual(unique["slots"][0]["effect_key"], "guts_bonus")
        self.assertEqual(unique["slots"][1]["effect_key"], "initial_guts")

    def test_complex_unique_effect_remains_raw(self):
        unique = self.by_id[30160]["unique_effect"]
        self.assertFalse(unique["fully_resolved"])
        self.assertEqual(unique["slots"][0]["type"], 118)
        self.assertEqual(unique["slots"][0]["status"], "condition_or_complex_effect_unresolved")
        self.assertEqual(unique["raw"]["value_0_1"], 60)

    def test_effect_type_names_come_from_mdb(self):
        self.assertEqual(self.catalog["effect_types"]["1"]["name_ja"], "友情ボーナス")
        self.assertEqual(self.catalog["effect_types"]["31"]["key"], "wit_recovery")

    def test_cook_verified_cards_match_generic_catalog(self):
        verified = json.loads((ROOT / "scenario_08_cook_model" / "support_candidates.json")
                              .read_text(encoding="utf-8"))["cards"]
        for card_id, expected in verified.items():
            actual = self.by_id[int(card_id)]["uncap_profiles"][4]["effects"]
            for key, value in expected["lv50_effects"].items():
                self.assertEqual(actual.get(key), value, f"{card_id} {key}")


if __name__ == "__main__":
    unittest.main()
