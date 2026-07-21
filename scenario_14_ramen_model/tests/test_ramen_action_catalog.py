import json, unittest
from pathlib import Path

D = json.loads((Path(__file__).parents[1] / 'ramen_action_catalog.json').read_text(encoding='utf-8'))

class RamenActionCatalogTest(unittest.TestCase):
    def test_stage_counts_and_point_gain(self):
        self.assertEqual([len(s['effects']) for s in D['stages']], [3, 5, 7])
        self.assertEqual([s['base_checkpoint_pt_gain'] for s in D['stages']], [300, 400, 500])
        self.assertTrue(all(s['effect_duration'] == 'current_turn' for s in D['stages']))

    def test_stage_one_bond_is_action_effect(self):
        effect = next(e for e in D['stages'][0]['effects'] if e['id'] == 3)
        self.assertEqual((effect['effect_type'], effect['effect_value']), (15, 10))
        self.assertIn('絆ゲージ', effect['display_text_ja'])
        self.assertIn('+10', effect['display_text_ja'])

    def test_failure_reduction_by_stage(self):
        expected = [(2,30),(6,50),(11,100)]
        actual = []
        for stage in D['stages']:
            effect = next(e for e in stage['effects'] if '失敗率ダウン' in e['display_text_ja'])
            actual.append((effect['id'], effect['effect_value']))
        self.assertEqual(actual, expected)

    def test_no_missing_display_text(self):
        effects = [e for s in D['stages'] for e in s['effects']]
        self.assertEqual(len(effects), 15)
        self.assertTrue(all(e['display_text_ja'] for e in effects))
        self.assertIn('そのターン中のみ', D['tutorial_evidence']['text_ja'])

if __name__ == '__main__': unittest.main()
