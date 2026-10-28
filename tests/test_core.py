import math
import unittest
from itertools import combinations

from p0ka.cards import Card, HandRules, STANDARD, SHORT_DECK, OMAHA, evaluate_five, evaluate_best, combinadic_rank, canonical_cards
from p0ka.icm import icm_equity
from p0ka.beliefs import TableBeliefs, update_range
from p0ka.graph import StateKey, TranspositionCache
from p0ka.policy import Action, Decision, Observation, choose_action, validate_decision
from p0ka.kuhn import KuhnCFR, expected_p0


def hand(*codes):
    return tuple(Card.parse(c) for c in codes)


class CardTests(unittest.TestCase):
    def test_card_validation(self):
        with self.assertRaises(ValueError):
            Card.parse("1s")
        with self.assertRaises(ValueError):
            evaluate_five(hand("As", "As", "Ks", "Qs", "Js"))

    def test_ranking(self):
        straight_flush = evaluate_five(hand("As", "Ks", "Qs", "Js", "Ts"))
        quads = evaluate_five(hand("As", "Ah", "Ad", "Ac", "Ks"))
        full_house = evaluate_five(hand("As", "Ah", "Ad", "Ks", "Kh"))
        flush = evaluate_five(hand("As", "Js", "9s", "5s", "2s"))
        straight = evaluate_five(hand("9s", "8h", "7d", "6c", "5s"))
        self.assertTrue(straight_flush > quads > full_house > flush > straight)

    def test_wheels(self):
        self.assertEqual(evaluate_five(hand("As", "2h", "3d", "4c", "5s"))[1], 5)
        self.assertEqual(evaluate_five(hand("As", "6h", "7d", "8c", "9s"), SHORT_DECK)[1], 9)
        with self.assertRaises(ValueError):
            evaluate_five(hand("As", "2h", "7d", "8c", "9s"), SHORT_DECK)

    def test_short_deck_flush_beats_full(self):
        flush = evaluate_five(hand("As", "Ks", "Qs", "9s", "6s"), SHORT_DECK)
        full = evaluate_five(hand("Ah", "Ad", "Ac", "Kh", "Kd"), SHORT_DECK)
        self.assertGreater(flush, full)

    def test_omaha_exact_selection(self):
        hole = hand("As", "Ks", "Qs", "Jh")
        board = hand("Ts", "9s", "8d", "2c", "3d")
        holdem = evaluate_best(hole, board, STANDARD)
        omaha = evaluate_best(hole, board, OMAHA)
        self.assertEqual(holdem[0], 5)  # five spades in the union
        self.assertLess(omaha, holdem)   # only two private cards allowed

    def test_combinadic_unique(self):
        ranks = {combinadic_rank(tuple(c), 8) for c in combinations(range(8), 3)}
        self.assertEqual(ranks, set(range(math.comb(8, 3))))

    def test_suit_isomorphism(self):
        x = canonical_cards(hand("As", "Ks"), (hand("Qh", "Jh", "2c"),))
        y = canonical_cards(hand("Ah", "Kh"), (hand("Qs", "Js", "2c"),))
        self.assertEqual(x, y)
        self.assertNotEqual(x, canonical_cards(hand("As", "Ks"), (hand("Qh", "Jh"), hand("2c"))))


class IcmTests(unittest.TestCase):
    def test_equal_stacks(self):
        self.assertEqual(icm_equity((100., 100.), (10., 4.)), (7., 7.))
        values = icm_equity((1.,) * 8, (20., 12., 8., 5., 3., 2., 1., 0.))
        for x in values:
            self.assertAlmostEqual(x, 51.0 / 8, places=10)

    def test_known_two_player(self):
        self.assertEqual(icm_equity((75., 25.), (10., 0.)), (7.5, 2.5))

    def test_conservation(self):
        payouts = (100., 60., 40., 20., 10., 0., 0., 0.)
        values = icm_equity((13., 21., 5., 4., 9., 16., 3., 31.), payouts)
        self.assertAlmostEqual(sum(values), sum(payouts), places=8)
        self.assertGreater(values[-1], values[6])

    def test_reject_bad(self):
        with self.assertRaises(ValueError):
            icm_equity((0., 0.), (2., 1.))


class BeliefTests(unittest.TestCase):
    def test_idempotent_and_reset(self):
        b = TableBeliefs("table1")
        opts = ("fold", "call")
        self.assertTrue(b.observe("h1/a1", "seat2", "preflop-facing-raise", "fold", opts))
        self.assertFalse(b.observe("h1/a1", "seat2", "preflop-facing-raise", "fold", opts))
        self.assertAlmostEqual(b.predictive("seat2", "preflop-facing-raise", "fold", opts), 2/3)
        v = b.version
        b.reset("table2")
        self.assertEqual(b.version, v + 1)
        self.assertAlmostEqual(b.predictive("seat2", "preflop-facing-raise", "fold", opts), .5)

    def test_range_update_and_blocker(self):
        r = update_range({1: .5, 2: .3, 3: .2}, {1: .5, 2: 1., 3: .9}, frozenset((3,)))
        self.assertAlmostEqual(sum(r.values()), 1.)
        self.assertGreater(r[2], r[1])
        self.assertNotIn(3, r)
        with self.assertRaises(ValueError):
            update_range({1: 1.}, {1: 0.})


