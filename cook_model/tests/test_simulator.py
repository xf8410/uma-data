import unittest
from cook_model.simulator import CookSimulator, TARGET_RACES, TOTAL_TURNS, CARD_ID, SCENARIO_ID

class SimulatorTest(unittest.TestCase):
    def test_fixed_identity_and_shape(self):
        g=CookSimulator(1)
        self.assertEqual((SCENARIO_ID,CARD_ID),(8,101101))
        self.assertEqual(len(g.features()),128)

    def test_complete_run_advances_and_executes_targets_events(self):
        g=CookSimulator(20260720); seen=[]
        while not g.done:
            if g.forced_race:seen.append(g.s.turn)
            main=7 if g.forced_race else (5 if g.s.vital<25 else 4)
            g.step(0,main)
        self.assertEqual(g.s.turn,TOTAL_TURNS)
        self.assertTrue(set((11,22,33,45,47,59,66,71,73,75,77)).issubset(seen))
        self.assertGreaterEqual(g.s.race_count,len(seen))
        self.assertGreater(g.s.event_counts[0],0)
        self.assertGreater(g.s.event_counts[2],0)

    def test_deterministic_seed(self):
        def run(seed):
            g=CookSimulator(seed)
            while not g.done:g.step(0,7 if g.forced_race else 4)
            return g.score(),g.s.status,g.s.event_counts
        self.assertEqual(run(9),run(9)); self.assertNotEqual(run(9),run(10))

if __name__=='__main__':unittest.main()
