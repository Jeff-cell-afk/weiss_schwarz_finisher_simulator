from __future__ import annotations

import re
import math
from dataclasses import dataclass
from typing import ClassVar, List, Optional, Tuple, TYPE_CHECKING, Union

from .models import Card

if TYPE_CHECKING:
    from .game_system import GameSystem

_TRIGGER_DAMAGE_BONUS = {None: 0, "single": 2, "twin": 4}
_TRIGGER_STOCK_BONUS = {None: 0, "single": 1, "twin": 2}
_COLORS = {"YELLOW", "GREEN", "RED", "BLUE", "PURPLE"}


class Effect:
    
    JOINT_COST: ClassVar[bool] = False

    def resolve(self, gs: "GameSystem") -> bool:
        raise NotImplementedError

    def max_damage(self, ctx: "BoundContext") -> int:
        raise NotImplementedError


_TRIGGER_CHECK_COUNT = {None: 0, "single": 1, "twin": 2}


@dataclass(frozen=True)
class Burn(Effect):
    n: int
    trigger: Optional[str] = None
    on_reveal: Optional[Tuple["Condition", "Occurrence"]] = None

    def __post_init__(self):
        if self.n < 0:
            raise ValueError(f"Burn.n must be >= 0, got {self.n!r}")
        if self.trigger not in (None, "single", "twin"):
            raise ValueError(f"invalid trigger: {self.trigger!r}")
        if self.on_reveal is not None and self.trigger is None:
            raise ValueError(
                "Burn.on_reveal requires a trigger ('single' or 'twin'): "
                "ONREVEAL inspects the card(s) revealed by the trigger "
                "check, so there must be a trigger check to hook into."
            )

    def resolve(self, gs: "GameSystem") -> bool:
        if self.on_reveal is None:
            return gs.resolution(self.n, self.trigger)

        condition, then = self.on_reveal
        n_checks = _TRIGGER_CHECK_COUNT[self.trigger]
        bonus, cards = gs.reveal_trigger_cards(n_checks)
        for card in cards:
            if condition.matches(card):
                then.resolve(gs)
        return gs.resolution_core(self.n + bonus)

    def max_damage(self, ctx: "BoundContext") -> int:
        base = self.n + _TRIGGER_DAMAGE_BONUS[self.trigger]
        if self.on_reveal is not None:
            n_checks = _TRIGGER_CHECK_COUNT[self.trigger]
            _, then = self.on_reveal
            base += n_checks * then.max_damage(ctx)
        return base


@dataclass(frozen=True)
class Shuffle(Effect):
    JOINT_COST: ClassVar[bool] = True

    x: int
    then: "Occurrence"

    def __post_init__(self):
        if self.x < 0:
            raise ValueError(f"Shuffle.x must be >= 0, got {self.x!r}")

    def resolve(self, gs: "GameSystem") -> bool:
        raise TypeError(
            "Shuffle.resolve() must not be called directly - Occurrence.resolve() "
            "dispatches JOINT_COST effects to resolve_joint() instead, since the "
            "post_cost payment must happen between the shuffle action and `then`."
        )

    def resolve_joint(self, gs: "GameSystem", cost_after: int) -> bool:
        gs.shuffle_discard_into_main(self.x)
        if cost_after:
            gs.pay_trigger(cost_after)
        return self.then.resolve(gs)

    def max_damage(self, ctx: "BoundContext") -> int:
        return self.then.max_damage(ctx)


@dataclass(frozen=True)
class OnCancel(Effect):
    primary: "Occurrence"
    then: Tuple["Occurrence", ...]

    def resolve(self, gs: "GameSystem") -> bool:
        canceled = self.primary.resolve(gs)
        if canceled:
            for occ in self.then:
                occ.resolve(gs)
        return canceled

    def max_damage(self, ctx: "BoundContext") -> int:
        x_value = self.primary.max_damage(ctx)
        then_value = sum(occ.max_damage(ctx) for occ in self.then)
        return max(x_value, then_value)


