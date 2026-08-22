import random
from dataclasses import dataclass

import numpy as np

from .game_system import run_single_trial
from .grammar import Occurrence, parse_occurrences
from .models import Pools


@dataclass
class PairedComparisonResult:
    damages_a: np.ndarray
    damages_b: np.ndarray
    diffs: np.ndarray
    mean_diff: float
    std_diff: float
    ci_95: tuple[float, float]
    t_stat: float
    p_value: float
    cohens_d: float

    def summary(self) -> str:
        direction = "B > A" if self.mean_diff > 0 else "A > B" if self.mean_diff < 0 else "A == B"
        return (
            f"Mean damage diff (B - A): {self.mean_diff:+.3f} "
            f"[95% CI: {self.ci_95[0]:+.3f}, {self.ci_95[1]:+.3f}] "
            f"({direction}), Cohen's d = {self.cohens_d:.3f}, "
            f"t = {self.t_stat:.3f}, p = {self.p_value:.4g}, "
            f"n = {len(self.diffs)}"
        )


def _run_one(size, climax_n, occurrences, pools, trigger_deck_size,
             trigger_deck_climax, trigger_deck_stock_size,
             main_deck_stock_size, check_invariants, seed) -> int:
    random.seed(seed)
    return run_single_trial(
        size, climax_n, occurrences, pools,
        trigger_deck_size, trigger_deck_climax,
        trigger_deck_stock_size, main_deck_stock_size,
        check_invariants,
    )


def _bootstrap_ci(diffs: np.ndarray, n_boot: int, rng: np.random.Generator,
                   alpha: float = 0.05) -> tuple[float, float]:
    n = len(diffs)
    boot_means = rng.choice(diffs, size=(n_boot, n), replace=True).mean(axis=1)
    lo, hi = np.percentile(boot_means, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(lo), float(hi)


def compare_occurrences_paired(
    occurrences_a: list | list[Occurrence],
    occurrences_b: list | list[Occurrence],
    pools: Pools,
    deck_size: int,
    climax_n: int,
    n_trials: int,
    trigger_deck_size: int,
    trigger_deck_climax: int,
    trigger_deck_stock_size: int = 0,
    main_deck_stock_size: int = 0,
    check_invariants: bool = False,
    seed: int = 0,
    n_boot: int = 10_000,
) -> PairedComparisonResult:
    if n_trials <= 0:
        raise ValueError(f"n_trials ({n_trials}) must be a positive integer.")

    parsed_a = occurrences_a if occurrences_a and isinstance(occurrences_a[0], Occurrence) \
        else parse_occurrences(occurrences_a)
    parsed_b = occurrences_b if occurrences_b and isinstance(occurrences_b[0], Occurrence) \
        else parse_occurrences(occurrences_b)

    damages_a = np.empty(n_trials, dtype=int)
    damages_b = np.empty(n_trials, dtype=int)

    for i in range(n_trials):
        trial_seed = seed + i
        damages_a[i] = _run_one(
            deck_size, climax_n, parsed_a, pools, trigger_deck_size,
            trigger_deck_climax, trigger_deck_stock_size,
            main_deck_stock_size, check_invariants, trial_seed,
        )
        damages_b[i] = _run_one(
            deck_size, climax_n, parsed_b, pools, trigger_deck_size,
            trigger_deck_climax, trigger_deck_stock_size,
            main_deck_stock_size, check_invariants, trial_seed,
        )

    diffs = damages_b - damages_a
    mean_diff = float(diffs.mean())
    std_diff = float(diffs.std(ddof=1)) if n_trials > 1 else 0.0

    se = std_diff / np.sqrt(n_trials) if n_trials > 1 else 0.0
    t_stat = mean_diff / se if se > 0 else 0.0
    p_value = float(2 * (1 - _norm_cdf(abs(t_stat)))) if se > 0 else 1.0

    cohens_d = mean_diff / std_diff if std_diff > 0 else 0.0

    rng = np.random.default_rng(seed)
    ci_95 = _bootstrap_ci(diffs, n_boot, rng) if n_trials > 1 else (mean_diff, mean_diff)

    return PairedComparisonResult(
        damages_a=damages_a,
        damages_b=damages_b,
        diffs=diffs,
        mean_diff=mean_diff,
        std_diff=std_diff,
        ci_95=ci_95,
        t_stat=t_stat,
        p_value=p_value,
        cohens_d=cohens_d,
    )


def _norm_cdf(x: float) -> float:
    import math
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))