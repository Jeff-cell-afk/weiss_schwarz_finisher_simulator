from typing import List, NamedTuple

categories = ("character", "event", "climax")
colors = ("yellow", "green", "red", "blue", "purple")

class Card(NamedTuple):
    level: int
    n_triggers: int
    category: str
    color: str

card_new = Card.__new__

def validated_card_new(cls, level: int, n_triggers: int, category: str, color: str):
    if not isinstance(level, int) or isinstance(level, bool) or level < 0:
        raise TypeError(
            f"level invalide : {level!r} (attendu un entier >= 0)"
        )
    if not isinstance(n_triggers, int) or isinstance(n_triggers, bool) or n_triggers < 0:
        raise TypeError(
            f"n_triggers invalide : {n_triggers!r} (attendu un entier >= 0)"
        )
    if category not in categories:
        raise ValueError(
            f"category invalide : {category!r} (attendu parmi {categories})"
        )
    if color not in colors:
        raise ValueError(
            f"color invalide : {color!r} (attendu parmi {colors})"
        )
    return card_new(cls, level, n_triggers, category, color)

Card.__new__ = validated_card_new

class Pools(NamedTuple):
    main_climax: List[Card]
    main_non_climax: List[Card]
    trigger_climax: List[Card]
    trigger_non_climax: List[Card]