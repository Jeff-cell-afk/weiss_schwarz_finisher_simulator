from .models import Card

# Main deck
MAIN_NON_CLIMAX_SPECS = {
    Card(0, 0, False): 8,
    Card(0, 1, False): 6,
    Card(1, 0, False): 8,
    Card(1, 1, False): 6,
    Card(2, 0, False): 8,
    Card(2, 1, False): 6,
    Card(3, 0, False): 8,
    Card(3, 1, False): 4,
}

MAIN_CLIMAX_SPECS = {
    Card(0, 0, True): 4,
    Card(0, 1, True): 4,
    Card(0, 2, True): 4,
}

# Trigger deck
TRIGGER_NON_CLIMAX_SPECS = {
    Card(0, 0, False): 17,
    Card(0, 1, False): 0,
    Card(1, 0, False): 12,
    Card(1, 1, False): 0,
    Card(2, 0, False): 0,
    Card(2, 1, False): 3,
    Card(3, 0, False): 3,
    Card(3, 2, False): 7,
}

TRIGGER_CLIMAX_SPECS = {
    Card(0, 0, True): 4,
    Card(0, 1, True): 4,
    Card(0, 2, True): 0,
}

TRIGGER_DECK_SIZE = 16
TRIGGER_DECK_CLIMAX = 0

MAIN_DECK_SIZES = [40, 50]
CLIMAX_NUMBERS = [6, 8]