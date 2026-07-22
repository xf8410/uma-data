import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "training_effect_candidates", ROOT / "training_effect_candidates.py")
CANDIDATES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CANDIDATES)


class TrainingEffectCandidatesTest(unittest.TestCase):
    def test_umaai_baseline_multiplier(self):
        sample = {
            "head_count": 2,
            "motivation": 5,
            "motivation_bonus": 20,
        }
        multiplier = CANDIDATES.umaai_card_multiplier(sample, 10, 1.3)
        expected = 1.10 * 1.10 * (1.0 + 0.2 * 1.20) * 1.3
        self.assertAlmostEqual(multiplier, expected)

    def test_ramen_friendship_is_inactive_without_shining_card(self):
        self.assertEqual(
            CANDIDATES.friendship_candidates([], 45),
            {"none": 1.0},
        )

    def test_one_shining_card_distinguishes_friendship_candidates(self):
        result = CANDIDATES.friendship_candidates([30], 30)
        self.assertAlmostEqual(result["scenario_once"], 1.30 * 1.30)
        self.assertAlmostEqual(result["add_to_each_shining_card"], 1.60)

    def test_stage_cap_bonus_is_applied_but_marked_candidate_only(self):
        result = CANDIDATES.evaluate_candidates({
            "ramen_stage": 3,
            "basic_value": 200,
            "head_count": 0,
            "motivation": 3,
            "normal_cap": 100,
        })
        self.assertEqual(result["stage_effects"]["cap"], 40)
        self.assertTrue(all(row["predicted_gain"] <= 140
                            for row in result["prediction_groups"]))
        self.assertEqual(result["status"], "candidate_only_not_for_production_scoring")

    def test_observation_reports_all_exact_matches_without_confirmation(self):
        sample = {
            "ramen_stage": 1,
            "basic_value": 10,
            "head_count": 0,
            "motivation": 3,
            "support_training_bonus": 0,
            "region_training_bonus": 0,
            "observed_gain": 11,
        }
        result = CANDIDATES.evaluate_candidates(sample)
        self.assertGreater(result["exact_match_count"], 0)
        self.assertTrue(all(row["matches_observed"] for row in result["exact_matches"]))
        self.assertIn("additional discriminating samples", result["interpretation"])

    def test_support_and_region_bonus_create_multiple_predictions(self):
        result = CANDIDATES.evaluate_candidates({
            "ramen_stage": 2,
            "basic_value": 20,
            "head_count": 1,
            "motivation": 5,
            "motivation_bonus": 20,
            "support_training_bonus": 20,
            "region_training_bonus": 25,
            "friendship_bonuses": [30],
        })
        gains = {row["predicted_gain"] for row in result["prediction_groups"]}
        self.assertGreater(len(gains), 1)


if __name__ == "__main__":
    unittest.main()
