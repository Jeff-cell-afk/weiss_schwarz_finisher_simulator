import random
from typing import List, Optional, Tuple, Union

from .models import Card

def build_deck(climax_pool, non_climax_pool, size, climax_n) -> List[Card]:
    deck = random.sample(climax_pool, climax_n) + random.sample(non_climax_pool, size - climax_n)
    random.shuffle(deck)
    return deck

def parse_occurrence(spec: Union[int, str]) -> Tuple[int, Optional[str]]:
    """Retourne (draw_count, trigger_type) ou trigger_type vaut :
    - None     : pas de trigger
    - "single" : trigger classique (suffixe 'A')
    - "twin"   : twin drive (suffixe 'T')
    """
    s = str(spec).strip().upper()
    if s.endswith("T"):
        return (int(s[:-1]), "twin")
    if s.endswith("A"):
        return (int(s[:-1]), "single")
    return (int(s), None)

def parse_occurrences(occurrences) -> List[Tuple[int, Optional[str]]]:
    return [parse_occurrence(spec) for spec in occurrences]