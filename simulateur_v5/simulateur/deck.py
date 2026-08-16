import random
from collections import deque
from typing import Deque, List, Sequence, Tuple

import numpy as np

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

    climax_deck_idx = random.sample(range(n_climax), climax_n)
    non_climax_needed = (deck_size - climax_n) + stock_size
    non_climax_idx = random.sample(range(n_non_climax), non_climax_needed)
    non_climax_deck_idx = non_climax_idx[: deck_size - climax_n]
    stock_non_climax_idx = non_climax_idx[deck_size - climax_n:]

    deck_cards = (
        [climax_pool[i] for i in climax_deck_idx]
        + [non_climax_pool[i] for i in non_climax_deck_idx]
    )
    random.shuffle(deck_cards)

    trigger_deck_stock = [non_climax_pool[i] for i in stock_non_climax_idx]

    return deque(deck_cards), trigger_deck_stock


# Vectorized deck construction

def _batch_permutations(n_trials: int, n_pool: int, rng: np.random.Generator) -> np.ndarray:
    if n_pool == 0:
        return np.empty((n_trials, 0), dtype=np.int64)
    keys = rng.random((n_trials, n_pool))
    return np.argsort(keys, axis=1)


def batch_build_main_decks(climax_pool: Sequence[Card], non_climax_pool: Sequence[Card],
                            deck_size: int, climax_n: int, n_trials: int,
                            rng: np.random.Generator, stock_size: int = 0) -> Tuple[np.ndarray, np.ndarray]:
    climax_arr = np.asarray(climax_pool, dtype=object)
    non_climax_arr = np.asarray(non_climax_pool, dtype=object)

    climax_idx = _batch_permutations(n_trials, len(climax_pool), rng)[:, :climax_n]

    non_climax_needed = (deck_size - climax_n) + stock_size
    non_climax_sel = _batch_permutations(n_trials, len(non_climax_pool), rng)[:, :non_climax_needed]
    deck_non_climax_idx = non_climax_sel[:, : deck_size - climax_n]
    stock_non_climax_idx = non_climax_sel[:, deck_size - climax_n:]

    deck_cards = np.concatenate(
        [climax_arr[climax_idx], non_climax_arr[deck_non_climax_idx]], axis=1
    )
    # Reshuffle each row so climax cards aren't all grouped together.
    shuffle_perm = _batch_permutations(n_trials, deck_size, rng)
    deck_cards = np.take_along_axis(deck_cards, shuffle_perm, axis=1)

    stock_cards = non_climax_arr[stock_non_climax_idx]
    return deck_cards, stock_cards


def batch_build_trigger_decks(climax_pool: Sequence[Card], non_climax_pool: Sequence[Card],
                               deck_size: int, climax_n: int, n_trials: int,
                               rng: np.random.Generator, stock_size: int = 0) -> Tuple[np.ndarray, np.ndarray]:
    climax_arr = np.asarray(climax_pool, dtype=object)
    non_climax_arr = np.asarray(non_climax_pool, dtype=object)

    climax_idx = _batch_permutations(n_trials, len(climax_pool), rng)[:, :climax_n]

    non_climax_needed = (deck_size - climax_n) + stock_size
    non_climax_sel = _batch_permutations(n_trials, len(non_climax_pool), rng)[:, :non_climax_needed]
    deck_non_climax_idx = non_climax_sel[:, : deck_size - climax_n]
    stock_non_climax_idx = non_climax_sel[:, deck_size - climax_n:]

    deck_cards = np.concatenate(
        [climax_arr[climax_idx], non_climax_arr[deck_non_climax_idx]], axis=1
    )
    shuffle_perm = _batch_permutations(n_trials, deck_size, rng)
    deck_cards = np.take_along_axis(deck_cards, shuffle_perm, axis=1)

    stock_cards = non_climax_arr[stock_non_climax_idx]
    return deck_cards, stock_cards
