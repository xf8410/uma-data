import json, unittest
from pathlib import Path

P = Path(__file__).parents[1] / 'region_catalog.json'
D = json.loads(P.read_text(encoding='utf-8'))

class RegionCatalogTest(unittest.TestCase):
    def test_all_regions_and_names(self):
        regions = D['regions']
        self.assertEqual([r['region_id'] for r in regions], list(range(1, 21)))
        names = ['札幌','函館','新潟','福島','東京','中山','中京','京都','阪神','小倉']
        self.assertEqual([r['name_ja'] for r in regions[:10]], names)
        self.assertEqual([r['name_ja'] for r in regions[10:]], names)

    def test_phase_boundaries(self):
        self.assertEqual([(r['region_select_type'], r['turn']) for r in D['selection_phases']], [(1,3),(2,24),(3,48)])
        self.assertEqual([r['region_select_type'] for r in D['regions']], [1]*5 + [2]*5 + [3]*10)

    def test_third_phase_reuses_names_not_effects(self):
        for early, third in zip(D['regions'][:10], D['regions'][10:]):
            self.assertEqual(early['name_ja'], third['name_ja'])
            self.assertNotEqual(
                [e['text_group_id'] for e in early['effects']],
                [e['text_group_id'] for e in third['effects']],
            )
            self.assertNotEqual(
                [(e['effect_type'], e['effect_value']) for e in early['effects']],
                [(e['effect_type'], e['effect_value']) for e in third['effects']],
            )

    def test_effect_and_feeling_counts(self):
        self.assertEqual(sum(len(r['effects']) for r in D['regions']), 98)
        self.assertEqual(sum(len(r['feelings']) for r in D['regions']), 60)
        self.assertEqual(sum(len(r['point_bonus_tiers']) for r in D['regions']), 180)
        self.assertTrue(all(e['display_template'] for r in D['regions'] for e in r['effects']))

    def test_known_display_semantics(self):
        r1 = D['regions'][0]
        self.assertIn('スピードのトレーニング効果アップ', r1['effects'][0]['display_template'])
        r2 = D['regions'][1]
        self.assertIn('スタミナのトレーニング効果アップ', r2['effects'][0]['display_template'])

if __name__ == '__main__': unittest.main()
