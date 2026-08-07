import random
from typing import Deque, List, Optional

from .deck import (
    build_deck, build_trigger_deck_and_reserve, CancelBurn,
    MillBottomCountClimax, MillBottomEachClimax, Musashi, ParsedOccurrence,
    TopCheckLevelBurn,
)
from .models import Card, Pools

class SystemBrokenError(RuntimeError):
    
class GameSystem:
    __slots__ = (
        "main_deck", "discard", "trigger_deck", "trigger_discard", "stock",
        "clock_zone", "level_zone", "total_damage", "initial_main_count",
        "initial_trigger_count", "initial_stock_count",
    )

    def __init__(self, main_deck: Deque[Card], trigger_deck: Deque[Card],
                 initial_stock: Optional[List[Card]] = None):
        self.main_deck = main_deck
        self.discard: List[Card] = []
        self.trigger_deck = trigger_deck
        self.trigger_discard: List[Card] = []
        self.stock: List[Card] = list(initial_stock) if initial_stock else []
        self.clock_zone: List[Card] = []
        self.level_zone: List[Card] = []
        self.total_damage = 0
        self.initial_main_count = len(main_deck)
        self.initial_trigger_count = len(trigger_deck)
        self.initial_stock_count = len(self.stock)

    def _ensure_trigger_deck(self) -> None:
        if not self.trigger_deck:
            if not self.trigger_discard:
                raise SystemBrokenError("congrats, you just broke the system")
            random.shuffle(self.trigger_discard)
            self.trigger_deck.extend(self.trigger_discard)
            self.trigger_discard.clear()

    def _reveal_trigger_card(self) -> Card:
        self._ensure_trigger_deck()
        card = self.trigger_deck.pop()
        self.stock.append(card)
        return card

    def _peek_trigger_top(self) -> Card:
        self._ensure_trigger_deck()
        return self.trigger_deck[-1]

    def _burn_trigger_top(self) -> Card:
        self._ensure_trigger_deck()
        card = self.trigger_deck.pop()
        self.trigger_discard.append(card)
        return card

    @staticmethod
    def __card_soul(card: Card) -> int:
        return card.n_triggers if card.n_triggers <= 2 else 0

    # Trigger check rule
    def trigger_check(self) -> int:
        card = self._reveal_trigger_card()
        return self.__card_soul(card)

    # Twin drive rule (custom, hors-CR : 2 trigger checks au lieu d'un seul)
    def twin_drive_check(self) -> int:
        total = 0
        for _ in range(2):
            card = self._reveal_trigger_card()
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
    def refresh(self) -> None:
        if not self.discard:
            raise SystemBrokenError("congrats, you just broke the system")
        new_deck = self.discard[:]
        self.discard.clear()
        random.shuffle(new_deck)
        self.clock_zone.append(new_deck.pop())
        self.total_damage += 1
        self.levelup()
        self.main_deck.extend(new_deck)

    def keep_cards(self, cards: List[Card]) -> None:
        self.clock_zone.extend(cards)
        self.total_damage += len(cards)
        self.levelup()

    def resolve_occurrence(self, draw_count: int, trigger_type: Optional[str],
                            cost: int = 0) -> bool:
        if cost > 0:
            if len(self.stock) < cost:
                return False
            for _ in range(cost):
                self.trigger_discard.append(self.stock.pop())

        if trigger_type == "single":
            draw_count += self.trigger_check()
        elif trigger_type == "twin":
            draw_count += self.twin_drive_check()

        drawn: List[Card] = []
        while len(drawn) < draw_count:
            if not self.main_deck:
                self.refresh()
                continue
            card = self.main_deck.pop()
            drawn.append(card)
            if card.category == "climax":
                self.discard.extend(drawn)
                return True

        self.keep_cards(drawn)
        return False

    def _mill_bottom(self, count: int) -> int:
        climax_count = 0
        milled = 0
        while milled < count:
            if not self.main_deck:
                self.refresh()
                continue
            card = self.main_deck.popleft()
            self.discard.append(card)
            if card.category == "climax":
                climax_count += 1
            milled += 1
        return climax_count

    def _resolve_mill_count_climax(self, mill: MillBottomCountClimax) -> None:
        climax_count = self._mill_bottom(mill.x)
        self.resolve_occurrence(climax_count, None)

    def _resolve_mill_each_climax(self, mill: MillBottomEachClimax) -> None:
        climax_count = self._mill_bottom(mill.x)
        z_draw_count, z_trigger_type, z_cost = mill.z
        for _ in range(climax_count):
            self.resolve_occurrence(z_draw_count, z_trigger_type, z_cost)

    def _resolve_top_check_level_burn(self) -> None:
        card = self._peek_trigger_top()
        self.resolve_occurrence(card.level, None)

    def _resolve_musashi(self, musashi: Musashi) -> None:
        canceled = self.resolve_occurrence(*musashi.x)
        if not canceled:
            return
        card = self._burn_trigger_top()
        self.resolve_occurrence(card.level + 1, None)

    def _resolve_cancel_burn(self, cancel_burn: CancelBurn) -> None:
        canceled = self.resolve_occurrence(*cancel_burn.x)
        if not canceled:
            return

        for y_draw_count, y_trigger_type, y_cost in cancel_burn.y_list:
            self.resolve_occurrence(y_draw_count, y_trigger_type, y_cost)

    def run(self, parsed_occurrences: List[ParsedOccurrence]) -> int:
        for occurrence in parsed_occurrences:
            if isinstance(occurrence, CancelBurn):
                self._resolve_cancel_burn(occurrence)
            elif isinstance(occurrence, MillBottomCountClimax):
                self._resolve_mill_count_climax(occurrence)
            elif isinstance(occurrence, MillBottomEachClimax):
                self._resolve_mill_each_climax(occurrence)
            elif isinstance(occurrence, TopCheckLevelBurn):
                self._resolve_top_check_level_burn()
            elif isinstance(occurrence, Musashi):
                self._resolve_musashi(occurrence)
            else:
                draw_count, trigger_type, cost = occurrence
                self.resolve_occurrence(draw_count, trigger_type, cost)
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

        trigger_tracked = (len(self.trigger_deck) + len(self.trigger_discard)
                            + len(self.stock))
        trigger_expected = self.initial_trigger_count + self.initial_stock_count
        if trigger_tracked != trigger_expected:
            raise AssertionError(
                f"Incoherence de conservation des cartes trigger : "
                f"{trigger_tracked} cartes trackees "
                f"(trigger_deck+trigger_discard+stock) "
                f"pour {trigger_expected} au depart "
                f"(initial_trigger_count+initial_stock_count)."
            )

def run_single_trial(deck_size, climax_n, parsed_occurrences, pools: Pools,
                      trigger_deck_size, trigger_deck_climax,
                      reserve_stock_size: int = 0,
                      check_invariants=False) -> int:
    main_deck = build_deck(pools.main_climax, pools.main_non_climax, deck_size, climax_n)
    trigger_deck, initial_stock = build_trigger_deck_and_reserve(
        pools.trigger_climax, pools.trigger_non_climax,
        trigger_deck_size, trigger_deck_climax, reserve_stock_size,
    )
    state = GameSystem(main_deck, trigger_deck, initial_stock)
    damage = state.run(parsed_occurrences)
    if check_invariants:
        state.check_invariant()
    return damage