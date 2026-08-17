# User Manual — Damage Simulator

A standalone application (`index.html`) that runs entirely in the browser: no data
is sent to a server, no installation required. Just open `index.html` in a modern
browser (Chrome, Firefox, Edge, Safari).

The app simulates a large number of game turns (Monte Carlo) to estimate, for each
deck-size / climax-count combination, the probability of dealing at least N damage
in a turn.

---

## Overview of the 5 steps

| # | Section | What happens here |
|---|---------|--------------------|
| 1 | Card pool | Describe the cards available and how many copies of each |
| 2 | Deck configuration | Deck sizes, climax count, trigger deck, stocks |
| 3 | Effect sequence | Build the actions played on each trial |
| 4 | Simulation | Number of trials, random seed, run |
| 5 | Results | Probability table, curves, CSV export |

Sections recompute as you go: nothing is lost as long as the tab stays open, but
there is **no automatic save between sessions** (see [Limitations](#limitations-to-know-about)
at the end of this document).

---

## 1. Card pool

This is the equivalent of `main_non_climax_specs` / `main_climax_specs` in your Python
version: the list of cards that exist, with how many copies of each. Each trial's
deck is then drawn randomly from this pool.

- **Main deck — non-climax cards**: one row per card (level, number of triggers ♥,
  Character/Event type, color, number of copies).
- **Main deck — climax cards**: same thing, without the "type" field (fixed to climax).
- **"Use the same pool for the trigger deck"** (checked by default): the trigger deck
  is built from the same cards as the main deck — this is the most common case (a
  single 50-card deck, some of which is set aside as the trigger deck). Uncheck this
  box if you want to define a different trigger deck pool; two additional tables then
  appear.
- **+ Add a card**: adds an empty row at the bottom of the table.
- **✕** at the end of a row: removes the corresponding card.

> Tip: if a deck-size/climax combination later fails with an error like *"Pool only
> contains N copies, but M are needed"*, this is where you need to increase the
> number of copies of a card.

---

## 2. Deck configuration

| Field | Role |
|---|---|
| Deck sizes tested | Comma-separated list (e.g. `20, 25, 30`) — each size is simulated separately |
| Climax counts tested | Same (e.g. `4, 6, 8`) — combined with each deck size (combinations where climax ≥ size are skipped) |
| Trigger deck size | Number of cards in the trigger deck |
| Climax in the trigger deck | Number of climax cards among them |
| Trigger deck stock | Trigger cards already held in reserve at the start of the turn (lets you pay costs without having triggered a check) |
| Main deck stock | Main deck cards already held in reserve at the start |

Total number of combinations simulated = (number of deck sizes) × (number of valid
climax counts). With the default example (3 sizes × 3 climax counts), that's 9
combinations.

---

## 3. Effect sequence

This is the core of the tool: the sequence of actions played on each trial, in order
(equivalent to the `occurrences` list in `SimulationConfig`). Each colored block is
an independent action; **+ Add an action** adds a new one at the bottom of the list.

Each block has:
- a small number field on the far left: the **cost in trigger stock cards** to pay to
  trigger the action (0 = free);
- a dropdown to choose the **mechanic**.

Below the list, a **read-only preview** shows the generated DSL string for each
action (the exact string your Python engine would understand) — useful for quickly
checking what's been built, or spotting an error (a struck-through red line with the
error message underneath).

### Available mechanics

**Burn** — deals direct damage.
- *Damage (n)*: number of cards drawn and kept (canceled if a climax card appears).
- *Trigger check*: none / single / twin drive — reveals 1 or 2 extra trigger deck
  cards, whose bonus (♥) is added to the damage.
