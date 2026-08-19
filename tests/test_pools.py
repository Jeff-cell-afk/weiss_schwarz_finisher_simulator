import pytest

from simulateur.models import Card, Pools
from simulateur.pools import build_pools, expand_pool, validate_pools


CHAR = Card(1, 0, "character", "yellow")
CLIMAX = Card(0, 1, "climax", "yellow")


class TestExpandPool:
    def test_expands_counts_into_flat_list(self):
        pool = expand_pool({CHAR: 3})
        assert pool == [CHAR, CHAR, CHAR]

    def test_multiple_cards(self):
        other = Card(2, 0, "character", "blue")
        pool = expand_pool({CHAR: 2, other: 1})
        assert pool.count(CHAR) == 2
        assert pool.count(other) == 1

    @pytest.mark.parametrize("count", [0, -1, 1.5])
    def test_invalid_count_raises(self, count):
        with pytest.raises(ValueError):
            expand_pool({CHAR: count})


class TestBuildPools:
    def test_builds_all_four_pools(self):
        pools = build_pools(
            main_non_climax_specs={CHAR: 4},
            main_climax_specs={CLIMAX: 2},
            trigger_non_climax_specs={CHAR: 4},
            trigger_climax_specs={CLIMAX: 2},
        )
        assert len(pools.main_non_climax) == 4
        assert len(pools.main_climax) == 2
        assert len(pools.trigger_non_climax) == 4
        assert len(pools.trigger_climax) == 2


class TestValidatePools:
    def _pools(self, non_climax_n=20, climax_n=10):
        return Pools(
            main_non_climax=[CHAR] * non_climax_n,
            main_climax=[CLIMAX] * climax_n,
            trigger_non_climax=[CHAR] * non_climax_n,
            trigger_climax=[CLIMAX] * climax_n,
        )

    def test_passes_with_sufficient_pools(self):
        # should not raise
        validate_pools(
            self._pools(non_climax_n=20, climax_n=10),
            deck_size_list=[20], climax_list=[8],
            trigger_deck_size=16, trigger_deck_climax=4,
        )

    def test_trigger_climax_exceeding_trigger_deck_size_raises(self):
        with pytest.raises(ValueError, match="trigger_deck_climax"):
            validate_pools(
                self._pools(),
                deck_size_list=[20], climax_list=[8],
                trigger_deck_size=10, trigger_deck_climax=12,
            )

    def test_negative_trigger_stock_size_raises(self):
        with pytest.raises(ValueError, match="trigger_deck_stock_size"):
            validate_pools(
                self._pools(),
                deck_size_list=[20], climax_list=[8],
                trigger_deck_size=16, trigger_deck_climax=4,
                trigger_deck_stock_size=-1,
            )

    def test_negative_main_stock_size_raises(self):
        with pytest.raises(ValueError, match="main_deck_stock_size"):
            validate_pools(
                self._pools(),
                deck_size_list=[20], climax_list=[8],
                trigger_deck_size=16, trigger_deck_climax=4,
                main_deck_stock_size=-1,
            )

    def test_no_valid_size_climax_pair_raises(self):
        # climax_n < deck_size is required for every tested pair here
        with pytest.raises(ValueError, match="No valid"):
            validate_pools(
                self._pools(),
                deck_size_list=[20], climax_list=[20, 25],
                trigger_deck_size=16, trigger_deck_climax=4,
            )

    def test_insufficient_main_non_climax_pool_raises(self):
        with pytest.raises(ValueError, match="main_non_climax"):
            validate_pools(
                self._pools(non_climax_n=5, climax_n=10),
                deck_size_list=[20], climax_list=[8],
                trigger_deck_size=16, trigger_deck_climax=4,
            )

    def test_insufficient_main_climax_pool_raises(self):
        with pytest.raises(ValueError, match="main_climax"):
            validate_pools(
                self._pools(non_climax_n=20, climax_n=2),
                deck_size_list=[20], climax_list=[8],
                trigger_deck_size=16, trigger_deck_climax=4,
            )

    def test_main_deck_stock_size_increases_non_climax_requirement(self):
        # 20 non-climax available; deck needs (20-8)=12, +9 stock = 21 > 20
        with pytest.raises(ValueError, match="main_non_climax"):
            validate_pools(
                self._pools(non_climax_n=20, climax_n=10),
                deck_size_list=[20], climax_list=[8],
                trigger_deck_size=16, trigger_deck_climax=4,
                main_deck_stock_size=9,
            )