@dataclass(frozen=True)
class Mill(Effect):
    n: int
    target: str
    edge: str
    mode: str
    then: Optional["Occurrence"] = None
    offset: int = 0
    condition: Optional["Condition"] = None

    def __post_init__(self):
        if self.n < 1:
            raise ValueError(f"Mill.n must be >= 1, got {self.n!r}")
        if self.target not in ("self", "opp"):
            raise ValueError(f"invalid Mill target: {self.target!r} (expected 'self' or 'opp')")
        if self.edge not in ("top", "bottom"):
            raise ValueError(f"invalid Mill edge: {self.edge!r} (expected 'top' or 'bottom')")
        if self.mode not in ("count", "each", "level", "if"):
            raise ValueError(f"invalid Mill mode: {self.mode!r}")
        if self.mode in ("each", "if") and self.then is None:
            raise ValueError(f"Mill(...){self.mode.upper()}... requires an inner occurrence")
        if self.mode not in ("each", "if") and self.then is not None:
            raise ValueError(f"Mill mode {self.mode!r} does not take an inner occurrence")
        if self.mode in ("level", "if") and self.n != 1:
            raise ValueError(
                f"Mill(...){self.mode.upper()} is only valid for a single "
                f"milled card (n=1), got n={self.n!r}. A single-card check "
                f"(level or condition) has no defined meaning for several "
                f"cards milled at once - use MILL({self.n})...COUNT "
                f"(climax count) or MILL({self.n})...EACH[...] instead if "
                f"that's what you intended."
            )
        if self.offset != 0 and self.mode != "level":
            raise ValueError("Mill.offset is only meaningful in LEVEL mode")
        if self.mode == "if" and self.condition is None:
            raise ValueError('Mill(...)IF "..." THEN ... requires a condition')
        if self.mode != "if" and self.condition is not None:
            raise ValueError("Mill.condition is only meaningful in IF mode")

    def resolve(self, gs: "GameSystem") -> bool:
        climax_count, milled = gs.mill(self.n, self.target, self.edge)
        if self.mode == "count":
            return gs.resolution(climax_count, None)
        if self.mode == "level":
            card = milled[0]
            return gs.resolution(card.level + self.offset, None)
        if self.mode == "if":
            card = milled[0]
            assert self.condition is not None and self.then is not None
            if self.condition.matches(card):
                return self.then.resolve(gs)
            return False
        assert self.then is not None
        for _ in range(climax_count):
            self.then.resolve(gs)
        return False

    def max_damage(self, ctx: "BoundContext") -> int:
        if self.mode == "count":
            return self.n
        if self.mode == "level":
            max_level = ctx.max_trigger_level if self.target == "self" else ctx.max_main_level
            return max_level + self.offset
        if self.mode == "if":
            assert self.then is not None
            return self.then.max_damage(ctx)
        assert self.then is not None
        return self.n * self.then.max_damage(ctx)


@dataclass(frozen=True)
class Condition:
    colors: Optional[Tuple[str, ...]] = None
    card_type: str = "card"
    level_cmp: Optional[str] = None
    level_value: Optional[int] = None

    def __post_init__(self):
        if self.level_cmp is not None and self.level_cmp not in ("=", ">=", "<="):
            raise ValueError(f"invalid level comparator: {self.level_cmp!r}")
        if (self.level_cmp is None) != (self.level_value is None):
            raise ValueError("level_cmp and level_value must be both set or both None")

    def matches(self, card: Card) -> bool:
        if self.colors is not None and card.color.upper() not in self.colors:
            return False
        if self.level_cmp is not None:
            assert self.level_value is not None
            if self.level_cmp == "=" and card.level != self.level_value:
                return False
            if self.level_cmp == ">=" and card.level < self.level_value:
                return False
            if self.level_cmp == "<=" and card.level > self.level_value:
                return False
        if self.card_type == "card":
            return True
        if self.card_type == "climax":
            return card.category == "climax"
        if self.card_type == "non-climax":
            return card.category != "climax"
        return card.category == self.card_type


@dataclass(frozen=True)
class TopCheck(Effect):
    condition: Optional[Condition] = None
    then: Optional["Occurrence"] = None

    def __post_init__(self):
        if (self.condition is None) != (self.then is None):
            raise ValueError(
                "TopCheck: condition and then must be both set (conditional "
                "form) or both None (bare peek-level form)"
            )

    def resolve(self, gs: "GameSystem") -> bool:
        card = gs.peek_trigger_top()
        if self.condition is None:
            return Occurrence(effect=Burn(card.level)).resolve(gs)
        if self.condition.matches(card):
            assert self.then is not None
            return self.then.resolve(gs)
        return False

    def max_damage(self, ctx: "BoundContext") -> int:
        if self.condition is None:
            return ctx.max_trigger_level
        assert self.then is not None
        return self.then.max_damage(ctx)


