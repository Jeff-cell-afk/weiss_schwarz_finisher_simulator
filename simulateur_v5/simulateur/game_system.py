import random
from typing import Deque, List, Optional, Tuple

from .grammar import Occurrence
from .models import Card, Pools

class SystemBrokenError(RuntimeError):
    """Deckout lose condition. Used during the refresh procedure as an emergency system."""

# All the functions used to recreate a damage sequence are written here.
class GameSystem:
    __slots__ = (
        "main_deck", "discard", "trigger_deck", "trigger_discard",
        "trigger_deck_stock", "main_deck_stock",
        "clock_zone", "level_zone", "total_damage", "initial_main_count",
        "initial_trigger_count", "initial_trigger_stock_count",
        "initial_main_stock_count",
    )

    # All card zones and check counts are initialized here
    def __init__(self, main_deck: Deque[Card], trigger_deck: Deque[Card],
                 initial_trigger_stock: Optional[List[Card]] = None,
                 initial_main_stock: Optional[List[Card]] = None):
        self.main_deck = main_deck
        self.discard: List[Card] = []
        self.trigger_deck = trigger_deck
        self.trigger_discard: List[Card] = []
        self.trigger_deck_stock: List[Card] = list(initial_trigger_stock) if initial_trigger_stock else []
        self.main_deck_stock: List[Card] = list(initial_main_stock) if initial_main_stock else []
        self.clock_zone: List[Card] = []
        self.level_zone: List[Card] = []
        self.total_damage = 0
        self.initial_main_count = len(main_deck)
        self.initial_trigger_count = len(trigger_deck)
        self.initial_trigger_stock_count = len(self.trigger_deck_stock)
        self.initial_main_stock_count = len(self.main_deck_stock)

    # Trigger deck structure

    # Safety function to verify the main deck always has a card in it
    # If both main deck and its discard are simultaneous empty, the simulator is stopped
    def _ensure_trigger_deck(self) -> None:
        if not self.trigger_deck:
            if not self.trigger_discard:
                raise SystemBrokenError("You reached the simulation's limit here")
            random.shuffle(self.trigger_discard)
            self.trigger_deck.extend(self.trigger_discard)
            self.trigger_discard.clear()

    # Takes the main deck's top card, uses it for trigger check and puts it into trigger's stock zone
    def _reveal_trigger_card(self) -> Card:
        self._ensure_trigger_deck()
        card = self.trigger_deck.pop()
        self.trigger_deck_stock.append(card)
        return card

    # Looks at the top deck, but lets it on top for later trigger checks
    def peek_trigger_top(self) -> Card:
        self._ensure_trigger_deck()
        return self.trigger_deck[-1]

    @staticmethod
    # Failsafe function here, actually there is no card in the game that has more than two soul triggers in it
    def __card_soul(card: Card) -> int:
        return card.n_triggers if card.n_triggers <= 2 else 0

    # Trigger check rule
    def trigger_check(self) -> int:
        card = self._reveal_trigger_card()
        return self.__card_soul(card)

    # Double trigger check rule
    def twin_drive_check(self) -> int:
        total = 0
        for _ in range(2):
            card = self._reveal_trigger_card()
            total += self.__card_soul(card)
        return total

    # Damage structure

    # Level up rule
    # While the clock zone holds 7 or more cards, process a batch of 7:
    # move the first non-climax card found in that batch to the level zone, and discard the rest of the batch.
    # in case there are 7 climaxes in clock zone, one is forced to go into level zone
    def levelup(self) -> None:
        while len(self.clock_zone) >= 7:
            batch = [self.clock_zone.pop(0) for _ in range(7)]
            level_card_idx = next(
            (i for i, card in enumerate(batch) if card.category != "climax"),
            None,)
            if level_card_idx is not None:
                self.level_zone.append(batch.pop(level_card_idx))
            self.discard.extend(batch)

    # Refresh penalty rule
    def refresh(self) -> None:
        if not self.discard:
            raise SystemBrokenError("You reached the simulation's limit here")
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

    # Cost primitive

    def can_pay_trigger(self, n: int) -> bool:
        return len(self.trigger_deck_stock) >= n

    def pay_trigger(self, n: int) -> None:
        for _ in range(n):
            self.trigger_discard.append(self.trigger_deck_stock.pop())

    def can_pay_main(self, n: int) -> bool:
        return len(self.main_deck_stock) >= n

    def pay_main(self, n: int) -> None:
        for _ in range(n):
            self.discard.append(self.main_deck_stock.pop())

    # Burn primitive

    def reveal_trigger_cards(self, n: int) -> Tuple[int, List[Card]]:
        cards = [self._reveal_trigger_card() for _ in range(n)]
        bonus = sum(self.__card_soul(c) for c in cards)
        return bonus, cards

    def resolution_core(self, n: int) -> bool:
        pile: List[Card] = []
        canceled = False
        while len(pile) < n:
            if not self.main_deck:
                self.refresh()
                continue
            card = self.main_deck.pop()
            pile.append(card)
            if card.category == "climax":
                self.discard.extend(pile)
                canceled = True
                break

        if not canceled:
            self.keep_cards(pile)

        return canceled

    def resolution(self, n: int, trigger: Optional[str]) -> bool:
        bonus = 0
        if trigger == "single":
            bonus, _ = self.reveal_trigger_cards(1)
        elif trigger == "twin":
            bonus, _ = self.reveal_trigger_cards(2)
        return self.resolution_core(n + bonus)

    # Mill primitive

    def mill(self, n: int, target: str, edge: str) -> Tuple[int, List[Card]]:
        if target == "self":
            deck, discard_pile = self.trigger_deck, self.trigger_discard
        else:
            deck, discard_pile = self.main_deck, self.discard

        milled: List[Card] = []
        climax_count = 0
        while len(milled) < n:
            if not deck:
                if target == "self":
                    self._ensure_trigger_deck()
                else:
                    self.refresh()
                continue
            card = deck.pop() if edge == "top" else deck.popleft()
            discard_pile.append(card)
            milled.append(card)
            if card.category == "climax":
                climax_count += 1
        return climax_count, milled

    # Scry primitive

    def scry(self, n: int) -> Tuple[int, List[Card]]:
        count = min(n, len(self.main_deck))
        revealed = [self.main_deck.pop() for _ in range(count)]

        climax_cards = [c for c in revealed if c.category == "climax"]
        kept = [c for c in revealed if c.category != "climax"]
        self.discard.extend(climax_cards)
        for card in reversed(kept):
            self.main_deck.append(card)

        return len(climax_cards), revealed

    # Shuffle primitive

    def shuffle_into_main(self, moved: List[Card], kept: List[Card]) -> None:
        self.discard = kept
        new_main = list(self.main_deck) + moved
        random.shuffle(new_main)
        self.main_deck.clear()
        self.main_deck.extend(new_main)

    def shuffle_discard_into_main(self, count: int) -> None:
        eligible_idx = [i for i, c in enumerate(self.discard) if c.category != "climax"]
        chosen_idx = set(random.sample(eligible_idx, min(count, len(eligible_idx))))
        if not chosen_idx:
            return
        moved = [c for i, c in enumerate(self.discard) if i in chosen_idx]
        kept = [c for i, c in enumerate(self.discard) if i not in chosen_idx]
        self.shuffle_into_main(moved, kept)

    # StockSwap primitive

    def recomplete(self, n: int) -> List[Card]:
        drawn: List[Card] = []
        while len(drawn) < n:
            if not self.main_deck:
                self.refresh()
                continue
            drawn.append(self.main_deck.pop())
        return drawn

    def stock_swap(self) -> None:
        n = len(self.main_deck_stock)
        self.discard.extend(self.main_deck_stock)
        self.main_deck_stock.clear()
        self.main_deck_stock.extend(self.recomplete(n))

    def stock_shuffle(self) -> None:
        n = len(self.main_deck_stock)

        new_main = list(self.main_deck) + self.main_deck_stock
        self.main_deck_stock.clear()
        random.shuffle(new_main)
        self.main_deck.clear()
        self.main_deck.extend(new_main)

        self.main_deck_stock.extend(self.recomplete(n))

    def shuffle_all_but_climax_reserve(self, x: int) -> None:
        climax_idx = [i for i, c in enumerate(self.discard) if c.category == "climax"]
        hold_back_count = min(x, len(climax_idx))
        held_idx = set(random.sample(climax_idx, hold_back_count))

        moved = [c for i, c in enumerate(self.discard) if i not in held_idx]
        kept = [c for i, c in enumerate(self.discard) if i in held_idx]
        self.shuffle_into_main(moved, kept)

    
    def run(self, occurrences: List[Occurrence]) -> int:
        for occurrence in occurrences:
            occurrence.resolve(self)
        return self.total_damage

    # Cards tracked, used to look for bugs and data loss
    def check_invariant(self) -> None:
        tracked = (len(self.main_deck) + len(self.discard)
                   + len(self.clock_zone) + len(self.level_zone)
                   + len(self.main_deck_stock))
        expected = self.initial_main_count + self.initial_main_stock_count
        if tracked != expected:
            raise AssertionError(
                f"Card conservation inconsistency: {tracked} cards "
                f"tracked (main_deck+discard+clock_zone+level_zone"
                f"+main_deck_stock) for {expected} at the start "
                f"(initial_main_count+initial_main_stock_count)."
            )

        trigger_tracked = (len(self.trigger_deck) + len(self.trigger_discard)
                            + len(self.trigger_deck_stock))
        trigger_expected = self.initial_trigger_count + self.initial_trigger_stock_count
        if trigger_tracked != trigger_expected:
            raise AssertionError(
                f"Trigger card conservation inconsistency: "
                f"{trigger_tracked} cards tracked "
                f"(trigger_deck+trigger_discard+trigger_deck_stock) "
                f"for {trigger_expected} at the start "
                f"(initial_trigger_count+initial_trigger_stock_count)."
            )

