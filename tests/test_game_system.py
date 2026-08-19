import random
from collections import deque

import pytest

from simulateur.game_system import GameSystem, SystemBrokenError, run_trial_from_decks
from simulateur.grammar import parse_occurrences
from simulateur.models import Card


CHAR = Card(1, 0, "character", "yellow")
CLIMAX_LOW = Card(0, 0, "climax", "yellow")
TRIGGER_CHAR = Card(1, 1, "character", "yellow")


def _decks(main_size=30, main_climax=6, trigger_size=16, trigger_stock=2, main_stock=2):
    main = deque([CLIMAX_LOW] * main_climax + [CHAR] * (main_size - main_climax))
    random.shuffle(main)
    main_stock_cards = [CHAR] * main_stock
    trigger = deque([TRIGGER_CHAR] * trigger_size)
    trigger_stock_cards = [TRIGGER_CHAR] * trigger_stock
    return main, trigger, trigger_stock_cards, main_stock_cards


class TestCardConservation:
    """The total number of cards tracked across all zones must never
    change during a trial: nothing should be created or silently dropped
    by burn/mill/scry/shuffle/refresh handling.
    """

    @pytest.mark.parametrize("seed", range(10))
    def test_conservation_holds_over_many_random_seeds(self, seed):
        random.seed(seed)
        main, trigger, trigger_stock, main_stock = _decks()
        occurrences = parse_occurrences(
            ["BURN(4)", "BURN(3)/A", "BURN(4)", "BURN(3)/A", "BURN(4)", "BURN(3)/A"]
        )
        # should not raise AssertionError from check_invariant()
        run_trial_from_decks(
            main, trigger, trigger_stock, main_stock, occurrences,
            check_invariants=True,
        )

    @pytest.mark.parametrize("seed", range(5))
    def test_conservation_holds_with_mill_and_scry(self, seed):
        random.seed(seed)
        main, trigger, trigger_stock, main_stock = _decks()
        occurrences = parse_occurrences(
            ["MILL(2) OPP BOTTOM COUNT", "SCRY(3)", "BURN(2)/T"]
        )
        run_trial_from_decks(
            main, trigger, trigger_stock, main_stock, occurrences,
            check_invariants=True,
        )

    @pytest.mark.parametrize("seed", range(5))
    def test_conservation_holds_with_shuffle_and_stock_ops(self, seed):
        random.seed(seed)
        main, trigger, trigger_stock, main_stock = _decks(trigger_stock=4)
        occurrences = parse_occurrences(
            ["(1)SHUFFLE(2)->BURN(2)", "STOCKSWAP", "STOCKSHUFFLE"]
        )
        run_trial_from_decks(
            main, trigger, trigger_stock, main_stock, occurrences,
            check_invariants=True,
        )


class TestRefreshAndDeckout:
    def test_deckout_raises_system_broken_error(self):
        # tiny deck, no discard to reshuffle from -> must hit the loss condition
        random.seed(0)
        main = deque([CHAR])
        trigger = deque([TRIGGER_CHAR] * 4)
        gs = GameSystem(main, trigger)
        with pytest.raises(SystemBrokenError):
            for _ in range(50):
                gs.refresh()

    def test_levelup_moves_seven_cards_and_keeps_one_non_climax(self):
        gs = GameSystem(deque([CHAR]), deque([TRIGGER_CHAR]))
        batch = [CHAR] * 6 + [CLIMAX_LOW]
        gs.keep_cards(batch)
        # 7 cards triggers a level-up: exactly one non-climax card is kept
        # in the level zone, the rest go to discard
        assert len(gs.level_zone) == 1
        assert gs.level_zone[0].category != "climax"
        assert len(gs.discard) == 6


class TestResolutionCancellation:
    def test_burn_cancelled_by_climax_returns_true_and_deals_no_damage(self):
        # main deck starts with a climax on top (pop() draws from the end)
        main = deque([CHAR, CHAR, CLIMAX_LOW])
        trigger = deque([TRIGGER_CHAR] * 4)
        gs = GameSystem(main, trigger)
        occ = parse_occurrences(["BURN(3)"])[0]
        canceled = occ.resolve(gs)
        assert canceled is True
        assert gs.total_damage == 0

    def test_burn_not_cancelled_deals_full_damage(self):
        main = deque([CHAR] * 5)
        trigger = deque([TRIGGER_CHAR] * 4)
        gs = GameSystem(main, trigger)
        occ = parse_occurrences(["BURN(3)"])[0]
        canceled = occ.resolve(gs)
        assert canceled is False
        assert gs.total_damage == 3

    def test_unpayable_cost_returns_false_without_resolving(self):
        main = deque([CHAR] * 5)
        trigger = deque([TRIGGER_CHAR] * 4)
        gs = GameSystem(main, trigger)  # no trigger_deck_stock available
        occ = parse_occurrences(["(1)BURN(3)"])[0]
        resolved = occ.resolve(gs)
        assert resolved is False
        assert gs.total_damage == 0