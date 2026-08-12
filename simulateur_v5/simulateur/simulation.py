import itertools
import os
import random
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .grammar import (
    max_possible_damage,
    Occurrence, parse_occurrences, validate_occurrence_costs,
)
from .game_system import run_single_trial
from .pools import build_pools, validate_pools

def run_combination(task, pools, occurrences):
    (size, climax_n, trigger_deck_size, trigger_deck_climax, trigger_deck_stock_size,
     main_deck_stock_size, n_trials, check_invariants, task_seed) = task

    random.seed(task_seed)

    results = np.fromiter(
        (run_single_trial(size, climax_n, occurrences, pools,
                           trigger_deck_size, trigger_deck_climax,
                           trigger_deck_stock_size, main_deck_stock_size,
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

@dataclass
class SimulationConfig:
    deck_size_list: list[int]
    climax_list: list[int]
    occurrences: list
    n_trials: int
    trigger_deck_size: int
    trigger_deck_climax: int

    # Pools
    main_non_climax_specs: dict
    main_climax_specs: dict
    trigger_non_climax_specs: dict
    trigger_climax_specs: dict

    # Optional
    trigger_deck_stock_size: int = 0
    main_deck_stock_size: int = 0
    max_damage_column: int | None = None
    out_path: str | None = None
    seed: int | None = None
    n_jobs: int | None = None
    check_invariants: bool = False

def generate_table(config: SimulationConfig) -> pd.DataFrame:
    pools = build_pools(config.main_non_climax_specs, config.main_climax_specs,
                         config.trigger_non_climax_specs, config.trigger_climax_specs)
    validate_pools(pools, config.deck_size_list, config.climax_list,
                    config.trigger_deck_size, config.trigger_deck_climax,
                    config.trigger_deck_stock_size, config.main_deck_stock_size)
    occurrences = parse_occurrences(config.occurrences)
    validate_occurrence_costs(occurrences, config.trigger_deck_stock_size)

    max_trigger_level = pools.max_trigger_level
    max_main_level = pools.max_main_level

    max_damage_column = (
        max_possible_damage(occurrences, config.deck_size_list, max_trigger_level, max_main_level)
        if config.max_damage_column is None else config.max_damage_column
    )
    thresholds = np.arange(max_damage_column + 1)
    columns = [f"P(total_damage>={t})" for t in thresholds]

    combinations = [
        (size, climax_n)
        for size, climax_n in itertools.product(config.deck_size_list, config.climax_list)
        if climax_n < size
    ]

    tasks = [
        (size, climax_n, config.trigger_deck_size, config.trigger_deck_climax,
         config.trigger_deck_stock_size, config.main_deck_stock_size,
         config.n_trials, config.check_invariants,
         None if config.seed is None else config.seed + i)
        for i, (size, climax_n) in enumerate(combinations)
    ]

    n_jobs = config.n_jobs or os.cpu_count() or 1
    n_jobs = min(n_jobs, len(tasks)) or 1

    if n_jobs == 1:
        raw_results = [
            run_combination(task, pools, occurrences)
            for task in tasks
        ]
    else:
        with ProcessPoolExecutor(max_workers=n_jobs) as executor:
            futures = [
                executor.submit(run_combination, task, pools, occurrences)
                for task in tasks
            ]
            raw_results = [future.result() for future in futures]

    rows = []
    for size, climax_n, results in raw_results:
        probs = probs_from_results(results, thresholds)
        rows.append([size, climax_n, *probs])

    table = pd.DataFrame(rows, columns=["main_deck_size", "climax_number"] + columns)

    if config.out_path:
        table.to_csv(config.out_path, index=False)
        print(
            f"CSV written: {config.out_path} ({len(rows)} combinations x "
            f"{config.n_trials} simulations, n_jobs={n_jobs})"
        )

    return table