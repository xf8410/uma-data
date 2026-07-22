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
        result_context = {"_effect_type": effect_type}
        return result, result_context

    def test_all_complex_types_are_declared(self):
        self.assertEqual(set(DECODER.COMPLEX_UNIQUE_DEFINITIONS), set(range(101, 123)))
        self.assertEqual(DECODER.COMPLEX_UNIQUE_DEFINITIONS[107]["status"], "candidate_formula")

    def test_type_101_bond_threshold_two_effects(self):
        decoded, context = self.decode(101, [80, 3, 1, 30, 1])
        context["bond"] = 80
        result = DECODER.evaluate_decoded(decoded, context)
        self.assertEqual(result["effects"], {"speed_bonus": 1, "skill_pt_bonus": 1})
        context["bond"] = 79
        self.assertEqual(DECODER.evaluate_decoded(decoded, context)["effects"], {})

    def test_training_bonus_scalers(self):
        cases = [
            (103, [4, 10, 0, 0, 0], {"distinct_deck_types": 4}, 10),
            (104, [10000, 20, 0, 0, 0], {"fan_count": 155000}, 15),
            (109, [8, 30, 0, 0, 0], {"total_deck_bond": 299}, 9),
            (110, [8, 5, 0, 0, 0], {"training_support_count": 4}, 20),
            (111, [8, 5, 0, 0, 0], {"training_level": 7}, 25),
            (117, [8, 25, 20, 0, 0], {"total_training_level": 27}, 20),
        ]
        for effect_type, values, extra, expected in cases:
            decoded, context = self.decode(effect_type, values)
            context.update(extra)
            result = DECODER.evaluate_decoded(decoded, context)
            self.assertEqual(result["effects"]["training_bonus"], expected, effect_type)

    def test_friendship_training_and_skill_count(self):
        decoded, context = self.decode(113, [2, 60, 0, 0, 0])
        context["friendship_training"] = True
        self.assertEqual(DECODER.evaluate_decoded(decoded, context)["effects"]["motivation_bonus"], 60)
        decoded, context = self.decode(116, [3, 4, 1, 3, 0])
        context["skill_counts"] = {"recovery": 7}
        self.assertEqual(DECODER.evaluate_decoded(decoded, context)["effects"]["stamina_bonus"], 3)

    def test_deck_initial_and_parameter_bonuses(self):
        decoded, context = self.decode(105, [10, 2, 0, 0, 0])
        context["deck_counts"] = {"speed": 2, "friend": 1}
        stats = DECODER.evaluate_decoded(decoded, context)["actions"]["initial_stats"]
        self.assertEqual(stats, {"speed": 22, "stamina": 2, "power": 2, "guts": 2, "wit": 2})
        decoded, context = self.decode(120, [1, 80, 1, 2, 0])
        context.update(bond=80, deck_counts={"speed": 3, "guts": 1, "friend": 1})
        actions = DECODER.evaluate_decoded(decoded, context)["actions"]
        self.assertEqual(actions["parameter_bonuses"]["speed"], 2)
        self.assertEqual(actions["parameter_bonuses"]["guts"], 1)
        self.assertEqual(actions["skill_pt_bonus"], 1)

    def test_state_actions_118_to_122(self):
        decoded, context = self.decode(118, [1, 60, 0, 0, 0]); context["bond"] = 60
        self.assertTrue(DECODER.evaluate_decoded(decoded, context)["actions"]["second_training_position"])
        decoded, context = self.decode(119, [50, 1, 60, 0, 0]); context["bond"] = 60
        self.assertEqual(DECODER.evaluate_decoded(decoded, context)["actions"]["position_rate_bonus"], 50)
        decoded, context = self.decode(121, [1, 2, 0, 0, 0])
        self.assertEqual(DECODER.evaluate_decoded(decoded, context)["actions"]["bond_gain_if_present"], 2)
        decoded, context = self.decode(122, [19, 60, 0, 0, 0])
        action = DECODER.evaluate_decoded(decoded, context)["actions"]["next_turn_other_support_effect"]
        self.assertEqual((action["effect_key"], action["value"]), ("specialty_rate", 60))

    def test_type_107_is_not_presented_as_confirmed(self):
        decoded, context = self.decode(107, [1, 10, 30, 15, 5])
        self.assertEqual(decoded["status"], "candidate_formula")
        self.assertIn("todo", decoded["formula_status"].lower())
        context["current_vital"] = 30
        result = DECODER.evaluate_decoded(decoded, context)
        self.assertEqual(result["actions"]["formula_status"], "candidate")


if __name__ == "__main__":
    unittest.main()
