import json, unittest
from pathlib import Path

D = json.loads((Path(__file__).parents[1] / 'resource_economy.json').read_text(encoding='utf-8'))

class ResourceEconomyTest(unittest.TestCase):
    def test_inventory_caps_and_names(self):
        self.assertEqual(D['normal_items']['shared_inventory_cap'], 10)
        self.assertEqual([x['name_ja'] for x in D['normal_items']['items']], ['麺のコツ','スープのコツ','トッピングのコツ'])
        self.assertEqual(D['special_item']['inventory_cap'], 4)
        self.assertFalse(D['special_item']['shares_normal_inventory'])
        self.assertEqual(D['special_item']['max_substitutions_per_ramen'], 2)

    def test_all_recipes_cost_five(self):
        self.assertEqual([r['region_id'] for r in D['recipes']], list(range(1,21)))
        self.assertTrue(all(r['normal_item_total'] == 5 for r in D['recipes']))
        self.assertEqual(D['recipes'][0]['cost'], {'1':2,'2':2,'3':1})
        self.assertEqual(D['recipes'][10]['cost'], {'1':2,'2':2,'3':1})

    def test_fixed_special_gains(self):
        gains = [(r['turn'], r['count']) for r in D['special_item']['fixed_turn_gains']]
        self.assertEqual(gains, [(1,2),(24,2),(36,2),(37,1),(38,1),(39,1),(48,2),(60,2),(61,1),(62,1),(63,1)])

    def test_outing_rewards(self):
        rewards = D['special_item']['outing_rewards']
        self.assertEqual(len(rewards), 25)
        by_card = {}
        for r in rewards: by_card.setdefault(r['support_card_id'], []).append(r['special_feeling_num'])
        self.assertEqual(by_card[30305], [2]*5)
        for card in (10021,30021,10083,30052): self.assertEqual(by_card[card], [1]*5)
        self.assertTrue(all(r['support_card_name_ja'] for r in rewards))

    def test_year_end_rules(self):
        reset = D['normal_items']['year_end_reset']
        self.assertTrue(reset['clears_all_normal_items'])
        self.assertTrue(reset['remaining_items_restore_vital'])
        self.assertFalse(D['special_item']['cleared_at_year_end'])

if __name__ == '__main__': unittest.main()
