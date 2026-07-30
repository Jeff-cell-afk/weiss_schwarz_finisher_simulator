import itertools
import math
import os
import random
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from . import config
from .deck import parse_occurrences
from .game_system import run_single_trial
from .pools import build_pools, validate_pools

def max_possible_damage(occurrences, deck_size_list=None) -> int:
    base = sum(draw_count + (2 if is_trigger else 0)
               for draw_count, is_trigger in parse_occurrences(occurrences))
    if not deck_size_list:
        return base
    max_refreshes = math.ceil(base / min(deck_size_list))
    return base + max_refreshes

def run_combination(task):
    (size, climax_n, parsed_occurrences, pools,
     trigger_deck_size, trigger_deck_climax, n_trials,
     check_invariants, task_seed) = task

    random.seed(task_seed)

    results = np.fromiter(
        (run_single_trial(size, climax_n, parsed_occurrences, pools,
                           trigger_deck_size, trigger_deck_climax, check_invariants)
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
                    main_non_climax_specs=config.MAIN_NON_CLIMAX_SPECS,
                    main_climax_specs=config.MAIN_CLIMAX_SPECS,
                    trigger_non_climax_specs=config.TRIGGER_NON_CLIMAX_SPECS,
                    trigger_climax_specs=config.TRIGGER_CLIMAX_SPECS,
                    trigger_deck_size=config.TRIGGER_DECK_SIZE,
                    trigger_deck_climax=config.TRIGGER_DECK_CLIMAX,
                    max_damage_column=None,
                    out_path=None,
                    seed=None,
                    check_invariants=False,
                    n_jobs=None) -> pd.DataFrame:
    """
    Parameters
    ----------
    deck_size_list     : deck sizes to test
    climax_list        : climax counts to test [6, 8]
    occurrences        : damage sequence to test (type '1A' with to get soul trigger check)
    n_trials           : Monte Carlo simulations number for each (deck_size_list, climax_list) combination
    main_non_climax_specs, main_climax_specs,
    trigger_non_climax_specs, trigger_climax_specs
                        : customize both decks as you wish
    trigger_deck_size  : trigger deck size
    trigger_deck_climax: climax count in trigger deck
    max_damage_column  : cf function description before
    out_path           : csv table path on your PC (None = pas d'export)
    seed               : initialisation number
    check_invariants   : debugger system here, desactived by default
    """
    pools = build_pools(main_non_climax_specs, main_climax_specs,
                         trigger_non_climax_specs, trigger_climax_specs)
    validate_pools(pools, deck_size_list, climax_list, trigger_deck_size, trigger_deck_climax)
    parsed_occurrences = parse_occurrences(occurrences)

    thresholds = np.arange((max_damage_column or max_possible_damage(occurrences, deck_size_list)) + 1)
    columns = [f"P(total_damage>={t})" for t in thresholds]

    combinations = [
        (size, climax_n)
        for size, climax_n in itertools.product(deck_size_list, climax_list)
        if climax_n < size
    ]

    tasks = [
        (size, climax_n, parsed_occurrences, pools,
         trigger_deck_size, trigger_deck_climax, n_trials, check_invariants,
         None if seed is None else seed + i)
        for i, (size, climax_n) in enumerate(combinations)
    ]

    n_jobs = n_jobs or os.cpu_count() or 1
    n_jobs = min(n_jobs, len(tasks)) or 1

    if n_jobs == 1:
        raw_results = [run_combination(task) for task in tasks]
    else:
        with ProcessPoolExecutor(max_workers=n_jobs) as executor:
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