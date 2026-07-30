from typing import List, NamedTuple

class Card(NamedTuple):
    level: int
    n_triggers: int
    is_climax: bool

class Pools(NamedTuple):
    main_climax: List[Card]
    main_non_climax: List[Card]
    trigger_climax: List[Card]
    trigger_non_climax: List[Card]