class ZeroDamageEffect(Effect):
    def max_damage(self, ctx: "BoundContext") -> int:
        return 0


@dataclass(frozen=True)
class StockSwap(ZeroDamageEffect):
    def resolve(self, gs: "GameSystem") -> bool:
        gs.stock_swap()
        return False


@dataclass(frozen=True)
class StockShuffle(ZeroDamageEffect):
    def resolve(self, gs: "GameSystem") -> bool:
        gs.stock_shuffle()
        return False


@dataclass(frozen=True)
class ShuffleAll(ZeroDamageEffect):
    x: int

    def __post_init__(self):
        if self.x < 0:
            raise ValueError(f"ShuffleAll.x must be >= 0, got {self.x!r}")

    def resolve(self, gs: "GameSystem") -> bool:
        gs.shuffle_all_but_climax_reserve(self.x)
        return False




@dataclass(frozen=True)
class Occurrence:
    effect: Effect
    cost: int = 0
    post_cost: int = 0
    follow_up: Optional["Occurrence"] = None

    def __post_init__(self):
        if self.cost < 0 or self.post_cost < 0:
            raise ValueError("cost/post_cost must be >= 0")
        if self.effect.JOINT_COST:
            if self.follow_up is not None:
                raise ValueError(
                    f"{type(self.effect).__name__} does not support a "
                    f"chained follow_up via [next]: its own inner "
                    f"'then'/'->' occurrence already plays that role."
                )
        elif self.post_cost != 0:
            raise ValueError(
                f"post_cost is only meaningful for JOINT_COST effects "
                f"(Shuffle); {type(self.effect).__name__} has none. To "
                f"express a second, independently-gated cost, chain a "
                f"follow_up occurrence with its own leading cost instead "
                f"(e.g. 'BURN(3)[(1)BURN(4)]')."
            )

    def resolve(self, gs: "GameSystem") -> bool:
        if self.effect.JOINT_COST:
            assert isinstance(self.effect, Shuffle)
            total = self.cost + self.post_cost
            if total > 0 and not gs.can_pay_trigger(total):
                return False
            if self.cost:
                gs.pay_trigger(self.cost)
            return self.effect.resolve_joint(gs, self.post_cost)

        if self.cost > 0:
            if not gs.can_pay_trigger(self.cost):
                return False
            gs.pay_trigger(self.cost)

        canceled = self.effect.resolve(gs)

        if self.follow_up is not None:
            self.follow_up.resolve(gs)

        return canceled

    def max_damage(self, ctx: "BoundContext") -> int:
        value = self.effect.max_damage(ctx)
        if self.follow_up is not None:
            value += self.follow_up.max_damage(ctx)
        return value


@dataclass(frozen=True)
class BoundContext:
    max_trigger_level: int = 0
    max_main_level: int = 0



def walk_occurrences(occ: "Occurrence", mult: int = 1):
    yield occ, mult
    if occ.follow_up is not None:
        yield from walk_occurrences(occ.follow_up, mult)

    effect = occ.effect
    if isinstance(effect, OnCancel):
        yield from walk_occurrences(effect.primary, mult)
        for sub in effect.then:
            yield from walk_occurrences(sub, mult)
    elif isinstance(effect, Shuffle):
        yield from walk_occurrences(effect.then, mult)
    elif isinstance(effect, Burn) and effect.on_reveal is not None:
        _condition, then = effect.on_reveal
        yield from walk_occurrences(then, mult * _TRIGGER_CHECK_COUNT[effect.trigger])
    elif isinstance(effect, Mill):
        if effect.mode == "each":
            assert effect.then is not None
            yield from walk_occurrences(effect.then, mult * effect.n)
        elif effect.mode == "if":
            assert effect.then is not None
            yield from walk_occurrences(effect.then, mult)
    elif isinstance(effect, TopCheck):
        if effect.then is not None:
            yield from walk_occurrences(effect.then, mult)


def max_possible_stock_gain(occurrences: List["Occurrence"], trigger_deck_stock_size: int = 0) -> int:
    total = trigger_deck_stock_size
    for occ in occurrences:
        for o, mult in walk_occurrences(occ):
            if isinstance(o.effect, Burn):
                total += mult * _TRIGGER_STOCK_BONUS[o.effect.trigger]
    return total


