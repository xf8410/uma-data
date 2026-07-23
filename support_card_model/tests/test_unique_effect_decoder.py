import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
MODEL = ROOT / "support_card_model"
SPEC = importlib.util.spec_from_file_location("unique_effect_decoder", MODEL / "unique_effect_decoder.py")
DECODER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DECODER)


class UniqueEffectDecoderTest(unittest.TestCase):
    def decode(self, effect_type, values):
        result = DECODER.decode_unique_slot(effect_type, values)
        return result, {"_effect_type": effect_type}

    def test_all_complex_types_are_declared(self):
        self.assertEqual(set(DECODER.COMPLEX_UNIQUE_DEFINITIONS), set(range(101, 123)))
        numeric = {t for t, d in DECODER.COMPLEX_UNIQUE_DEFINITIONS.items()
                   if d["evaluation"] == "numeric"}
        action_only = {t for t, d in DECODER.COMPLEX_UNIQUE_DEFINITIONS.items()
                       if d["evaluation"] == "action_only"}
        self.assertEqual(numeric, {101, 113, 115})
        self.assertEqual(action_only, {112, 118})

    def test_direct_effect_keeps_stable_key_and_metadata(self):
        decoded, _ = self.decode(3, [1, 0, 0, 0, 0])
        self.assertEqual(decoded["effect_key"], "speed_bonus")
        self.assertEqual(decoded["effect"]["effect_category"], "training_stat_bonus")
        self.assertEqual(decoded["effect"]["target"], "speed")
        self.assertEqual(decoded["effect"]["display_name_zh"], "速度加成")

    def test_type_30_is_independent_skill_pt_bonus(self):
        decoded, _ = self.decode(30, [1, 0, 0, 0, 0])
        self.assertEqual(decoded["effect_key"], "skill_pt_bonus")
        self.assertEqual(decoded["effect"]["effect_category"], "skill_pt_bonus")
        self.assertEqual(decoded["effect"]["display_name_zh"], "技能Pt加成")

    def test_type_41_keeps_raw_and_read_only_expansion(self):
        decoded, _ = self.decode(41, [1, 0, 0, 0, 0])
        effect = decoded["effect"]
        self.assertEqual(effect["effect_key"], "all_stat_bonus")
        self.assertEqual(effect["value"], 1)
        self.assertEqual(effect["expanded_stat_bonuses"],
                         {"speed": 1, "stamina": 1, "power": 1, "guts": 1, "wit": 1})
        self.assertTrue(effect["expanded_is_derived_view"])

    def test_type_41_evaluation_applies_raw_only_never_both(self):
        decoded, context = self.decode(101, [100, 30, 1, 41, 1])
        context["bond"] = 100
        result = DECODER.evaluate_decoded(decoded, context)
        self.assertEqual(result["effects"], {"skill_pt_bonus": 1, "all_stat_bonus": 1})
        for key in ("speed_bonus", "stamina_bonus", "power_bonus", "guts_bonus", "wit_bonus"):
            self.assertNotIn(key, result["effects"], "type 41 must not be double-counted via expansion")

    def test_type_101_bond_threshold(self):
        decoded, context = self.decode(101, [80, 3, 1, 0, 0])
        context["bond"] = 80
        self.assertEqual(DECODER.evaluate_decoded(decoded, context)["effects"], {"speed_bonus": 1})
        context["bond"] = 79
        self.assertEqual(DECODER.evaluate_decoded(decoded, context)["effects"], {})

    def test_type_112_safe_output(self):
        decoded, context = self.decode(112, [20, 0, 0, 0, 0])
        self.assertEqual(decoded["action"], "set_failure_rate_zero")
        self.assertEqual(decoded["activation_scope"], "training_joined_by_this_card")
        self.assertEqual(decoded["value_raw"], 20)
        self.assertIsNone(decoded["probability"])
        self.assertEqual(decoded["probability_status"], "unknown")
        self.assertIsNone(decoded["timing"])
        self.assertEqual(decoded["timing_status"], "unknown")
        self.assertNotIn("probability_percent", decoded)
        result = DECODER.evaluate_decoded(decoded, context)
        # 112 must never decide triggering or set an actual failure rate.
        self.assertEqual(result["evaluation_status"], "action_only_not_numerically_evaluable")
        self.assertEqual(result["effects"], {})
        action = result["actions"]["failure_rate_zero"]
        self.assertEqual(action["value_raw"], 20)
        self.assertEqual(action["probability_status"], "unknown")
        self.assertIsNone(action["probability"])
        self.assertNotIn("probability_percent", action)
        self.assertNotIn("triggered", action)

    def test_structural_types_113_115_118(self):
        decoded, context = self.decode(113, [2, 60, 0, 0, 0])
        context["friendship_training"] = True
        self.assertEqual(DECODER.evaluate_decoded(decoded, context)["effects"], {"motivation_bonus": 60})
        decoded, context = self.decode(115, [9, 10, 0, 0, 0])
        self.assertEqual(DECODER.evaluate_decoded(decoded, context)["actions"]["all_cards_initial_effect"]["effect_key"], "initial_speed")
        decoded, context = self.decode(118, [1, 60, 0, 0, 0])
        self.assertEqual(decoded["deterministic_part"], "bond_threshold_met")
        self.assertEqual(decoded["candidate_capability_when_condition_met"],
                         {"action": "allow_second_training_position", "max_positions": 2})
        self.assertEqual(decoded["runtime_result_status"], "unknown")
        self.assertEqual(decoded["position_selection_probability_status"], "unknown")
        self.assertEqual(decoded["position_selection_process_status"], "unknown")
        self.assertNotIn("allow_second_training_position",
                         {k: v for k, v in decoded.items() if k != "candidate_capability_when_condition_met"})
        context["bond"] = 60
        result = DECODER.evaluate_decoded(decoded, context)
        self.assertEqual(result["evaluation_status"], "action_only_not_numerically_evaluable")
        self.assertEqual(result["effects"], {})
        self.assertTrue(result["actions"]["bond_threshold_met"])
        self.assertEqual(result["actions"]["candidate_capability"],
                         {"action": "allow_second_training_position", "max_positions": 2})
        self.assertEqual(result["actions"]["runtime_result_status"], "unknown")
        self.assertEqual(result["actions"]["position_selection_probability_status"], "unknown")
        context["bond"] = 59
        below = DECODER.evaluate_decoded(decoded, context)
        self.assertFalse(below["actions"]["bond_threshold_met"])
        self.assertNotIn("candidate_capability", below["actions"])

    def test_unknown_formula_types_return_explicit_unknown_never_zero(self):
        for effect_type, values in [
            (102, [80, 10, 0, 0, 0]), (103, [4, 10, 0, 0, 0]),
            (104, [10000, 20, 0, 0, 0]), (105, [10, 2, 0, 0, 0]),
            (106, [5, 8, 2, 0, 0]), (107, [1, 10, 30, 15, 5]),
            (108, [8, 30, 5, 10, 20]), (109, [8, 30, 0, 0, 0]),
            (110, [8, 5, 0, 0, 0]), (111, [8, 5, 0, 0, 0]),
            (114, [1, 10, 15, 0, 0]), (116, [3, 4, 1, 3, 0]),
            (117, [8, 25, 20, 0, 0]), (119, [50, 1, 60, 0, 0]),
            (120, [1, 80, 1, 2, 0]), (121, [1, 2, 0, 0, 0]),
            (122, [19, 60, 0, 0, 0]),
        ]:
            decoded, context = self.decode(effect_type, values)
            self.assertEqual(decoded["evaluation_status"], "unknown", effect_type)
            self.assertEqual(decoded["unresolved_reason"], DECODER.UNKNOWN_REASON)
            context.update(bond=100, friendship_training=True, fan_count=10**9,
                           distinct_deck_types=6, total_deck_bond=600,
                           training_support_count=5, training_level=5,
                           current_vital=100, max_vital=100,
                           skill_counts={"recovery": 9}, deck_counts={"speed": 6},
                           total_training_level=25)
            result = DECODER.evaluate_decoded(decoded, context)
            self.assertEqual(result["evaluation_status"], "unknown", effect_type)
            self.assertEqual(result["effects"], {}, f"type {effect_type} must not evaluate to numbers")
            self.assertEqual(result["actions"], {}, f"type {effect_type} must not produce actions")

    def test_evaluate_decoded_result_schema_is_uniform(self):
        cases = [
            (3, [1, 0, 0, 0, 0]), (30, [1, 0, 0, 0, 0]), (41, [1, 0, 0, 0, 0]),
            (101, [100, 30, 1, 41, 1]), (104, [10000, 20, 0, 0, 0]),
            (107, [1, 10, 30, 15, 5]), (112, [20, 0, 0, 0, 0]),
            (113, [2, 60, 0, 0, 0]), (115, [9, 10, 0, 0, 0]),
            (118, [1, 60, 0, 0, 0]), (122, [19, 60, 0, 0, 0]),
        ]
        valid_statuses = {"numerically_evaluable",
                          "action_only_not_numerically_evaluable", "unknown"}
        for effect_type, values in cases:
            decoded, context = self.decode(effect_type, values)
            context.update(bond=100, friendship_training=True)
            result = DECODER.evaluate_decoded(decoded, context)
            self.assertEqual(set(result), {"evaluation_status", "unresolved_reason",
                                           "effects", "actions"}, effect_type)
            if result["evaluation_status"] == "unknown":
                self.assertEqual(result["unresolved_reason"], DECODER.UNKNOWN_REASON)
            else:
                self.assertIsNone(result["unresolved_reason"])
            self.assertIn(result["evaluation_status"], valid_statuses, effect_type)
            self.assertIsInstance(result["effects"], dict)
            self.assertIsInstance(result["actions"], dict)
            for key, value in result["effects"].items():
                self.assertIsInstance(key, str)
                self.assertIsInstance(value, int)
                self.assertNotEqual(value, 0, f"type {effect_type}: unknown must not become 0")

    def test_no_external_formula_artifacts_remain(self):
        import inspect
        source = inspect.getsource(DECODER)
        for banned in ("umasim", "UmaAI", "BWIKI", "candidate_formula", "probability_percent"):
            self.assertNotIn(banned, source)


if __name__ == "__main__":
    unittest.main()