def run_trial_from_decks(main_deck: Deque[Card], trigger_deck: Deque[Card],
                          trigger_deck_stock: List[Card], main_deck_stock: List[Card],
                          occurrences: List[Occurrence], check_invariants: bool = False) -> int:
    state = GameSystem(main_deck, trigger_deck, trigger_deck_stock, main_deck_stock)
    damage = state.run(occurrences)
    if check_invariants:
        state.check_invariant()
    return damage


def run_single_trial(deck_size, climax_n, occurrences: List[Occurrence], pools: Pools,
                      trigger_deck_size, trigger_deck_climax,
                      trigger_deck_stock_size: int = 0,
                      main_deck_stock_size: int = 0,
                      check_invariants=False) -> int:
    from .deck import build_main_deck_and_stock, build_trigger_deck_and_stock

    main_deck, main_deck_stock = build_main_deck_and_stock(
        pools.main_climax, pools.main_non_climax, deck_size, climax_n,
        main_deck_stock_size,
    )
    trigger_deck, trigger_deck_stock = build_trigger_deck_and_stock(
        pools.trigger_climax, pools.trigger_non_climax,
        trigger_deck_size, trigger_deck_climax, trigger_deck_stock_size,
    )
    return run_trial_from_decks(
        main_deck, trigger_deck, trigger_deck_stock, main_deck_stock,
        occurrences, check_invariants,
    )