def validate_occurrence_costs(occurrences: List["Occurrence"], trigger_deck_stock_size: int = 0) -> None:
    max_stock = max_possible_stock_gain(occurrences, trigger_deck_stock_size)

    for occ in occurrences:
        for o, _mult in walk_occurrences(occ):
            if o.effect.JOINT_COST:
                total_cost = o.cost + o.post_cost
                if total_cost > max_stock:
                    raise ValueError(
                        f"Structurally unpayable cost: {type(o.effect).__name__} "
                        f"{o.effect!r} requires cost + post_cost = {total_cost} "
                        f"paid simultaneously (no trigger check happens between "
                        f"the two payments), but at most {max_stock} cards can "
                        f"theoretically be found in self.trigger_deck_stock during a trial "
                        f"(trigger_deck_stock_size={trigger_deck_stock_size} + trigger "
                        f"checks at best across the whole sequence). This cost "
                        f"can never be paid - check its value or increase "
                        f"trigger_deck_stock_size."
                    )
            elif o.cost > max_stock:
                raise ValueError(
                    f"Structurally unpayable cost: occurrence with "
                    f"effect {o.effect!r} requires a cost of "
                    f"{o.cost}, but at most {max_stock} cards can "
                    f"theoretically be found in self.trigger_deck_stock during a "
                    f"trial (trigger_deck_stock_size={trigger_deck_stock_size} + "
                    f"trigger checks at best across the whole "
                    f"sequence). This cost can never be paid - check "
                    f"its value or increase trigger_deck_stock_size."
                )


def max_possible_damage(occurrences: List["Occurrence"], deck_size_list=None,
                         max_trigger_level: int = 0, max_main_level: int = 0) -> int:
    ctx = BoundContext(max_trigger_level=max_trigger_level, max_main_level=max_main_level)
    base = sum(occ.max_damage(ctx) for occ in occurrences)
    if not deck_size_list:
        return base
    max_refreshes = math.ceil(base / min(deck_size_list))
    return base + max_refreshes



_BRACKET_PAIRS = {")": "(", "]": "["}


def check_balanced(spec: str) -> None:
    stack: List[Tuple[str, int]] = []
    for i, ch in enumerate(spec):
        if ch in "([":
            stack.append((ch, i))
        elif ch in ")]":
            if not stack or stack[-1][0] != _BRACKET_PAIRS[ch]:
                raise ValueError(
                    f"Unbalanced parenthesis/bracket at position {i} "
                    f"in {spec!r} ('{ch}' with no matching "
                    f"'{_BRACKET_PAIRS[ch]}')."
                )
            stack.pop()
    if stack:
        char, pos = stack[0]
        raise ValueError(f"'{char}' opened at position {pos} is never closed in {spec!r}.")



@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    pos: int


_TOKEN_RE = re.compile(
    r"""
      (?P<STRING>"[^"]*")
    | (?P<NUMBER>\d+)
    | (?P<ARROW>->)
    | (?P<SLASHTRIG>/[ATat])
    | (?P<IDENT>[A-Za-z][A-Za-z]*)
    | (?P<PLUS>\+)
    | (?P<LPAREN>\()
    | (?P<RPAREN>\))
    | (?P<LBRACKET>\[)
    | (?P<RBRACKET>\])
    | (?P<SEMI>;)
    | (?P<WS>\s+)
    | (?P<UNKNOWN>.)
    """,
    re.VERBOSE,
)

def tokenize(spec: str) -> List[Token]:
    tokens: List[Token] = []
    for m in _TOKEN_RE.finditer(spec):
        kind = m.lastgroup
        if kind == "WS":
            continue
        if kind == "UNKNOWN":
            raise ValueError(f"Unexpected character {m.group()!r} at position {m.start()} in {spec!r}")
        tokens.append(Token(kind, m.group(), m.start()))
    return tokens



