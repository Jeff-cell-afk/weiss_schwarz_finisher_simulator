# Weiss Schwarz Finisher Simulator

A Python-based simulation engine for Weiss Schwarz, optimized for execution within Jupyter Notebooks.

## Prerequisites & Setup

* **Python Dependencies:** Install the required modules listed in `requirements.txt`.
* **Execution:** Refer to `main.py` for standard usage examples and customizable options (deck configurations, occurrence sequences, etc.).

---

## Core Mechanics

* **Roles:** The attacking player acts as the **Trigger Deck**, while the opponent acts as the **Main Deck**.
* **Card Definition:** Cards are defined using the following format:
  `Card(level, soul_trigger, "card_type", "card_color"): card_ratio_in_deck`
* **Deck Construction:** Cards are drawn randomly from your pre-defined card pools based on specified ratios to eliminate bias regarding deck state.
* **Initial Stock:** You can specify an `initial_stock` parameter for both decks.
  > **Important:** If a deck cannot pay a required cost, the system automatically negates the associated occurrence. Ensure `initial_stock` is set correctly before launching simulations.
* **Starting State:** Discard piles for both players are assumed to be empty at the start of a sequence.

---

## Occurrence Syntax & Rules

An **occurrence** refers to any source of damage (auto-attacks, card effects, etc.). All damage is written as `BURN(X)`, where `X` represents the amount of damage dealt.

### Modifiers & Cost

* **Triggers (`/A`, `/T`):** Append `/A` to add a single trigger check, or `/T` for a double trigger check.  
  * *Example:* `BURN(2)/T` (2-damage auto-attack with a double trigger check before resolution).
* **On-Reveal Conditional (`ONREVEAL`):** Append `ONREVEAL "condition" THEN <occurrence>` after a `/A` or `/T` trigger to resolve an extra occurrence for each revealed trigger card matching the condition, on top of the base burn (and its usual soul-trigger bonus). Requires a trigger suffix — there is no card to inspect without one. Conditions follow the same syntax as `TOPCHECK`/`MILL...IF` (see Command Reference below).
  * *Example:* `BURN(3)/T ONREVEAL "Character or Event Card" THEN BURN(3)` (3-damage twin-drive attack; for each of the 2 revealed cards that is a character or an event, an extra 2-damage burn is resolved).
* **Cost `(COST)`:** Place cost requirements in parentheses before an occurrence.

---

### Command Reference

| Keyword | Description & Syntax | Example |
| :--- | :--- | :--- |
| **`TOPCHECK`** | Reveals the top card of the trigger deck and deals damage equal to its level. Can include conditional checks on card properties. <br> *Valid types:* `Card`, `Climax Card`, `Non-Climax Card`, `Character Card`, `Event Card`. | `TOPCHECK IF "Blue or Yellow Non-Climax Card" THEN BURN(3)` |
| **`MILL`** | Mills $n$ cards from target (`SELF` or `OPP`) at position (`TOP` or `BOTTOM`). <br> Modes: <br> • `COUNT`: Deals damage equal to climaxes milled. <br> • `EACH[occurrence]`: Applies occurrence per climax milled. <br> • `LEVEL+k`: Deals damage equal to card level + $k$ *(Only works with `MILL(1)`)*. | `MILL(2) OPP BOTTOM EACH[BURN(2)]` *(Mills bottom 2 cards of opponent deck; deals 2 damage per climax milled)* |
| **`SHUFFLE`** | `SHUFFLE(X)->` Shuffles up to $X$ non-climax cards from the main deck's discard pile back into the deck, then resolves the following occurrence. | `SHUFFLE(2)->BURN(2)` |
| **`SHUFFLEALL`** | `SHUFFLEALL(X)` Shuffles all cards from the main deck's discard pile back into the deck, except for $X$ climaxes. | `SHUFFLEALL(1)` |
| **`ONCANCEL`** | `ONCANCEL[a;b;...] ON x` Attempts to apply $x$. If $x$ is cancelled, applies effects $a, b, \dots$ in sequence. | `ONCANCEL[BURN(1);BURN(1)] ON BURN(3)` |
| **`STOCKSWAP`** | Moves all cards from the main deck's stock to the discard pile, then puts an equal number of cards from the top of the deck into stock. | `STOCKSWAP` |
| **`STOCKSHUFFLE`** | Sends all cards from the main deck's stock back to the deck, shuffles it, and puts the same number of cards back into stock. | `STOCKSHUFFLE` |
