from .models import Card

# Main deck
MAIN_NON_CLIMAX_SPECS = {
    Card(0, 0, "character", "yellow"): 8,
    Card(0, 1, "character", "yellow"): 6,
    Card(1, 0, "character", "yellow"): 8,
    Card(1, 1, "character", "yellow"): 6,
    Card(2, 0, "character", "yellow"): 8,
    Card(2, 1, "character", "yellow"): 6,
    Card(3, 0, "character", "yellow"): 8,
    Card(3, 1, "character", "yellow"): 4,
}

MAIN_CLIMAX_SPECS = {
    Card(0, 0, "climax", "yellow"): 4,
    Card(0, 1, "climax", "yellow"): 4,
    Card(0, 2, "climax", "yellow"): 4,
}

# Trigger deck
TRIGGER_NON_CLIMAX_SPECS = {
    Card(0, 0, "character", "yellow"): 17,
    Card(0, 1, "character", "yellow"): 0,
    Card(1, 0, "character", "yellow"): 12,
    Card(1, 1, "character", "yellow"): 0,
    Card(2, 0, "character", "yellow"): 0,
    Card(2, 1, "character", "yellow"): 3,
    Card(3, 0, "character", "yellow"): 3,
    Card(3, 2, "character", "yellow"): 7,
}

TRIGGER_CLIMAX_SPECS = {
    Card(0, 0, "climax", "yellow"): 4,
    Card(0, 1, "climax", "yellow"): 4,
    Card(0, 2, "climax", "yellow"): 0,
}

TRIGGER_DECK_SIZE = 16
TRIGGER_DECK_CLIMAX = 0

MAIN_DECK_SIZES = [40, 50]
CLIMAX_NUMBERS = [6, 8]