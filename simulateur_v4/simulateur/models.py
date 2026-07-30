from dataclasses import dataclass, field
from typing import List

categories = ("character", "event", "climax")
colors = ("yellow", "green", "red", "blue", "purple")

@dataclass(frozen=True)
class Card:
    level: int
    n_triggers: int
    category: str
    color: str

    def __post_init__(self):
        if not isinstance(self.level, int) or isinstance(self.level, bool) or self.level < 0:
            raise TypeError(
                f"level invalide : {self.level!r} (attendu un entier >= 0)"
            )
        if not isinstance(self.n_triggers, int) or isinstance(self.n_triggers, bool) or self.n_triggers < 0:
            raise TypeError(
                f"n_triggers invalide : {self.n_triggers!r} (attendu un entier >= 0)"
            )
        if self.category not in categories:
            raise ValueError(
                f"category invalide : {self.category!r} (attendu parmi {categories})"
            )
        if self.color not in colors:
            raise ValueError(
                f"color invalide : {self.color!r} (attendu parmi {colors})"
            )

@dataclass(frozen=True)
class Pools:
    main_climax: List[Card] = field(default_factory=list)
    main_non_climax: List[Card] = field(default_factory=list)
    trigger_climax: List[Card] = field(default_factory=list)
    trigger_non_climax: List[Card] = field(default_factory=list)