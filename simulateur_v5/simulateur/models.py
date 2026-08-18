import itertools
from dataclasses import dataclass, field
from typing import List

# Initial non-numeric parameters
categories = ("character", "event", "climax")
colors = ("yellow", "green", "red", "blue", "purple")

# The two following functions are used to separate booleans from levels and trigger number, which can take the zero and one value
def _is_valid_positive_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0

def _is_valid_nonnegative_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0

@dataclass(frozen=True)
# Core definition : a deck is a pile of cards we manipulate with functions, we need exhaustivity as much as precision
class Card:
    level: int
    n_triggers: int
    category: str
    color: str

    # Frozen dataclasses can't validated directly in __init__ , this function is used to bypass this problem
    def __post_init__(self):
        self._validate_field("level", self.level, allow_zero=True)
        self._validate_field("n_triggers", self.n_triggers, allow_zero=True)
        if self.category not in categories:
            raise ValueError(
                f"invalid category: {self.category!r} (expected one of {categories})"
            )
        if self.color not in colors:
            raise ValueError(
                f"invalid color: {self.color!r} (expected one of {colors})"
            )

    @staticmethod
    def _validate_field(name: str, value, allow_zero: bool = False) -> None:
        is_valid = _is_valid_nonnegative_int(value) if allow_zero else _is_valid_positive_int(value)
        if not is_valid:
            raise TypeError(
                f"invalid {name}: {value!r} (expected an integer "
                f"{'>= 0' if allow_zero else '> 0'})"
            )


@dataclass(frozen=True)

# Initial class used to build our card pools, we need to separate climax cards from the rest in both decks
class Pools:
    main_climax: List[Card] = field(default_factory=list)
    main_non_climax: List[Card] = field(default_factory=list)
    trigger_climax: List[Card] = field(default_factory=list)
    trigger_non_climax: List[Card] = field(default_factory=list)

    # The output of this simulation is a probability table, which we calculate the theoretical upper limit here
    @property
    def max_trigger_level(self) -> int:
        if not hasattr(self, '_max_trigger_level'):
            levels = [c.level for c in itertools.chain(self.trigger_climax, self.trigger_non_climax)]
            object.__setattr__(self, '_max_trigger_level', max(levels, default=0))
        return self._max_trigger_level

    @property
    def max_main_level(self) -> int:
        if not hasattr(self, '_max_main_level'):
            levels = [c.level for c in itertools.chain(self.main_climax, self.main_non_climax)]
            object.__setattr__(self, '_max_main_level', max(levels, default=0))
        return self._max_main_level