class _Parser:
    def __init__(self, tokens: List[Token], original: str):
        self.tokens = tokens
        self.i = 0
        self.original = original

    def _peek(self) -> Optional[Token]:
        return self.tokens[self.i] if self.i < len(self.tokens) else None

    def _peek_ident(self) -> Optional[str]:
        tok = self._peek()
        return tok.value.upper() if tok and tok.kind == "IDENT" else None

    def _advance(self) -> Token:
        tok = self._peek()
        if tok is None:
            raise ValueError(f"Unexpected end of spec in {self.original!r}")
        self.i += 1
        return tok

    def _expect(self, kind: str) -> Token:
        tok = self._peek()
        if tok is None or tok.kind != kind:
            got = f"{tok.kind}({tok.value!r})" if tok else "end of input"
            raise ValueError(f"Expected {kind} but got {got} in {self.original!r}")
        return self._advance()

    def _expect_ident(self, *names: str) -> str:
        tok = self._peek()
        val = tok.value.upper() if tok and tok.kind == "IDENT" else None
        if val not in names:
            got = f"{tok.kind}({tok.value!r})" if tok else "end of input"
            raise ValueError(f"Expected one of {names} but got {got} in {self.original!r}")
        self._advance()
        return val

    def _expect_int(self) -> int:
        return int(self._expect("NUMBER").value)

    def _at_end(self) -> bool:
        return self.i >= len(self.tokens)

    def parse_sequence(self, depth: int = 0) -> List[Occurrence]:
        self._expect("LBRACKET")
        occs = [self.parse_occurrence(depth + 1)]
        while self._peek() is not None and self._peek().kind == "SEMI":
            self._advance()
            occs.append(self.parse_occurrence(depth + 1))
        self._expect("RBRACKET")
        return occs

    def parse_occurrence(self, depth: int = 0) -> Occurrence:
        ident = self._peek_ident()
        if ident == "SHUFFLE":
            return self._parse_shuffle(depth, cost_before=0)

        cost = 0
        if self._peek() is not None and self._peek().kind == "LPAREN":
            self._advance()
            cost = self._expect_int()
            self._expect("RPAREN")
            if self._peek_ident() == "SHUFFLE":
                return self._parse_shuffle(depth, cost_before=cost)

        effect = self.parse_effect(depth)

        follow_up = None
        if self._peek() is not None and self._peek().kind == "LBRACKET":
            self._advance()
            follow_up = self.parse_occurrence(depth + 1)
            self._expect("RBRACKET")

        return Occurrence(effect=effect, cost=cost, follow_up=follow_up)

    def _parse_shuffle(self, depth: int, cost_before: int) -> Occurrence:
        self._expect_ident("SHUFFLE")
        self._expect("LPAREN")
        x = self._expect_int()
        self._expect("RPAREN")

        cost_after = 0
        if self._peek() is not None and self._peek().kind == "LPAREN":
            self._advance()
            cost_after = self._expect_int()
            self._expect("RPAREN")

        self._expect("ARROW")
        then = self.parse_occurrence(depth + 1)

        return Occurrence(
            effect=Shuffle(x=x, then=then), cost=cost_before, post_cost=cost_after
        )

    def parse_effect(self, depth: int) -> Effect:
        ident = self._peek_ident()
        if ident == "BURN":
            return self._parse_burn(depth)
        if ident == "ONCANCEL":
            return self._parse_oncancel(depth)
        if ident == "MILL":
            return self._parse_mill(depth)
        if ident == "TOPCHECK":
            return self._parse_topcheck(depth)
        if ident == "STOCKSWAP":
            self._advance()
            return StockSwap()
        if ident == "STOCKSHUFFLE":
            self._advance()
            return StockShuffle()
        if ident == "SHUFFLEALL":
            return self._parse_shuffle_all()
        tok = self._peek()
        got = f"{tok.kind}({tok.value!r})" if tok else "end of input"
        raise ValueError(
            f"Expected one of BURN/SHUFFLE/ONCANCEL/MILL/TOPCHECK/STOCKSWAP/"
            f"STOCKSHUFFLE/SHUFFLEALL but got {got} in {self.original!r}"
        )

    def _parse_burn(self, depth: int = 0) -> Burn:
        self._expect_ident("BURN")
        self._expect("LPAREN")
        n = self._expect_int()
        self._expect("RPAREN")
        trigger = None
        if self._peek() is not None and self._peek().kind == "SLASHTRIG":
            tok = self._advance()
            suffix = tok.value[1].upper()
            trigger = "single" if suffix == "A" else "twin"

        on_reveal = None
        if self._peek_ident() == "ONREVEAL":
            self._advance()
            raw = self._expect("STRING").value[1:-1] 
            condition = parse_condition(raw)
            self._expect_ident("THEN")
            then = self.parse_occurrence(depth + 1)
            on_reveal = (condition, then)

        return Burn(n=n, trigger=trigger, on_reveal=on_reveal)

    def _parse_shuffle_all(self) -> ShuffleAll:
        self._expect_ident("SHUFFLEALL")
        self._expect("LPAREN")
        x = self._expect_int()
        self._expect("RPAREN")
        return ShuffleAll(x=x)

    def _parse_oncancel(self, depth: int) -> OnCancel:
        self._expect_ident("ONCANCEL")
        then = tuple(self.parse_sequence(depth))
        self._expect_ident("ON")
        primary = self.parse_occurrence(depth + 1)
        return OnCancel(primary=primary, then=then)

    def _parse_mill(self, depth: int) -> Mill:
        self._expect_ident("MILL")
        self._expect("LPAREN")
        n = self._expect_int()
        self._expect("RPAREN")
        target_kw = self._expect_ident("SELF", "OPP")
        target = "self" if target_kw == "SELF" else "opp"
        edge = self._expect_ident("TOP", "BOTTOM").lower()

        mode_kw = self._expect_ident("COUNT", "EACH", "LEVEL", "IF")
        if mode_kw == "COUNT":
            return Mill(n=n, target=target, edge=edge, mode="count")
        if mode_kw == "EACH":
            self._expect("LBRACKET")
            then = self.parse_occurrence(depth + 1)
            self._expect("RBRACKET")
            return Mill(n=n, target=target, edge=edge, mode="each", then=then)
        if mode_kw == "IF":
            raw = self._expect("STRING").value[1:-1]  
            condition = parse_condition(raw)
            self._expect_ident("THEN")
            then = self.parse_occurrence(depth + 1)
            return Mill(n=n, target=target, edge=edge, mode="if", condition=condition, then=then)
        offset = 0
        if self._peek() is not None and self._peek().kind == "PLUS":
            self._advance()
            offset = self._expect_int()
        return Mill(n=n, target=target, edge=edge, mode="level", offset=offset)

    def _parse_topcheck(self, depth: int) -> TopCheck:
        self._expect_ident("TOPCHECK")
        if self._peek() is None or self._peek_ident() != "IF":
            return TopCheck()
        self._advance()  # IF
        raw = self._expect("STRING").value[1:-1]  
        condition = parse_condition(raw)
        self._expect_ident("THEN")
        then = self.parse_occurrence(depth + 1)
        return TopCheck(condition=condition, then=then)


