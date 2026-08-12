from typing import List

from .models import Card, Pools, _is_valid_positive_int

def expand_pool(card_counts: dict) -> List[Card]:
    pool = []
    for card, count in card_counts.items():
        if not _is_valid_positive_int(count):
            raise ValueError(
                f"Invalid count for {card!r}: {count!r} "
                f"(expected an integer > 0)."
            )
        pool.extend([card] * count)
    return pool

def build_pools(main_non_climax_specs, main_climax_specs,
                trigger_non_climax_specs, trigger_climax_specs) -> Pools:
    return Pools(
        main_climax=expand_pool(main_climax_specs),
        main_non_climax=expand_pool(main_non_climax_specs),
        trigger_climax=expand_pool(trigger_climax_specs),
        trigger_non_climax=expand_pool(trigger_non_climax_specs),
    )

def validate_pools(pools: Pools, deck_size_list, climax_list,
                    trigger_deck_size, trigger_deck_climax,
                    trigger_deck_stock_size: int = 0,
                    main_deck_stock_size: int = 0) -> None:
    if trigger_deck_climax > trigger_deck_size:
        raise ValueError(
            f"trigger_deck_climax ({trigger_deck_climax}) cannot exceed "
            f"trigger_deck_size ({trigger_deck_size})."
        )

    if trigger_deck_stock_size < 0:
        raise ValueError(
            f"trigger_deck_stock_size ({trigger_deck_stock_size}) cannot be negative."
        )

    if main_deck_stock_size < 0:
        raise ValueError(
            f"main_deck_stock_size ({main_deck_stock_size}) cannot be negative."
        )

    valid_pairs = [(s, c) for s in deck_size_list for c in climax_list if c < s]
    if not valid_pairs:
        raise ValueError(
            "No valid (deck_size, climax_n) combination: climax_n < "
            "deck_size is required for at least one tested pair."
        )

    pool_sizes = {
        "main_climax": len(pools.main_climax),
        "main_non_climax": len(pools.main_non_climax),
        "trigger_climax": len(pools.trigger_climax),
        "trigger_non_climax": len(pools.trigger_non_climax),
    }

    needed = {
        "main_climax": max(climax_list),
        "main_non_climax": max(s - c for s, c in valid_pairs) + main_deck_stock_size,
        "trigger_climax": trigger_deck_climax,
        "trigger_non_climax": trigger_deck_size - trigger_deck_climax,
    }
    for field, n_needed in needed.items():
        if pool_sizes[field] < n_needed:
            raise ValueError(
                f"Pool '{field}' only contains {pool_sizes[field]} "
                f"copies, but at least {n_needed} are needed. Increase "
                f"the number of copies per card in the corresponding "
                f"specs."
            )

    trigger_pool_total = pool_sizes["trigger_climax"] + pool_sizes["trigger_non_climax"]
    trigger_needed_total = trigger_deck_size + trigger_deck_stock_size
    if trigger_pool_total < trigger_needed_total:
        raise ValueError(
            f"The trigger pools ('trigger_climax' + 'trigger_non_climax') "
            f"only contain {trigger_pool_total} copies in total, but at "
            f"least {trigger_needed_total} are needed ({trigger_deck_size} "
            f"for the trigger deck + {trigger_deck_stock_size} for "
            f"trigger_deck_stock). Increase the number of copies per card "
            f"in the trigger specs, or reduce trigger_deck_stock_size."
        )