- If a trigger check is active, an **ONREVEAL** checkbox lets you trigger an
  additional effect when the revealed card matches a condition (see
  [Conditions](#conditions) below).

**Mill** — discards cards from the top or bottom of a deck (yours or the opponent's),
with 4 possible behaviors:
- *Deals damage equal to climax cards discarded*: damage = number of climax cards
  among the discarded cards.
- *Triggers an effect for each climax discarded*: nests an action to repeat.
- *Deals damage based on the card's level*: a single card discarded, damage = its
  level (+ an adjustable bonus/malus).
- *Triggers an effect if the card matches a condition*: a single card discarded,
  tested against a condition.

**TopCheck** — looks at the top card of the trigger deck without drawing it.
- Unchecked: automatically deals damage equal to that card's level.
- Checked ("Conditional effect"): triggers a nested effect if the card matches a
  condition.

**StockSwap** — discards the entire main deck stock and rebuilds it by drawing the
same number of new cards. No parameters.

**StockShuffle** — shuffles the main deck stock back into the main deck, then draws
the same number of cards to rebuild the stock. No parameters.

**ShuffleAll** — shuffles the whole discard pile into the main deck, keeping aside a
chosen number of climax cards (parameter *x*).

**Scry** — looks at the top *n* cards of the main deck, discards any climax cards
among them, returns the rest in the same order.

**Shuffle** — shuffles *x* non-climax cards from the discard pile back into the main
deck, then always chains into a following effect ("Then: …"). Unlike other
mechanics, its cost can be paid in two parts: a cost before (the field on the far
left of the block) and a **cost after** (a dedicated field), paid *simultaneously* —
that's why this block has no "chain a following effect" checkbox: the "Then" clause
already plays that role.

**OnCancel** — watches a primary effect (often a Burn); if it gets canceled (a
climax card appeared during its resolution), one or more fallback effects trigger.
**+ Add an effect** lets you chain several of them.

### Chaining a following effect

On (almost) every block, an **"Immediately chain another effect after this one"**
checkbox lets you nest an additional action that plays right after, regardless of
the outcome of the first one (unlike OnCancel, which only triggers on cancellation).
Only Shuffle doesn't have this checkbox, since its "Then" clause already plays that
role.

### Conditions

Several mechanics (Mill…IF, conditional TopCheck, Burn…ONREVEAL) require defining a
**condition** a card must meet:
- an optional level filter (=, ≥, ≤, with a value);
- a card type (any, climax, non-climax, character, event);
- one or more colors to check (none checked = all colors accepted).

---

## 4. Simulation

- **Number of trials per combination**: the higher this number, the more precise the
  estimate, but the longer the simulation — everything runs in a single browser
  thread (unlike your Python version, which uses `multiprocessing` + `numpy`). For a
  first try, stay around 1,000 to 5,000; go up to 10,000+ once the config is
  validated, if the wait time stays acceptable.
- **Random seed (optional)**: leave empty for a different result on every click, or
  enter a number to be able to reproduce the exact same trial later.
- **Verify card conservation on every trial**: enables the same debug assertion as
  `check_invariants=True` on the Python side (checks that no card is duplicated or
  lost). Useful for debugging, slower — leave unchecked for normal use.
- **Run simulation**: starts the computation. A status line shows progress (current
  combination, percentage of trials done). The button is disabled while running.

If the configuration contains an error (a structurally unpayable cost, a pool that's
too small, etc.), an error message is shown instead of results — this is the same
validation as `validate_pools` / `validate_occurrence_costs` on the Python side.

---

## 5. Results

A table appears, one row per combination (deck size × climax count):

- The **P(damage ≥ N)** columns give, for each threshold N, the probability of
  reaching at least that total damage in the simulated turn. The darker green the
  cell, the higher the probability.
- The **Curve** column plots a mini sparkline of that probability as a function of
  the threshold — handy for visually comparing several configurations at a glance.
- **Download as CSV** exports the full table (same columns as the file produced by
  `SimulationConfig.out_path` on the Python side).

---

## Limitations to know about

- **No save between sessions**: reloading the page resets everything to the example
  config. If you want to keep a configuration, note down the DSL sequence shown in
  the preview, or export the results CSV before closing the tab.
- **Single-threaded**: slower than your vectorized Python version with `numpy` +
  `multiprocessing`, especially with many combinations × many trials. The
  simulation doesn't freeze the tab (it yields to the browser every 200 trials), but
  it can take a while on large volumes.
- **Generated DSL isn't hand-editable**: the preview is read-only by design (to keep
  the interface accessible to someone unfamiliar with the grammar) — any change must
  go through the dropdowns.

---

## Troubleshooting

| Symptom | Lead |
|---|---|
| Error *"Pool 'X' only contains N copies..."* | Increase the number of copies of the card in question in step 1 |
| Error *"Structurally unpayable cost"* | A cost (Shuffle, or a cost on an action) can never be paid with the configured triggers/burns — revisit the effect sequence or the trigger deck's starting stock |
| A line in the DSL preview is struck through in red | A field of the corresponding mechanic is likely empty or inconsistent (e.g. missing level) — reopen the block and check its fields |
| The simulation seems stuck | Check the number of trials × number of combinations; reduce it if needed, the computation is single-threaded |
