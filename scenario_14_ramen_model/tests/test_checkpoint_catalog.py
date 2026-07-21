import json, unittest
from pathlib import Path

D = json.loads((Path(__file__).parents[1] / 'checkpoint_catalog.json').read_text(encoding='utf-8'))

class CheckpointCatalogTest(unittest.TestCase):
    def test_turns_and_thresholds(self):
        cps = D['checkpoints']
        self.assertEqual([c['turn'] for c in cps], [24,48,72])
        self.assertEqual([(c['success_pt'],c['great_success_pt']) for c in cps], [(1500,0),(3000,0),(3500,5000)])

    def test_result_state_ranges(self):
        cps = D['checkpoints']
        self.assertEqual([r['result_state'] for r in cps[0]['result_ranges']], [1,2])
        self.assertEqual([r['result_state'] for r in cps[1]['result_ranges']], [1,2])
        self.assertEqual([r['result_state'] for r in cps[2]['result_ranges']], [1,2,3])
        self.assertEqual([(r['pt_min'],r['pt_max']) for r in cps[2]['result_ranges']], [(0,3499),(3500,4999),(5000,9999)])

    def test_settlement_effects_are_complete_and_raw(self):
        effects = [e for c in D['checkpoints'] for r in c['result_ranges'] for e in r['effects']]
        self.assertEqual(len(effects), 21)
        self.assertEqual(sorted({e['effect_type'] for e in effects}), [4,13,14])
        self.assertTrue(all('effect_value' in e for e in effects))

    def test_point_passives_are_not_settlement(self):
        tiers = D['checkpoint_point_passive_tiers']
        self.assertEqual(len(tiers), 33)
        self.assertEqual(sorted({r['effect_type'] for r in tiers}), [2,13,14])
        self.assertEqual(D['domain'], 'rmj_checkpoint_settlement')

if __name__ == '__main__': unittest.main()
