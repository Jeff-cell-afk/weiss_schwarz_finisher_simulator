from simulateur import Card, generate_table

if __name__ == "__main__":
    non_climax_specs = {
        Card(0, 0, "character", "yellow"): 17,
        Card(1, 0, "character", "yellow"): 12,
        Card(2, 1, "character", "yellow"): 3,
        Card(3, 0, "character", "yellow"): 3,
        Card(3, 1, "character", "yellow"): 7,
    }
    climax_specs = {
        Card(0, 0, "climax", "yellow"): 4,
        Card(0, 1, "climax", "yellow"): 4,
    }

    table = generate_table(
        deck_size_list=[20, 25, 30],
        climax_list=[4, 6, 8],
        occurrences=[4, '3A', 4, '3A', 4, '3A'],
        n_trials=20000,
        main_non_climax_specs=non_climax_specs,
        main_climax_specs=climax_specs,
        trigger_non_climax_specs=non_climax_specs,
        trigger_climax_specs=climax_specs,
        reserve_stock_size=6,
        out_path="resultats_simulation_v5.csv",
        trigger_deck_size=16, trigger_deck_climax=0,
    )

    print(table.head())