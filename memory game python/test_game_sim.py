"""Tests for the game logic. Run:  python -m unittest test_game_sim -v"""
import itertools
import unittest

from game_sim import Params, expected_hits, run


def all_layouts():
    """Every distinct arrangement of 3 pairs (0,0,1,1,2,2) in 6 slots - 90 of them."""
    return sorted(set(itertools.permutations([0, 0, 1, 1, 2, 2])))


class TestGame(unittest.TestCase):
    def test_all_90_layouts(self):
        layouts = all_layouts()
        self.assertEqual(len(layouts), 90)
        worst = 0.0
        for lay in layouts:
            r = run(lay)
            with self.subTest(layout=lay):
                self.assertEqual(r["state"], "Done")
                self.assertEqual(r["hits"], expected_hits(list(lay)))   # right cards, right order
                self.assertEqual(sorted(r["hits"]), [1, 2, 3, 4, 5, 6])  # every card once
                self.assertEqual(r["err_count"], 0)
                self.assertFalse(r["laser_moving"])                      # laser only when stopped
                self.assertLessEqual(abs(r["final_actual"]), 1)          # back home at the end
            worst = max(worst, r["time_s"])
        print(f"\n  worst-case game time over 90 layouts: {worst:.1f} s")

    def test_pairs_shot_back_to_back(self):
        for lay in all_layouts():
            h = run(lay)["hits"]
            for a, b in zip(h[0::2], h[1::2]):
                self.assertEqual(lay[a - 1], lay[b - 1])

    def test_unknown_start_position_and_far_start(self):
        r = run([2, 1, 0, 0, 1, 2], start_steps=2900)
        self.assertEqual(r["hits"], [1, 6, 2, 5, 3, 4])

    def test_laser_offset(self):
        p = Params(LASER_OFFSET_MM=-30.0)   # laser spot 30 mm towards home from camera centre
        lay = [0, 1, 0, 2, 1, 2]
        r = run(lay, p)
        self.assertEqual(r["hits"], expected_hits(lay))

    def test_unreadable_candidate_is_skipped_not_shot(self):
        lay = [0, -1, 1, 0, 1, 2]           # slot 2 unreadable; slot 6 then has no partner
        r = run(lay)
        self.assertEqual(r["state"], "Done")
        self.assertNotIn(2, r["hits"])
        self.assertEqual(r["hits"], [1, 4, 3, 5, 6])
        self.assertGreaterEqual(r["err_count"], 1)

    def test_unmatched_card_does_not_stall(self):
        lay = [0, 1, 2, 0, 1, 3]            # ID 2 and ID 3 have no partner
        r = run(lay)
        self.assertEqual(r["state"], "Done")
        self.assertEqual(r["hits"], expected_hits(lay))
        self.assertEqual(r["err_count"], 2)

    def test_broken_end_switch_faults(self):
        r = run([0, 0, 1, 1, 2, 2], switch_works=False, max_s=60)
        self.assertEqual(r["state"], "Fault")
        self.assertEqual(r["hits"], [])

    def test_active_high_wiring(self):
        p = Params(ENDSW_ACTIVE_LOW=False, DIR_POS_LEVEL=False)
        lay = [1, 2, 2, 0, 1, 0]
        self.assertEqual(run(lay, p)["hits"], expected_hits(lay))


if __name__ == "__main__":
    unittest.main()
