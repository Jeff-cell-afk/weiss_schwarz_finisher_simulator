import random
from collections import deque
from typing import Deque, List, Tuple

from .models import Card

def build_main_deck_and_stock(climax_pool, non_climax_pool, deck_size,
                               climax_n, stock_size: int = 0) -> Tuple[Deque[Card], List[Card]]:
    n_climax = len(climax_pool)
    n_non_climax = len(non_climax_pool)

    climax_idx = random.sample(range(n_climax), climax_n)
    non_climax_needed = (deck_size - climax_n) + stock_size
    non_climax_idx = random.sample(range(n_non_climax), non_climax_needed)
    deck_non_climax_idx = non_climax_idx[: deck_size - climax_n]
    stock_non_climax_idx = non_climax_idx[deck_size - climax_n:]

    deck_cards = (
        [climax_pool[i] for i in climax_idx]
        + [non_climax_pool[i] for i in deck_non_climax_idx]
    )
    random.shuffle(deck_cards)

    main_deck_stock = [non_climax_pool[i] for i in stock_non_climax_idx]

    return deque(deck_cards), main_deck_stock

def build_trigger_deck_and_stock(climax_pool, non_climax_pool, deck_size,
                                  climax_n, stock_size: int = 0) -> Tuple[Deque[Card], List[Card]]:
    n_climax = len(climax_pool)
    n_non_climax = len(non_climax_pool)

    climax_deck_idx = set(random.sample(range(n_climax), climax_n))
    non_climax_deck_idx = set(random.sample(range(n_non_climax), deck_size - climax_n))

    deck_cards = (
        [climax_pool[i] for i in climax_deck_idx]
        + [non_climax_pool[i] for i in non_climax_deck_idx]
    )
    random.shuffle(deck_cards)

    trigger_deck_stock: List[Card] = []
    if stock_size:
        used_unified = (
            climax_deck_idx
            | {n_climax + j for j in non_climax_deck_idx}
        )
        pool_size = n_climax + n_non_climax
        available = [i for i in range(pool_size) if i not in used_unified]
        for idx in random.sample(available, stock_size):
            if idx < n_climax:
                trigger_deck_stock.append(climax_pool[idx])
            else:
                trigger_deck_stock.append(non_climax_pool[idx - n_climax])

    return deque(deck_cards), trigger_deck_stock