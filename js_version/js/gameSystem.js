(function () {
// gameSystem.js — port of game_system.py
// main_deck / trigger_deck are plain JS arrays used as stacks: push()/pop()
// operate on the "top" of the deck (matches Python's deque.append/pop on the
// right end). Mill's "bottom" edge uses shift() (matches deque.popleft()).

function shuffleInPlace(arr, rng) {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

/** Sample k unique indices from [0, n) without replacement. */
function sampleIndices(n, k, rng) {
  const idx = Array.from({ length: n }, (_, i) => i);
  shuffleInPlace(idx, rng);
  return idx.slice(0, k);
}

class SystemBrokenError extends Error {}

class GameSystem {
  constructor(mainDeck, triggerDeck, initialTriggerStock = [], initialMainStock = [], rng = Math.random) {
    this.rng = rng;
    this.mainDeck = mainDeck.slice();
    this.discard = [];
    this.triggerDeck = triggerDeck.slice();
    this.triggerDiscard = [];
    this.triggerDeckStock = initialTriggerStock.slice();
    this.mainDeckStock = initialMainStock.slice();
    this.clockZone = [];
    this.levelZone = [];
    this.totalDamage = 0;
    this.initialMainCount = this.mainDeck.length;
    this.initialTriggerCount = this.triggerDeck.length;
    this.initialTriggerStockCount = this.triggerDeckStock.length;
    this.initialMainStockCount = this.mainDeckStock.length;
  }

  shuffle(arr) { return shuffleInPlace(arr, this.rng); }
  sample(n, k) { return sampleIndices(n, k, this.rng); }

  // -- Trigger deck structure --

  ensureTriggerDeck() {
    if (this.triggerDeck.length === 0) {
      if (this.triggerDiscard.length === 0) throw new SystemBrokenError("congrats, you just broke the system");
      this.shuffle(this.triggerDiscard);
      this.triggerDeck.push(...this.triggerDiscard);
      this.triggerDiscard.length = 0;
    }
  }

  revealTriggerCard() {
    this.ensureTriggerDeck();
    const card = this.triggerDeck.pop();
    this.triggerDeckStock.push(card);
    return card;
  }

  peekTriggerTop() {
    this.ensureTriggerDeck();
    return this.triggerDeck[this.triggerDeck.length - 1];
  }

  static cardSoul(card) { return card.nTriggers <= 2 ? card.nTriggers : 0; }

  triggerCheck() {
    const card = this.revealTriggerCard();
    return GameSystem.cardSoul(card);
  }

  twinDriveCheck() {
    let total = 0;
    for (let i = 0; i < 2; i++) total += GameSystem.cardSoul(this.revealTriggerCard());
    return total;
  }

  // -- Damage structure --

  levelup() {
    while (this.clockZone.length >= 7) {
      const batch = this.clockZone.splice(0, 7);
      const idx = batch.findIndex((c) => c.category !== "climax");
      if (idx !== -1) this.levelZone.push(batch.splice(idx, 1)[0]);
      this.discard.push(...batch);
    }
  }

  refresh() {
    if (this.discard.length === 0) throw new SystemBrokenError("congrats, you just reached the deckout lose condition");
    const newDeck = this.discard.slice();
    this.discard.length = 0;
    this.shuffle(newDeck);
    this.clockZone.push(newDeck.pop());
    this.totalDamage += 1;
    this.levelup();
    this.mainDeck.push(...newDeck);
  }

  keepCards(cards) {
    this.clockZone.push(...cards);
    this.totalDamage += cards.length;
    this.levelup();
  }

  // -- Cost primitives --

  canPayTrigger(n) { return this.triggerDeckStock.length >= n; }
  payTrigger(n) { for (let i = 0; i < n; i++) this.triggerDiscard.push(this.triggerDeckStock.pop()); }
  canPayMain(n) { return this.mainDeckStock.length >= n; }
  payMain(n) { for (let i = 0; i < n; i++) this.discard.push(this.mainDeckStock.pop()); }

  // -- Burn primitive --

  revealTriggerCards(n) {
    const cards = [];
    for (let i = 0; i < n; i++) cards.push(this.revealTriggerCard());
    const bonus = cards.reduce((s, c) => s + GameSystem.cardSoul(c), 0);
    return { bonus, cards };
  }

  resolutionCore(n) {
    const pile = [];
    let canceled = false;
    while (pile.length < n) {
      if (this.mainDeck.length === 0) { this.refresh(); continue; }
      const card = this.mainDeck.pop();
      pile.push(card);
      if (card.category === "climax") {
        this.discard.push(...pile);
        canceled = true;
        break;
      }
    }
    if (!canceled) this.keepCards(pile);
    return canceled;
  }

  resolution(n, trigger) {
    let bonus = 0;
    if (trigger === "single") ({ bonus } = this.revealTriggerCards(1));
    else if (trigger === "twin") ({ bonus } = this.revealTriggerCards(2));
    return this.resolutionCore(n + bonus);
  }

  // -- Mill primitive --

  mill(n, target, edge) {
    const isSelf = target === "self";
    const deck = isSelf ? this.triggerDeck : this.mainDeck;
    const discardPile = isSelf ? this.triggerDiscard : this.discard;

    const milled = [];
    let climaxCount = 0;
    while (milled.length < n) {
      if (deck.length === 0) {
        if (isSelf) this.ensureTriggerDeck();
        else this.refresh();
        continue;
      }
      const card = edge === "top" ? deck.pop() : deck.shift();
      discardPile.push(card);
      milled.push(card);
      if (card.category === "climax") climaxCount++;
    }
    return { climaxCount, milled };
  }

  // -- Scry primitive --

  scry(n) {
    const count = Math.min(n, this.mainDeck.length);
    const revealed = [];
    for (let i = 0; i < count; i++) revealed.push(this.mainDeck.pop());

    const climaxCards = revealed.filter((c) => c.category === "climax");
    const kept = revealed.filter((c) => c.category !== "climax");
    this.discard.push(...climaxCards);
    for (let i = kept.length - 1; i >= 0; i--) this.mainDeck.push(kept[i]);

    return { climaxCount: climaxCards.length, revealed };
  }

  // -- Shuffle primitive --

  shuffleIntoMain(moved, kept) {
    this.discard = kept;
    const newMain = this.mainDeck.concat(moved);
    this.shuffle(newMain);
    this.mainDeck.length = 0;
    this.mainDeck.push(...newMain);
  }

  shuffleDiscardIntoMain(count) {
    const eligibleIdx = [];
    this.discard.forEach((c, i) => { if (c.category !== "climax") eligibleIdx.push(i); });
    const chosen = new Set(this.sample(eligibleIdx.length, Math.min(count, eligibleIdx.length)).map((i) => eligibleIdx[i]));
    if (chosen.size === 0) return;
    const moved = this.discard.filter((c, i) => chosen.has(i));
    const kept = this.discard.filter((c, i) => !chosen.has(i));
    this.shuffleIntoMain(moved, kept);
  }

  // -- StockSwap primitive --

  recomplete(n) {
    const drawn = [];
    while (drawn.length < n) {
      if (this.mainDeck.length === 0) { this.refresh(); continue; }
      drawn.push(this.mainDeck.pop());
    }
    return drawn;
  }

  stockSwap() {
    const n = this.mainDeckStock.length;
    this.discard.push(...this.mainDeckStock);
    this.mainDeckStock.length = 0;
    this.mainDeckStock.push(...this.recomplete(n));
  }

  stockShuffle() {
    const n = this.mainDeckStock.length;
    const newMain = this.mainDeck.concat(this.mainDeckStock);
    this.mainDeckStock.length = 0;
    this.shuffle(newMain);
    this.mainDeck.length = 0;
    this.mainDeck.push(...newMain);
    this.mainDeckStock.push(...this.recomplete(n));
  }

  shuffleAllButClimaxReserve(x) {
    const climaxIdx = [];
    this.discard.forEach((c, i) => { if (c.category === "climax") climaxIdx.push(i); });
    const holdBackCount = Math.min(x, climaxIdx.length);
    const held = new Set(this.sample(climaxIdx.length, holdBackCount).map((i) => climaxIdx[i]));
    const moved = this.discard.filter((c, i) => !held.has(i));
    const kept = this.discard.filter((c, i) => held.has(i));
    this.shuffleIntoMain(moved, kept);
  }

  run(occurrences) {
    for (const occurrence of occurrences) occurrence.resolve(this);
    return this.totalDamage;
  }

  checkInvariant() {
    const tracked = this.mainDeck.length + this.discard.length + this.clockZone.length
      + this.levelZone.length + this.mainDeckStock.length;
    const expected = this.initialMainCount + this.initialMainStockCount;
    if (tracked !== expected) {
      throw new Error(
        `Card conservation inconsistency: ${tracked} cards tracked (mainDeck+discard+clockZone+levelZone` +
        `+mainDeckStock) for ${expected} at the start (initialMainCount+initialMainStockCount).`
      );
    }

    const triggerTracked = this.triggerDeck.length + this.triggerDiscard.length + this.triggerDeckStock.length;
    const triggerExpected = this.initialTriggerCount + this.initialTriggerStockCount;
    if (triggerTracked !== triggerExpected) {
      throw new Error(
        `Trigger card conservation inconsistency: ${triggerTracked} cards tracked ` +
        `(triggerDeck+triggerDiscard+triggerDeckStock) for ${triggerExpected} at the start ` +
        `(initialTriggerCount+initialTriggerStockCount).`
      );
    }
  }
}

function runTrialFromDecks(mainDeck, triggerDeck, triggerDeckStock, mainDeckStock, occurrences, checkInvariants = false, rng = Math.random) {
  const state = new GameSystem(mainDeck, triggerDeck, triggerDeckStock, mainDeckStock, rng);
  const damage = state.run(occurrences);
  if (checkInvariants) state.checkInvariant();
  return damage;
}

const _exports = { GameSystem, SystemBrokenError, runTrialFromDecks, shuffleInPlace, sampleIndices };
if (typeof module !== "undefined") {
  module.exports = _exports;
} else {
  window.TCG = window.TCG || {};
  Object.assign(window.TCG, _exports);
}

})();
