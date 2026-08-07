from typing import List

from .models import Card, Pools

def expand_pool(card_counts: dict) -> List[Card]:
    pool = []
    for card, count in card_counts.items():
        if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
            raise ValueError(
                f"Compte invalide pour {card!r} : {count!r} "
                f"(attendu un entier > 0)."
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
                    reserve_stock_size: int = 0) -> None:
    if trigger_deck_climax > trigger_deck_size:
        raise ValueError(
            f"trigger_deck_climax ({trigger_deck_climax}) ne peut pas depasser "
            f"trigger_deck_size ({trigger_deck_size})."
        )

    if reserve_stock_size < 0:
        raise ValueError(
            f"reserve_stock_size ({reserve_stock_size}) ne peut pas etre negatif."
        )

    valid_pairs = [(s, c) for s in deck_size_list for c in climax_list if c < s]
    if not valid_pairs:
        raise ValueError(
            "Aucune combinaison (deck_size, climax_n) valide : il faut "
            "climax_n < deck_size pour au moins une paire testee."
        )

    needed = {
        "main_climax": max(climax_list),
        "main_non_climax": max(s - c for s, c in valid_pairs),
        "trigger_climax": trigger_deck_climax,
        "trigger_non_climax": trigger_deck_size - trigger_deck_climax,
    }
    for field, n_needed in needed.items():
        pool = getattr(pools, field)
        if len(pool) < n_needed:
            raise ValueError(
                f"Le pool '{field}' ne contient que {len(pool)} exemplaires, "
                f"or il en faut au moins {n_needed}. Augmente le nombre "
                f"d'exemplaires par carte dans les specs correspondantes."
            )

    trigger_pool_total = len(pools.trigger_climax) + len(pools.trigger_non_climax)
    trigger_needed_total = trigger_deck_size + reserve_stock_size
    if trigger_pool_total < trigger_needed_total:
        raise ValueError(
            f"Les pools trigger ('trigger_climax' + 'trigger_non_climax') ne "
            f"contiennent que {trigger_pool_total} exemplaires au total, or il "
            f"en faut au moins {trigger_needed_total} ({trigger_deck_size} pour "
            f"le trigger deck + {reserve_stock_size} pour la reserve de stock "
            f"initial). Augmente le nombre d'exemplaires par carte dans les "
            f"specs trigger, ou reduis reserve_stock_size."
        )