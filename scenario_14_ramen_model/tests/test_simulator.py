import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ramen_simulator", ROOT / "simulator.py")
SIM = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SIM)


class SimulatorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogs = SIM.load_catalogs(ROOT)

    def test_region_name_and_point_bonus_are_resolved(self):
        regions = SIM.resolve_regions(self.catalogs["regions"], [1, 11], 600)
        self.assertEqual([row["name_ja"] for row in regions], ["札幌", "札幌"])
        self.assertNotEqual(regions[0]["region_id"], regions[1]["region_id"])
        speed = next(effect for effect in regions[0]["effects"] if effect["effect_type"] == 2)
        self.assertEqual(speed["base_value"], 20)
        self.assertEqual(speed["add_value"], 5)
        self.assertEqual(speed["resolved_value"], 25)
        self.assertEqual(speed["bonus_tier"], {"min_pt": 600, "max_pt": 899})

    def test_runtime_final_gauge_vector_replays_reset_and_fifo(self):
        ramen = {
            "feeling_info": [
                {"feeling_id": 1, "feeling_index": 0},
                {"feeling_id": 2, "feeling_index": 1},
                {"feeling_id": 3, "feeling_index": 2},
                {"feeling_id": 1, "feeling_index": 3},
                {"feeling_id": 2, "feeling_index": 4},
                {"feeling_id": 3, "feeling_index": 5},
                {"feeling_id": 1, "feeling_index": 6},
                {"feeling_id": 2, "feeling_index": 7},
                {"feeling_id": 3, "feeling_index": 8},
                {"feeling_id": 1, "feeling_index": 9},
            ],
            "acquisition_gauges": [
                {"feeling_id": 1, "remaining": 2},
                {"feeling_id": 2, "remaining": 5},
                {"feeling_id": 3, "remaining": 6},
            ],
            "command_gauge_vectors": [{
                "command_id": 601,
                "progress": [
                    {"feeling_id": 1, "remaining": 5},
                    {"feeling_id": 2, "remaining": 3},
                    {"feeling_id": 3, "remaining": 4},
                ],
            }],
        }
        result = SIM.simulate_gauges(self.catalogs["gauges"], ramen)[0]
        self.assertEqual(result["gained_feelings"], [1])
        self.assertEqual(result["remaining_after"], {1: 7, 2: 2, 3: 2})
        self.assertEqual(result["evicted_feelings"], [1])
        self.assertEqual(result["inventory_after"][-1], 1)
        self.assertFalse(result["overflow_carried"])

    def test_recipe_uses_at_most_two_special_items(self):
        recipe = self.catalogs["resources"]["recipes"][0]
        ramen = {
            "selected_region_ids": [recipe["region_id"]],
            "sozai": [0, 0, 0],
            "special_feeling_num": 4,
        }
        result = SIM.recipe_affordability(self.catalogs["resources"], ramen)[0]
        self.assertEqual(result["special_needed"], 5)
        self.assertFalse(result["craftable"])

    def test_checkpoint_projection_uses_catalog_thresholds(self):
        result = SIM.checkpoint_projection(
            self.catalogs["checkpoints"], self.catalogs["actions"], 20, 1000, 2)
        self.assertEqual(result["checkpoint_turn"], 24)
        self.assertEqual(result["base_pt_per_ramen"], 300)
        self.assertEqual(result["projected_pt"], 1600)
        self.assertEqual(result["success_shortfall"], 0)

    def test_training_gains_are_passed_through(self):
        snapshot = {
            "turn": 20,
            "planned_ramen_count": 1,
            "trainings": [{"command_id": 601, "gains": {"Speed": 42, "SkillPt": 7}}],
            "ramen": {"check_point_pt": 1000, "selected_region_ids": []},
        }
        result = SIM.simulate(snapshot, self.catalogs)
        self.assertEqual(result["training_gains"][0]["gains"], {"Speed": 42, "SkillPt": 7})
        self.assertEqual(result["training_gains"][0]["source"], "runtime_final_gains")
        self.assertIn("server-side training gain decomposition and rounding", result["unknowns"])
    def test_accepts_plugin_checkpoint_pt(self):
        # Real plugin /summary schema uses "checkpoint_pt" (no underscore).
        snapshot = {
            "turn": 24,
            "ramen": {
                "checkpoint_pt": 1600,
                "selected_region_ids": [],
            },
        }
        result = SIM.simulate(snapshot, self.catalogs)
        self.assertEqual(result["checkpoint"]["current_pt"], 1600)

    def test_checkpoint_pt_precedence_and_snapshot_fallback(self):
        # ramen-level spelling wins over snapshot-level legacy spelling.
        snapshot = {
            "turn": 24,
            "check_point_pt": 500,
            "ramen": {"checkpoint_pt": 1600, "selected_region_ids": []},
        }
        result = SIM.simulate(snapshot, self.catalogs)
        self.assertEqual(result["checkpoint"]["current_pt"], 1600)
        # snapshot-level legacy spelling still works when ramen omits it.
        snapshot2 = {"turn": 24, "check_point_pt": 500, "ramen": {}}
        result2 = SIM.simulate(snapshot2, self.catalogs)
        self.assertEqual(result2["checkpoint"]["current_pt"], 500)


if __name__ == "__main__":
    unittest.main()
