import pytest

from simulateur.models import Card, Pools

class TestCard:
    def test_valid_card(self):
        card = Card(2, 1, "character", "yellow")
        assert card.level == 2
        assert card.n_triggers == 1
        assert card.category == "character"
        assert card.color == "yellow"

    def test_card_is_frozen(self):
        card = Card(1, 0, "climax", "blue")
        with pytest.raises(Exception):
            card.level = 5

    @pytest.mark.parametrize("level", [-1, 1.5, "1", True, False])
    def test_invalid_level_raises(self, level):
        with pytest.raises(TypeError):
            Card(level, 0, "character", "yellow")

    def test_level_zero_is_valid(self):
        # level allows zero (unlike n_triggers=0 also allowed, but count > 0 fields don't)
        card = Card(0, 0, "character", "yellow")
        assert card.level == 0

    @pytest.mark.parametrize("n_triggers", [-1, 2.5, "0"])
    def test_invalid_n_triggers_raises(self, n_triggers):
        with pytest.raises(TypeError):
            Card(1, n_triggers, "character", "yellow")

    def test_invalid_category_raises(self):
        with pytest.raises(ValueError):
            Card(1, 0, "not-a-category", "yellow")

    def test_invalid_color_raises(self):
        with pytest.raises(ValueError):
            Card(1, 0, "character", "not-a-color")

    def test_two_cards_with_same_fields_are_equal(self):
        # frozen dataclass -> value equality, useful since pools rely on
        # cards being usable as dict keys / list membership
        assert Card(1, 0, "character", "yellow") == Card(1, 0, "character", "yellow")

    def test_card_is_hashable(self):
        # required: cards are used as dict keys in main.py specs
        {Card(1, 0, "character", "yellow"): 4}


class TestPools:
    def test_empty_pools_defaults(self):
        pools = Pools()
        assert pools.main_climax == []
        assert pools.max_trigger_level == 0
        assert pools.max_main_level == 0

    def test_max_trigger_level_across_climax_and_non_climax(self):
        pools = Pools(
            trigger_climax=[Card(3, 1, "climax", "yellow")],
            trigger_non_climax=[Card(1, 0, "character", "yellow"),
                                 Card(5, 0, "character", "yellow")],
        )
        assert pools.max_trigger_level == 5

    def test_max_main_level_ignores_trigger_pools(self):
        pools = Pools(
            main_non_climax=[Card(2, 0, "character", "yellow")],
            trigger_non_climax=[Card(9, 0, "character", "yellow")],
        )
        assert pools.max_main_level == 2