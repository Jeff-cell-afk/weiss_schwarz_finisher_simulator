import random
from typing import List, Tuple, Union

from .models import Card

def build_deck(climax_pool, non_climax_pool, size, climax_n) -> List[Card]:
    deck = random.sample(climax_pool, climax_n) + random.sample(non_climax_pool, size - climax_n)
    random.shuffle(deck)
    return deck

def parse_occurrence(spec: Union[int, str]) -> Tuple[int, bool]:
    s = str(spec).strip().upper()
    return (int(s[:-1]), True) if s.endswith("A") else (int(s), False)

def parse_occurrences(occurrences) -> List[Tuple[int, bool]]:
    return [parse_occurrence(spec) for spec in occurrences]