class GraphTests(unittest.TestCase):
    def test_belief_version_isolation_and_lru(self):
        cache = TranspositionCache(2)
        a = StateKey("v1", (1,), ("As",), ("raise",), 1)
        b = StateKey("v1", (1,), ("As",), ("raise",), 2)
        c = StateKey("v1", (2,), ("As",), ("raise",), 2)
        cache.put(a, 0.8)
        self.assertIsNone(cache.get(b))
        cache.put(b, 0.5)
        cache.put(c, 0.4)
        self.assertIsNone(cache.get(a))
        self.assertEqual(len(cache), 2)


class PolicyTests(unittest.TestCase):
    def test_fallback_legal(self):
        legal = (Action("fold"), Action("call"))
        action = choose_action(Observation(legal, pot=100, to_call=80))
        self.assertTrue(validate_decision(action, legal))
        self.assertEqual(action.kind, "fold")

    def test_check_no_equity(self):
        legal = (Action("check"), Action("raise", 20, 100))
        self.assertEqual(choose_action(Observation(legal, 100, 0)).kind, "check")

    def test_call_above_threshold(self):
        legal = (Action("fold"), Action("call"))
        self.assertEqual(choose_action(Observation(legal, 100, 20, .8)).kind, "call")

    def test_clamped_raise(self):
        legal = (Action("check"), Action("raise", 75, 90))
        d = choose_action(Observation(legal, 100, 0, .95))
        self.assertTrue(validate_decision(d, legal))
        self.assertEqual(d.amount, 75)


class KuhnTests(unittest.TestCase):
    def test_near_equilibrium_value(self):
        cfr = KuhnCFR()
        cfr.train(2000)
        value = expected_p0(cfr.policy())
        self.assertAlmostEqual(value, -1 / 18, delta=.065)
        self.assertEqual(len(cfr.policy()), 12)


class PotTests(unittest.TestCase):
    def test_sidepot(self):
        from p0ka.pots import settle_pots
        # Seat 0 has best hand but only contributed 50; seat 1 wins the side pot.
        s = settle_pots((50, 100, 100), (True, True, True),
                        ((8, 14), (3, 13), (2, 12)))
        self.assertEqual(s.awards, (150, 100, 0))
        self.assertEqual(s.refunds, (0, 0, 0))

    def test_odd_chip_and_unmatched_refund(self):
        from p0ka.pots import settle_pots
        s = settle_pots((5, 5, 9), (True, True, True),
                        ((1, 14), (1, 14), (0, 8)), (1, 0, 2))
        self.assertEqual(s.awards, (7, 8, 0))
        self.assertEqual(s.refunds, (0, 0, 4))

    def test_folded_contribution(self):
        from p0ka.pots import settle_pots
        s = settle_pots((20, 20, 20), (False, True, True),
                        (None, (2, 12), (1, 14)))
        self.assertEqual(s.awards, (0, 60, 0))

    def test_inconsistent_history_rejected(self):
        from p0ka.pots import settle_pots
        with self.assertRaises(ValueError):
            settle_pots((10, 10), (False, False), (None, None))


class BenchmarkTests(unittest.TestCase):
    def test_measured_function_and_validation(self):
        from p0ka.benchmark import measure
        summary = measure(lambda x: x + 1, [1, 2, 3], repeats=5)
        self.assertEqual(summary.samples, 15)
        self.assertTrue(0 <= summary.p50_us <= summary.maximum_us)
        with self.assertRaises(ValueError):
            measure(lambda x: x, [])

class EquityTests(unittest.TestCase):
    def test_unbeatable_royal_flush(self):
        from p0ka.equity import uniform_equity
        result = uniform_equity(hand("As", "Ks"), hand("Qs", "Js", "Ts", "2d", "3c"),
                                opponents=5, trials=30, seed=7)
        self.assertEqual(result.equity, 1.0)
        self.assertEqual(result.sole_wins, 30)

    def test_board_tie(self):
        from p0ka.equity import uniform_equity
        # Royal flush on board means everyone ties regardless of their cards.
        result = uniform_equity(hand("2d", "3c"), hand("As", "Ks", "Qs", "Js", "Ts"),
                                opponents=3, trials=20)
        self.assertAlmostEqual(result.equity, .25)
        self.assertEqual(result.tied_first, 20)

    def test_repeatable_sampling(self):
        from p0ka.equity import uniform_equity
        a = uniform_equity(hand("As", "Ah"), hand("2c", "7d", "9s"), trials=30, seed=10)
        b = uniform_equity(hand("As", "Ah"), hand("2c", "7d", "9s"), trials=30, seed=10)
        self.assertEqual(a, b)

    def test_reject_invalid_sampler_config(self):
        from p0ka.equity import uniform_equity
        with self.assertRaises(ValueError):
            uniform_equity(hand("As", "As"))
        with self.assertRaises(ValueError):
            uniform_equity(hand("As", "Ks"), rules=OMAHA)


if __name__ == "__main__":
    unittest.main()
