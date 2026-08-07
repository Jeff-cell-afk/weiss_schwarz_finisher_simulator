import random
import re
from collections import deque
from typing import Deque, List, NamedTuple, Optional, Union

from .models import Card

def build_deck(climax_pool, non_climax_pool, size, climax_n) -> Deque[Card]:
    cards = random.sample(climax_pool, climax_n) + random.sample(non_climax_pool, size - climax_n)
    random.shuffle(cards)
    return deque(cards)

def build_trigger_deck_and_reserve(climax_pool, non_climax_pool, deck_size,
                                    climax_n, reserve_size: int = 0):
    n_climax = len(climax_pool)
    n_non_climax = len(non_climax_pool)

    climax_deck_idx = set(random.sample(range(n_climax), climax_n))
    non_climax_deck_idx = set(random.sample(range(n_non_climax), deck_size - climax_n))

    deck_cards = (
        [climax_pool[i] for i in climax_deck_idx]
        + [non_climax_pool[i] for i in non_climax_deck_idx]
    )
    random.shuffle(deck_cards)

    initial_stock: List[Card] = []
    if reserve_size:
        used_unified = (
            climax_deck_idx
            | {n_climax + j for j in non_climax_deck_idx}
        )
        pool_size = n_climax + n_non_climax
        available = [i for i in range(pool_size) if i not in used_unified]
        for idx in random.sample(available, reserve_size):
            if idx < n_climax:
                initial_stock.append(climax_pool[idx])
            else:
                initial_stock.append(non_climax_pool[idx - n_climax])

    return deque(deck_cards), initial_stock

class Occurrence(NamedTuple):
    draw_count: int
    trigger_type: Optional[str] = None
    cost: int = 0

class CancelBurn(NamedTuple):
    x: Occurrence
    y_list: List[Occurrence]

class MillBottomCountClimax(NamedTuple):
    x: int

class MillBottomEachClimax(NamedTuple):
    x: int
    z: Occurrence

class TopCheckLevelBurn(NamedTuple):
    

class Musashi(NamedTuple):
    x: Occurrence

_OCC_GROUPED = r"(?:\([0-9]+\))?[0-9]+[AT]?"
_CANCEL_BURN_RE = re.compile(
    rf"^({_OCC_GROUPED})-CANCELBURN/\[({_OCC_GROUPED}(?:-{_OCC_GROUPED})*)\]$"
)

_MILL_COUNT_CLIMAX_RE = re.compile(r"^MILL-BOTTOM-COUNT-CLIMAX-([0-9]+)$")

_MILL_EACH_CLIMAX_RE = re.compile(
    rf"^MILL-BOTTOM-EACH-CLIMAX-\[([0-9]+)/({_OCC_GROUPED})\]$"
)

_TOP_CHECK_LEVEL_BURN_RE = re.compile(r"^TOP-CHECK-LEVEL-BURN$")

_MUSASHI_RE = re.compile(rf"^MUSASHI-({_OCC_GROUPED})$")

_SINGLE_RE = re.compile(r"^(?:\(([0-9]+)\))?([0-9]+)([AT]?)$")

def _parse_single(spec: Union[int, str]) -> Occurrence:
    s = str(spec).strip().upper().replace(" ", "")
    match = _SINGLE_RE.match(s)
    if not match:
        raise ValueError(f"Occurrence invalide : {spec!r}")
    cost_str, draw_str, suffix = match.groups()
    cost = int(cost_str) if cost_str is not None else 0
    trigger_type = {"A": "single", "T": "twin", "": None}[suffix]
    return Occurrence(int(draw_str), trigger_type, cost)

ParsedOccurrence = Union[
    Occurrence, CancelBurn, MillBottomCountClimax, MillBottomEachClimax,
    TopCheckLevelBurn, Musashi,
]

def parse_occurrence(spec: Union[int, str]) -> ParsedOccurrence:
    s = str(spec).strip().upper().replace(" ", "")

    match = _CANCEL_BURN_RE.match(s)
    if match:
        x_spec, y_specs = match.groups()
        x = _parse_single(x_spec)
        y_list = [_parse_single(y_spec) for y_spec in y_specs.split("-")]
        return CancelBurn(x=x, y_list=y_list)

    match = _MILL_EACH_CLIMAX_RE.match(s)
    if match:
        x_spec, z_spec = match.groups()
        return MillBottomEachClimax(x=int(x_spec), z=_parse_single(z_spec))

    match = _MILL_COUNT_CLIMAX_RE.match(s)
    if match:
        return MillBottomCountClimax(x=int(match.group(1)))

    if _TOP_CHECK_LEVEL_BURN_RE.match(s):
        return TopCheckLevelBurn()

    match = _MUSASHI_RE.match(s)
    if match:
        return Musashi(x=_parse_single(match.group(1)))

    # occurrence simple : s est deja normalisee (strip + upper + sans espace).
    return _parse_single(s)

def parse_occurrences(occurrences) -> List[ParsedOccurrence]:
    return [parse_occurrence(spec) for spec in occurrences]