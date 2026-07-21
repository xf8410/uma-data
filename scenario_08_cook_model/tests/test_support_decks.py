import unittest
from scenario_08_cook_model.simulator import CookSimulator, validate_deck, STATUS_SCORE

class SupportDeckTest(unittest.TestCase):
    def test_real_deck_shape_director_and_unique_characters(self):
        ids=(30242,30283,30264,30294,30289,30207)
        cards=validate_deck(ids)
        self.assertEqual([c.kind for c in cards].count('guts'),2)
        self.assertEqual(len({c.chara_id for c in cards}),6)
        g=CookSimulator(1,ids)
        self.assertFalse(g.s.director_npc_present)
        self.assertEqual(len(g.s.npc_pos),7)
        self.assertTrue(cards[-1].link)

    def test_same_character_is_rejected(self):
        # Daring Tact wit and guts cards cannot be carried together.
        with self.assertRaises(ValueError):
            validate_deck((30242,30283,30293,30294,30248,30207))

    def test_new_unique_effects(self):
        cards=validate_deck((30298,30283,30264,30294,30289,30207))
        clash=cards[0].effects(80,5)
        self.assertEqual(clash['hint_count_bonus'],1)
        director=cards[-1]
        self.assertEqual(director.extra_bond_unique,(1,2))
        courage=cards[3].effects(80,5)
        self.assertEqual(courage['training_bonus'],10)

    def test_official_status_score_table(self):
        self.assertEqual(len(STATUS_SCORE),2801)
        self.assertEqual((STATUS_SCORE[100],STATUS_SCORE[1200],STATUS_SCORE[2300]),(66,3841,10117))

if __name__=='__main__':unittest.main()
