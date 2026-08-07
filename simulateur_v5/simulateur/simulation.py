import itertools
import math
import os
import random
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from .deck import (
    CancelBurn, MillBottomCountClimax, MillBottomEachClimax, Musashi,
    parse_occurrences, TopCheckLevelBurn,
)
from .game_system import run_single_trial
from .pools import build_pools, validate_pools

_TRIGGER_BONUS = {None: 0, "single": 2, "twin": 4}

def _spec_value(spec, trigger_bonus=_TRIGGER_BONUS) -> int:
    draw_count, trigger_type, _cost = spec
    return draw_count + trigger_bonus[trigger_type]

def max_possible_damage(occurrences, deck_size_list=None, max_trigger_level=0) -> int:
    base = 0
    for occurrence in parse_occurrences(occurrences):
        if isinstance(occurrence, CancelBurn):
            x_value = _spec_value(occurrence.x)
            y_value = sum(_spec_value(y) for y in occurrence.y_list)
            base += max(x_value, y_value)
        elif isinstance(occurrence, MillBottomCountClimax):
            base += occurrence.x
        elif isinstance(occurrence, MillBottomEachClimax):
            base += occurrence.x * _spec_value(occurrence.z)
        elif isinstance(occurrence, TopCheckLevelBurn):
            base += max_trigger_level
        elif isinstance(occurrence, Musashi):
            x_value = _spec_value(occurrence.x)
            base += max(x_value, max_trigger_level + 1)
        else:
            base += _spec_value(occurrence)
    if not deck_size_list:
        return base
    max_refreshes = math.ceil(base / min(deck_size_list))
    return base + max_refreshes

_worker_pools = None
_worker_parsed_occurrences = None

def _init_worker(pools, parsed_occurrences) -> None:
    global _worker_pools, _worker_parsed_occurrences
    _worker_pools = pools
    _worker_parsed_occurrences = parsed_occurrences

def run_combination(task):
    (size, climax_n, trigger_deck_size, trigger_deck_climax, reserve_stock_size,
     n_trials, check_invariants, task_seed) = task

    random.seed(task_seed)

    results = np.fromiter(
        (run_single_trial(size, climax_n, _worker_parsed_occurrences, _worker_pools,
                           trigger_deck_size, trigger_deck_climax, reserve_stock_size,
                           check_invariants)
         for _ in range(n_trials)),
        dtype=int, count=n_trials,
    )
    return size, climax_n, results

def probs_from_results(results: np.ndarray, thresholds: np.ndarray) -> np.ndarray:
    sorted_results = np.sort(results)
    n = len(sorted_results)
    counts = n - np.searchsorted(sorted_results, thresholds, side="left")
    return (counts / n).round(4)

def generate_table(deck_size_list, climax_list, occurrences, n_trials,
                    main_non_climax_specs, main_climax_specs,
                    trigger_non_climax_specs, trigger_climax_specs,
                    trigger_deck_size, trigger_deck_climax,
                    reserve_stock_size=0,
                    max_damage_column=None,
                    out_path=None,
                    seed=None,
                    check_invariants=False,
                    n_jobs=None) -> pd.DataFrame:
    pools = build_pools(main_non_climax_specs, main_climax_specs,
                         trigger_non_climax_specs, trigger_climax_specs)
    validate_pools(pools, deck_size_list, climax_list, trigger_deck_size,
                    trigger_deck_climax, reserve_stock_size)
    parsed_occurrences = parse_occurrences(occurrences)

    max_trigger_level = max(
        (card.level for card in itertools.chain(trigger_non_climax_specs, trigger_climax_specs)),
        default=0,
    )

    max_damage_column = (
        max_possible_damage(occurrences, deck_size_list, max_trigger_level)
        if max_damage_column is None else max_damage_column
    )
    thresholds = np.arange(max_damage_column + 1)
    columns = [f"P(total_damage>={t})" for t in thresholds]

    combinations = [
        (size, climax_n)
        for size, climax_n in itertools.product(deck_size_list, climax_list)
        if climax_n < size
    ]

    tasks = [
        (size, climax_n, trigger_deck_size, trigger_deck_climax, reserve_stock_size,
         n_trials, check_invariants, None if seed is None else seed + i)
        for i, (size, climax_n) in enumerate(combinations)
    ]

    n_jobs = n_jobs or os.cpu_count() or 1
    n_jobs = min(n_jobs, len(tasks)) or 1

    if n_jobs == 1:
        _init_worker(pools, parsed_occurrences)
        raw_results = [run_combination(task) for task in tasks]
    else:
        with ProcessPoolExecutor(
            max_workers=n_jobs, initializer=_init_worker,
            initargs=(pools, parsed_occurrences),
        ) as executor:
            raw_results = list(executor.map(run_combination, tasks))

    rows = []
    for size, climax_n, results in raw_results:
        probs = probs_from_results(results, thresholds)
        rows.append([size, climax_n, *probs])

    table = pd.DataFrame(rows, columns=["main_deck_size", "climax_number"] + columns)

    if out_path:
        table.to_csv(out_path, index=False)
        print(f"CSV ecrit : {out_path} ({len(rows)} combinaisons x {n_trials} simulations, n_jobs={n_jobs})")

    return table