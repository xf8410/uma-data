import json, unittest
from pathlib import Path

D = json.loads((Path(__file__).parents[1] / 'acquisition_gauge_catalog.json').read_text(encoding='utf-8'))

class AcquisitionGaugeCatalogTest(unittest.TestCase):
    def test_scenario_and_feeling_identity(self):
        self.assertEqual(D['scenario_id'], 14)
        self.assertEqual(
            [(x['feeling_id'], x['name_ja']) for x in D['normal_feelings']],
            [(1, '麺のコツ'), (2, 'スープのコツ'), (3, 'トッピングのコツ')],
        )
        self.assertEqual(D['system'], 'normal_feeling_acquisition_gauge')
        self.assertTrue(any('heroes_gauge' in x for x in D['planner_constraints']))

    def test_runtime_protocol_keeps_state_mapping_and_vectors_separate(self):
        protocol = D['runtime_protocol']
        self.assertEqual(protocol['current_state']['dataset_array'], 'FeelingTurnInfoArray')
        self.assertEqual(protocol['command_to_feeling']['dataset_array'], 'CommandFeelingInfoArray')
        self.assertEqual(protocol['final_command_vectors']['dataset_array'], 'FeelingReduceTurnInfoArray')
        self.assertIn('do not hard-code', protocol['command_to_feeling']['rule'])

    def test_threshold_reset_and_full_inventory_behavior(self):
        rules = D['acquisition_rules']
        self.assertEqual(rules['threshold'], 7)
        self.assertEqual(rules['on_reach_threshold']['grants_matching_normal_item'], 1)
        self.assertTrue(rules['on_reach_threshold']['resets_gauge'])
        self.assertFalse(rules['on_reach_threshold']['overflow_progress_carried'])
        self.assertEqual(rules['inventory']['shared_capacity'], 10)
        self.assertEqual(rules['inventory']['overflow_policy'], 'fifo_drop_oldest_then_append_new')
        self.assertFalse(rules['inventory']['blocked_when_full'])

    def test_strict_sample_is_not_promoted_to_general_formula(self):
        sample = D['observations']['strict_training_sample']
        self.assertEqual(sample['base_vector_by_feeling_id'], {'1': 3, '2': 3, '3': 4})
        self.assertEqual(sample['speed_command_vector_by_feeling_id'], {'1': 5, '2': 3, '3': 4})
        self.assertIn('not asserted as a universal formula', sample['interpretation'])
        self.assertTrue(any('general decomposition' in x for x in D['unknowns']))

if __name__ == '__main__': unittest.main()
