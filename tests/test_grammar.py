import pytest

from simulateur.grammar import (
    BoundContext, Burn, Condition, Mill, Occurrence, OnCancel, Scry, Shuffle,
    ShuffleAll, StockShuffle, StockSwap, TopCheck, check_balanced,
    max_possible_damage, parse_condition, parse_occurrence, parse_occurrences,
    tokenize,
)


class TestCheckBalanced:
    def test_balanced_parens_and_brackets_pass(self):
        check_balanced('BURN(3)[BURN(2)]')  # should not raise

    def test_unmatched_closing_paren_raises(self):
        with pytest.raises(ValueError, match="no matching"):
            check_balanced("BURN(3))")

    def test_unclosed_opening_bracket_raises(self):
        with pytest.raises(ValueError, match="never closed"):
            check_balanced("ONCANCEL[BURN(1)")

    def test_mismatched_bracket_kind_raises(self):
        with pytest.raises(ValueError):
            check_balanced("BURN(3]")


class TestTokenize:
    def test_simple_burn(self):
        tokens = tokenize("BURN(3)")
        kinds = [t.kind for t in tokens]
        assert kinds == ["IDENT", "LPAREN", "NUMBER", "RPAREN"]

    def test_trigger_suffix(self):
        tokens = tokenize("BURN(2)/T")
        assert tokens[-1].kind == "SLASHTRIG"
        assert tokens[-1].value == "/T"

    def test_string_literal(self):
        tokens = tokenize('IF "Blue or Yellow Non-Climax Card" THEN')
        string_tokens = [t for t in tokens if t.kind == "STRING"]
        assert len(string_tokens) == 1
        assert string_tokens[0].value == '"Blue or Yellow Non-Climax Card"'

    def test_whitespace_is_skipped(self):
        # Token carries a `pos` field, so compare kind/value only —
        # positions legitimately differ once leading whitespace is added.
        as_pairs = lambda toks: [(t.kind, t.value) for t in toks]
        assert as_pairs(tokenize("BURN(3)")) == as_pairs(tokenize("  BURN( 3 )  "))

    def test_unknown_character_raises(self):
        with pytest.raises(ValueError, match="Unexpected character"):
            tokenize("BURN(3)#")


class TestParseCondition:
    def test_bare_card_matches_anything(self):
        cond = parse_condition("Card")
        assert cond.matches(_card("climax", "red", level=9))

    def test_climax_type(self):
        cond = parse_condition("Climax Card")
        assert cond.matches(_card("climax", "yellow"))
        assert not cond.matches(_card("character", "yellow"))

    def test_non_climax_type(self):
        cond = parse_condition("Non-Climax Card")
        assert cond.matches(_card("character", "yellow"))
        assert not cond.matches(_card("climax", "yellow"))

    def test_character_type(self):
        cond = parse_condition("Character Card")
        assert cond.matches(_card("character", "yellow"))
        assert not cond.matches(_card("event", "yellow"))

    def test_single_color_filter(self):
        cond = parse_condition("Blue Card")
        assert cond.matches(_card("character", "blue"))
        assert not cond.matches(_card("character", "red"))

    def test_multi_color_filter(self):
        cond = parse_condition("Blue or Yellow Non-Climax Card")
        assert cond.matches(_card("character", "blue"))
        assert cond.matches(_card("character", "yellow"))
        assert not cond.matches(_card("character", "red"))
        assert not cond.matches(_card("climax", "blue"))


class TestParseOccurrenceBurn:
    def test_plain_burn(self):
        occ = parse_occurrence("BURN(4)")
        assert isinstance(occ, Occurrence)
        assert isinstance(occ.effect, Burn)
        assert occ.effect.n == 4
        assert occ.effect.trigger is None

    def test_burn_with_single_trigger(self):
        occ = parse_occurrence("BURN(3)/A")
        assert occ.effect.trigger == "single"

    def test_burn_with_twin_trigger(self):
        occ = parse_occurrence("BURN(3)/T")
        assert occ.effect.trigger == "twin"

    def test_burn_with_cost(self):
        occ = parse_occurrence("(1)BURN(3)")
        assert occ.cost == 1
        assert occ.effect.n == 3

    def test_onreveal_requires_trigger(self):
        # ONREVEAL needs a card to inspect, which only exists with a trigger check
        with pytest.raises(ValueError):
            Burn(3, trigger=None, on_reveal=(Condition(), parse_occurrence("BURN(1)")))

    def test_onreveal_parses_with_trigger(self):
        # single-type condition (works today; the multi-type "X or Y Card"
        # form from the README does not - see test below)
        occ = parse_occurrence(
            'BURN(3)/T ONREVEAL "Character Card" THEN BURN(3)'
        )
        assert occ.effect.trigger == "twin"
        assert occ.effect.on_reveal is not None