_LEVEL_CLAUSE_RE = re.compile(r"^LEVEL\s*(=|>=|<=)\s*(\d+)\s*")


def parse_condition(text: str) -> Condition:
    normalized = " ".join(text.upper().replace("-", " ").split())
    if not normalized:
        raise ValueError("Empty condition string")

    level_cmp = None
    level_value = None
    level_match = _LEVEL_CLAUSE_RE.match(normalized)
    if level_match:
        level_cmp, level_value = level_match.group(1), int(level_match.group(2))
        normalized = normalized[level_match.end():].strip()

    type_map = {
        "NON CLIMAX CARD": "non-climax",
        "CLIMAX CARD": "climax",
        "CHARACTER CARD": "character",
        "EVENT CARD": "event",
        "CARD": "card",
    }
    card_type = None
    color_part = normalized
    if normalized:
        for phrase, mapped in sorted(type_map.items(), key=lambda kv: -len(kv[0])):
            if normalized.endswith(phrase):
                card_type = mapped
                color_part = normalized[: -len(phrase)].strip()
                break

    if card_type is None:
        if level_cmp is None:
            raise ValueError(
                f"Condition {text!r}: no recognized card type suffix "
                f"(expected one of {sorted(type_map)}, or a leading LEVEL "
                f"clause to make it optional)"
            )
        card_type = "card"

    colors = None
    if color_part:
        color_words = [w for w in color_part.split() if w != "OR"]
        for w in color_words:
            if w not in _COLORS:
                raise ValueError(f"Condition {text!r}: unknown color {w!r}")
        colors = tuple(color_words)

    return Condition(colors=colors, card_type=card_type, level_cmp=level_cmp, level_value=level_value)


def parse_occurrence(spec: str) -> Occurrence:
    check_balanced(spec)
    tokens = tokenize(spec)
    parser = _Parser(tokens, spec)
    occ = parser.parse_occurrence()
    if not parser._at_end():
        tok = parser._peek()
        raise ValueError(
            f"Invalid occurrence (extra characters after parsing): {spec!r} "
            f"(unexpected {tok.kind}({tok.value!r}) at position {tok.pos})"
        )
    return occ


def parse_occurrences(specs: List[Union[str, int]]) -> List[Occurrence]:
    return [parse_occurrence(str(spec)) for spec in specs]
