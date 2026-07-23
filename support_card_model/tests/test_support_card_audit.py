"""Regression guards for the support-card full-coverage audit.

Covers the three counter-example cards (30161 El Condor Pasa, 30098 Haru
Urara, 30108 Nakayama Festa), B-bonus vs hint-reward isolation, type-41
single-counting, and database-level count invariants.
"""

import importlib.util
import json
import pathlib
import sqlite3
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
MODEL = ROOT / "support_card_model"
SPEC = importlib.util.spec_from_file_location("extract_support_cards", MODEL / "extract_support_card_catalog.py")
EXTRACT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXTRACT)

B_KEYS = ("speed_bonus", "stamina_bonus", "power_bonus", "guts_bonus", "wit_bonus")


class SupportCardAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads((MODEL / "support_card_catalog.json").read_text(encoding="utf-8"))
        cls.by_id = {card["support_card_id"]: card for card in cls.catalog["cards"]}
        cls.db = sqlite3.connect(ROOT / "master.mdb")
        cls.db.row_factory = sqlite3.Row

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    # ---- 30161 El Condor Pasa: three-layer output -----------------------

    def test_30161_three_layers(self):
        card = self.by_id[30161]
        normal = card["uncap_profiles"][4]["effects"]
        self.assertEqual(normal["speed_bonus"], 1)
        self.assertEqual(normal["skill_pt_bonus"], 1)
        unique = card["unique_effect"]
        slot = unique["slots"][0]
        self.assertEqual(slot["type"], 101)
        self.assertEqual(slot["condition"], {"bond_at_least": 100})
        keys = [effect["effect_key"] for effect in slot["effects"]]
        self.assertEqual(keys, ["skill_pt_bonus", "all_stat_bonus"])
        expanded = slot["effects"][1]["expanded_stat_bonuses"]
        self.assertEqual(expanded, {"speed": 1, "stamina": 1, "power": 1, "guts": 1, "wit": 1})
        resolved = card["resolved_effects_when_condition_met"]
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved["condition"], {"bond_at_least": 100})
        self.assertEqual(resolved["sources"]["normal"]["speed_bonus"], 1)
        self.assertEqual(resolved["sources"]["unique"]["speed_bonus"], 1)
        self.assertEqual(resolved["sources"]["unique"]["skill_pt_bonus"], 1)
        self.assertEqual(resolved["effects"]["speed_bonus"], 2)
        self.assertEqual(resolved["effects"]["skill_pt_bonus"], 2)
        for key in B_KEYS:
            self.assertEqual(resolved["effects"][key], 1 if key != "speed_bonus" else 2)
        self.assertTrue(resolved["all_stat_bonus_expanded_in_resolved"])
        self.assertNotIn("all_stat_bonus", resolved["effects"],
                         "type 41 must be counted exactly once in the merged view")

    def test_30161_resolved_view_is_marked_conditional_not_passive(self):
        card = self.by_id[30161]
        resolved = card["resolved_effects_when_condition_met"]
        self.assertEqual(resolved["resolution_status"], "resolved")
        self.assertEqual(resolved["condition_status"], "conditional_not_passive")
        self.assertIn("only when the condition is met", resolved["consumer_warning"])
        # Default (unconditional) panel keeps normal values only.
        self.assertEqual(resolved["default_panel_effects"]["speed_bonus"], 1)
        self.assertEqual(resolved["default_panel_effects"]["skill_pt_bonus"], 1)
        self.assertNotIn("stamina_bonus", resolved["default_panel_effects"])
        normal = card["uncap_profiles"][4]["effects"]
        self.assertEqual(normal["speed_bonus"], 1)
        self.assertEqual(normal["skill_pt_bonus"], 1)

    def test_30137_two_type_101_slots_both_merged(self):
        card = self.by_id[30137]
        slots = [s for s in card["unique_effect"]["slots"] if s["type"] == 101]
        self.assertEqual(len(slots), 2)
        self.assertTrue(all(s["condition"] == {"bond_at_least": 100} for s in slots))
        resolved = card["resolved_effects_when_condition_met"]
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved["resolution_status"], "resolved")
        self.assertEqual(resolved["condition"], {"bond_at_least": 100})
        self.assertEqual(resolved["merged_slot_count"], 2)
        self.assertEqual(resolved["sources"]["unique"],
                         {"friendship_bonus": 10, "motivation_bonus": 15, "skill_pt_bonus": 1})
        self.assertIn("絆ゲージが100以上の時", card["unique_effect"]["description_ja"])

    def test_only_30137_has_multiple_type_101_slots(self):
        db = sqlite3.connect(ROOT / "master.mdb")
        multi = []
        for row in db.execute("SELECT id, type_0, type_1 FROM support_card_unique_effect"):
            count = sum(1 for t in (row[1], row[2]) if t == 101)
            if count > 1:
                multi.append(row[0])
        db.close()
        self.assertEqual(multi, [30137])

    def test_resolved_view_safety_whitelist(self):
        # A type-101 slot whose nested effect is not a direct MDB effect must
        # stay unresolved instead of being merged.
        unique = {"slots": [{"type": 101, "evaluation_status": "numerically_evaluable",
                             "condition": {"bond_at_least": 100},
                             "effects": [{"effect_type": 99, "effect_key": "raw_99", "value": 5}]}]}
        result = EXTRACT.resolved_when_condition_met({"speed_bonus": 1}, unique)
        self.assertEqual(result["resolution_status"], "unresolved")
        self.assertEqual(result["unresolved_reason"], "nested_effect_outside_direct_whitelist")
        # Every generated resolved view in the catalog must pass the whitelist.
        for card in self.catalog["cards"]:
            view = card.get("resolved_effects_when_condition_met")
            if view and view.get("resolution_status") == "resolved":
                for slot in card["unique_effect"]["slots"]:
                    if slot["type"] != 101:
                        continue
                    for effect in slot["effects"]:
                        self.assertIn(effect["effect_type"], EXTRACT.SAFE_RESOLVED_NESTED_TYPES)

    def test_resolved_views_only_for_whitelisted_type_101(self):
        for card in self.catalog["cards"]:
            view = card.get("resolved_effects_when_condition_met")
            if view is None:
                continue
            slots = [s for s in card["unique_effect"]["slots"] if s.get("type") == 101]
            self.assertTrue(slots, f"{card['support_card_id']} resolved view without type 101")
            if view["resolution_status"] == "resolved":
                self.assertEqual(view["condition_status"], "conditional_not_passive")

    def test_30241_type41_counted_once(self):
        card = self.by_id[30241]
        resolved = card["resolved_effects_when_condition_met"]
        self.assertIsNotNone(resolved)
        self.assertNotIn("all_stat_bonus", resolved["effects"])
        for key in B_KEYS:
            self.assertGreaterEqual(resolved["effects"].get(key, 0), 1)

    # ---- 30098 Haru Urara: raw rows vs semantics -------------------------

    def test_30098_direct_unique_skill_pt_saved_independently(self):
        slot = self.by_id[30098]["unique_effect"]["slots"][0]
        self.assertEqual(slot["kind"], "direct")
        self.assertEqual(slot["type"], 30)
        self.assertEqual(slot["effect_key"], "skill_pt_bonus")
        self.assertEqual(slot["value"], 1)
        self.assertEqual(slot["effect"]["display_name_zh"], "技能Pt加成")

    def test_30098_hint_reward_rows(self):
        rewards = self.by_id[30098]["hint_effects"]["hint_event_parameter_rewards"]
        normal = rewards["normal_parameter_reward_rows"]
        conditional = rewards["conditional_parameter_reward_rows"]
        normal_pairs = {(row["hint_value_1"], row["hint_value_2"]) for row in normal}
        self.assertIn((2, 2), normal_pairs)
        self.assertIn((3, 6), normal_pairs)
        self.assertEqual(len(conditional), 3)
        self.assertTrue(all(row["condition_set_id"] == 830098 for row in conditional))
        conditional_pairs = {(row["hint_value_1"], row["hint_value_2"]) for row in conditional}
        self.assertEqual(conditional_pairs, {(2, 4), (3, 12), (30, 2)})
        self.assertEqual(rewards["selection_semantics"], "unknown")
        for row in normal + conditional:
            self.assertEqual(row["effect_category"], "hint_event_reward")
            self.assertIn("Hint事件", row["display_name_zh"])

    def test_30098_hint_rewards_never_enter_b_fields(self):
        card = self.by_id[30098]
        # Per-profile, per-key: every uncap profile is checked independently.
        for profile in card["uncap_profiles"]:
            for key in B_KEYS:
                self.assertNotIn(key, profile["effects"],
                                 f"uncap {profile['uncap']}: hint rewards must not leak into B field {key}")
        for state in card["level_breakpoints"]:
            for key in B_KEYS:
                self.assertNotIn(key, state["effects"],
                                 f"level {state['level']}: hint rewards must not leak into B field {key}")
        normal_effects_text = json.dumps(card["uncap_profiles"], ensure_ascii=False)
        self.assertNotIn("Hint事件", normal_effects_text)

    # ---- 30108 Nakayama Festa: safe type-112 output ----------------------

    def test_30108_type_112_safe_output(self):
        card = self.by_id[30108]
        self.assertEqual(card["rarity_name"], "SSR")
        self.assertEqual(card["training_type"], "wit")
        slot = card["unique_effect"]["slots"][0]
        self.assertEqual(slot["type"], 112)
        self.assertEqual(slot["action"], "set_failure_rate_zero")
        self.assertEqual(slot["activation_scope"], "training_joined_by_this_card")
        self.assertEqual(slot["value_raw"], 20)
        self.assertIsNone(slot["probability"])
        self.assertEqual(slot["probability_status"], "unknown")
        self.assertEqual(slot["timing_status"], "unknown")
        self.assertNotIn("probability_percent", json.dumps(slot))
        self.assertIn("失敗率が0%になることがある", card["unique_effect"]["description_ja"])

    # ---- nested type 33 hint-count bonus ---------------------------------

    def test_nested_type_33_hint_count_bonus(self):
        for cid in (30283, 30289, 30298):
            slot = self.by_id[cid]["unique_effect"]["slots"][0]
            self.assertEqual(slot["type"], 101)
            nested = slot["effects"][-1]
            self.assertEqual(nested["effect_type"], 33)
            self.assertEqual(nested["effect_key"], "hint_count_bonus")
            self.assertEqual(nested["display_name_zh"], "Hint获取数加成")

    # ---- database-level invariants ---------------------------------------

    def test_hint_gain_database_counts(self):
        db = self.db
        total = db.execute("SELECT COUNT(*) FROM single_mode_hint_gain").fetchone()[0]
        self.assertEqual(total, 4919)
        cards = db.execute("SELECT COUNT(DISTINCT support_card_id) FROM single_mode_hint_gain").fetchone()[0]
        self.assertEqual(cards, 513)
        dist = dict(db.execute("SELECT hint_gain_type, COUNT(*) FROM single_mode_hint_gain GROUP BY hint_gain_type"))
        self.assertEqual(dist, {0: 3784, 1: 1135})
        cond_rows = db.execute("SELECT COUNT(*) FROM single_mode_hint_gain WHERE condition_set_id<>0").fetchone()[0]
        cond_cards = db.execute("SELECT COUNT(DISTINCT support_card_id) FROM single_mode_hint_gain WHERE condition_set_id<>0").fetchone()[0]
        cond_sets = db.execute("SELECT COUNT(DISTINCT condition_set_id) FROM single_mode_hint_gain WHERE condition_set_id<>0").fetchone()[0]
        self.assertEqual((cond_rows, cond_cards, cond_sets), (3, 1, 1))
        no_hint = db.execute("""SELECT support_card_type, COUNT(*) FROM support_card_data
            WHERE id NOT IN (SELECT DISTINCT support_card_id FROM single_mode_hint_gain)
            GROUP BY support_card_type""").fetchall()
        self.assertEqual({row[0]: row[1] for row in no_hint}, {2: 23, 3: 5})

    def test_effect_table_has_no_type_33_or_41_normal_rows(self):
        types = {row[0] for row in self.db.execute("SELECT DISTINCT type FROM support_card_effect_table")}
        self.assertNotIn(33, types)
        self.assertNotIn(41, types)

    # ---- consumer compatibility ------------------------------------------

    def test_machine_keys_unchanged_for_consumers(self):
        card = self.by_id[30001]
        effects = card["uncap_profiles"][4]["effects"]
        for key in ("friendship_bonus", "motivation_bonus", "training_bonus"):
            self.assertIn(key, effects)
        self.assertEqual(self.catalog["effect_types"]["3"]["key"], "speed_bonus")
        self.assertEqual(self.catalog["effect_types"]["41"]["key"], "all_stat_bonus")


if __name__ == "__main__":
    unittest.main()