class TestParseOccurrenceMill:
    def test_mill_count_mode(self):
        occ = parse_occurrence("MILL(2) OPP BOTTOM COUNT")
        assert isinstance(occ.effect, Mill)
        assert occ.effect.n == 2
        assert occ.effect.target == "opp"
        assert occ.effect.edge == "bottom"
        assert occ.effect.mode == "count"

    def test_mill_each_mode(self):
        occ = parse_occurrence("MILL(2) OPP BOTTOM EACH[BURN(2)]")
        assert occ.effect.mode == "each"
        assert occ.effect.then is not None

    def test_mill_level_mode_requires_n_equal_1(self):
        with pytest.raises(ValueError, match="only valid for a single"):
            Mill(n=2, target="self", edge="top", mode="level")


class TestParseOccurrenceOthers:
    def test_topcheck_bare(self):
        occ = parse_occurrence(
            'TOPCHECK IF "Blue or Yellow Non-Climax Card" THEN BURN(3)'
        )
        assert isinstance(occ.effect, TopCheck)

    def test_shuffle(self):
        occ = parse_occurrence("SHUFFLE(2)->BURN(2)")
        assert isinstance(occ.effect, Shuffle)
        assert occ.effect.x == 2

    def test_shuffle_all(self):
        occ = parse_occurrence("SHUFFLEALL(1)")
        assert isinstance(occ.effect, ShuffleAll)
        assert occ.effect.x == 1

    def test_oncancel(self):
        occ = parse_occurrence("ONCANCEL[BURN(1);BURN(1)] ON BURN(3)")
        assert isinstance(occ.effect, OnCancel)
        assert len(occ.effect.then) == 2

    def test_stock_swap(self):
        occ = parse_occurrence("STOCKSWAP")
        assert isinstance(occ.effect, StockSwap)

    def test_stock_shuffle(self):
        occ = parse_occurrence("STOCKSHUFFLE")
        assert isinstance(occ.effect, StockShuffle)

    def test_scry(self):
        occ = parse_occurrence("SCRY(3)")
        assert isinstance(occ.effect, Scry)
        assert occ.effect.n == 3


class TestParseOccurrenceErrors:
    def test_unknown_keyword_raises(self):
        with pytest.raises(ValueError):
            parse_occurrence("NOTAKEYWORD(3)")

    def test_trailing_garbage_raises(self):
        with pytest.raises(ValueError):
            parse_occurrence("BURN(3) BURN(4)")

    def test_unbalanced_parens_raises(self):
        with pytest.raises(ValueError):
            parse_occurrence("BURN(3")


class TestParseOccurrences:
    def test_list_of_strings(self):
        occs = parse_occurrences(["BURN(4)", "BURN(3)/A"])
        assert len(occs) == 2
        assert all(isinstance(o, Occurrence) for o in occs)


class TestMaxPossibleDamage:
    def test_sums_static_damage(self):
        occs = parse_occurrences(["BURN(4)", "BURN(3)"])
        ctx_damage = max_possible_damage(occs)
        assert ctx_damage == 7

    def test_trigger_bonus_included(self):
        occs = parse_occurrences(["BURN(3)/T"])
        # twin trigger adds up to +4 static bonus (2 soul-trigger checks)
        assert max_possible_damage(occs) == 3 + 4

    def test_refresh_padding_added_when_deck_sizes_given(self):
        occs = parse_occurrences(["BURN(4)"])
        without_refresh = max_possible_damage(occs)
        with_refresh = max_possible_damage(occs, deck_size_list=[10])
        assert with_refresh >= without_refresh


def _card(category, color, level=1):
    from simulateur.models import Card
    return Card(level, 0, category, color)