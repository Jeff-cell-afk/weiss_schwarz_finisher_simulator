from simulateur import Card, generate_table, SimulationConfig

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

    config = SimulationConfig(
        deck_size_list=[20, 25, 30],
        climax_list=[4, 6, 8],
        occurrences=["BURN(4)", "BURN(3)/A", "BURN(4)", "BURN(3)/A", "BURN(4)", "BURN(3)/A"],
        n_trials=20000,
        main_non_climax_specs=non_climax_specs,
        main_climax_specs=climax_specs,
        trigger_non_climax_specs=non_climax_specs,
        trigger_climax_specs=climax_specs,
        out_path="simulation_results_v5.csv",
        trigger_deck_size=16, trigger_deck_climax=0,
        trigger_deck_stock_size=2, main_deck_stock_size=2,
    )
    table = generate_table(config)

    print(table.head())