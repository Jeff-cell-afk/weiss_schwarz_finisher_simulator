import random
from typing import List, Optional, Tuple

from .deck import build_deck
from .models import Card, Pools

class GameSystem:
    __slots__ = (
        "main_deck", "discard", "trigger_deck", "trigger_discard", "stock",
        "clock_zone", "level_zone", "total_damage", "initial_main_count",
        "initial_trigger_count",
    )

    def __init__(self, main_deck: List[Card], trigger_deck: List[Card]):
        self.main_deck = main_deck
        self.discard: List[Card] = []
        self.trigger_deck = trigger_deck
        self.trigger_discard: List[Card] = []
        self.stock: List[Card] = []
        self.clock_zone: List[Card] = []
        self.level_zone: List[Card] = []
        self.total_damage = 0
        self.initial_main_count = len(main_deck)
        self.initial_trigger_count = len(trigger_deck)

    def _reveal_trigger_card(self) -> Optional[Card]:
        if not self.trigger_deck:
            if not self.trigger_discard:
                return None
            self.trigger_deck.extend(self.trigger_discard)
            self.trigger_discard.clear()
            random.shuffle(self.trigger_deck)
        card = self.trigger_deck.pop()
        self.stock.append(card)
        return card

    @staticmethod
    def __card_soul(card: Card) -> int:
        return card.n_triggers if card.n_triggers <= 2 else 0

    # Trigger check rule
    def trigger_check(self) -> int:
        card = self._reveal_trigger_card()
        return self.__card_soul(card) if card else 0

    # Twin drive rule
    def twin_drive_check(self) -> int:
        if self.stock:
            self.trigger_discard.append(self.stock.pop())
        total = 0
        for _ in range(2):
            card = self._reveal_trigger_card()
            if card:
                total += self.__card_soul(card)
        return total

    # Level up rule
    def levelup(self) -> None:
        while len(self.clock_zone) >= 7:
            batch = self.clock_zone[:7]
            del self.clock_zone[:7]
            idx = next((i for i, c in enumerate(batch) if c.category != "climax"), None)
            if idx is not None:
                self.level_zone.append(batch.pop(idx))
            self.discard.extend(batch)

    # Refresh penalty rule
    def refresh(self) -> bool:
        if not self.discard:
            return True
        new_deck = self.discard[:]
        self.discard.clear()
        random.shuffle(new_deck)
        self.clock_zone.append(new_deck.pop())
        self.total_damage += 1
        self.levelup()
        self.main_deck.extend(new_deck)
        return False

    def keep_cards(self, cards: List[Card]) -> None:
        self.clock_zone.extend(cards)
        self.total_damage += len(cards)
        self.levelup()

    def resolve_occurrence(self, draw_count: int, trigger_type: Optional[str]) -> bool:
        if trigger_type == "single":
            draw_count += self.trigger_check()
        elif trigger_type == "twin":
            draw_count += self.twin_drive_check()

        drawn: List[Card] = []
        while len(drawn) < draw_count:
            if not self.main_deck:
                if self.refresh():
                    return True
                continue
            card = self.main_deck.pop()
            drawn.append(card)
            if card.category == "climax":
                self.discard.extend(drawn)
                return False

        self.keep_cards(drawn)
        return False

    def run(self, parsed_occurrences: List[Tuple[int, Optional[str]]]) -> int:
        for draw_count, trigger_type in parsed_occurrences:
            if self.resolve_occurrence(draw_count, trigger_type):
                break
        return self.total_damage

    # Cards tracked, used to look for bugs and data loss
    def check_invariant(self) -> None:
        tracked = (len(self.main_deck) + len(self.discard)
                   + len(self.clock_zone) + len(self.level_zone))
        if tracked != self.initial_main_count:
            raise AssertionError(
                f"Incoherence de conservation des cartes : {tracked} cartes "
                f"trackees (main_deck+discard+clock_zone+level_zone) "
                f"pour {self.initial_main_count} au depart."
            )

        trigger_tracked = len(self.trigger_deck) + len(self.trigger_discard) + len(self.stock)
        if trigger_tracked != self.initial_trigger_count:
            raise AssertionError(
                f"Incoherence de conservation des cartes trigger : "
                f"{trigger_tracked} cartes trackees "
                f"(trigger_deck+trigger_discard+stock) "
                f"pour {self.initial_trigger_count} au depart."
            )

def run_single_trial(deck_size, climax_n, parsed_occurrences, pools: Pools,
                      trigger_deck_size, trigger_deck_climax,
                      check_invariants=False) -> int:
    main_deck = build_deck(pools.main_climax, pools.main_non_climax, deck_size, climax_n)
    trigger_deck = build_deck(pools.trigger_climax, pools.trigger_non_climax,
                               trigger_deck_size, trigger_deck_climax)
    state = GameSystem(main_deck, trigger_deck)
    damage = state.run(parsed_occurrences)
    if check_invariants:
        state.check_invariant()
    return damage
