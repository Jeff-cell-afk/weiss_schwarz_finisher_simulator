(function () {
// deck.js — port of deck.py
// No numpy batch-vectorization needed here: JS runs each trial's deck
// construction directly, which is plenty fast for browser-scale trial counts.
const dep = (name) => (typeof module !== "undefined" ? require(name) : window.TCG);

function buildMainDeckAndStock(climaxPool, nonClimaxPool, deckSize, climaxN, stockSize, rng) {
  const { sampleIndices, shuffleInPlace } = dep("./gameSystem");

  const climaxIdx = sampleIndices(climaxPool.length, climaxN, rng);
  const nonClimaxNeeded = (deckSize - climaxN) + stockSize;
  const nonClimaxIdx = sampleIndices(nonClimaxPool.length, nonClimaxNeeded, rng);
  const deckNonClimaxIdx = nonClimaxIdx.slice(0, deckSize - climaxN);
  const stockNonClimaxIdx = nonClimaxIdx.slice(deckSize - climaxN);

  const deckCards = climaxIdx.map((i) => climaxPool[i]).concat(deckNonClimaxIdx.map((i) => nonClimaxPool[i]));
  shuffleInPlace(deckCards, rng);

  const mainDeckStock = stockNonClimaxIdx.map((i) => nonClimaxPool[i]);

  return { deck: deckCards, stock: mainDeckStock };
}

function buildTriggerDeckAndStock(climaxPool, nonClimaxPool, deckSize, climaxN, stockSize, rng) {
  const { sampleIndices, shuffleInPlace } = dep("./gameSystem");

  const climaxIdx = sampleIndices(climaxPool.length, climaxN, rng);
  const nonClimaxNeeded = (deckSize - climaxN) + stockSize;
  const nonClimaxIdx = sampleIndices(nonClimaxPool.length, nonClimaxNeeded, rng);
  const deckNonClimaxIdx = nonClimaxIdx.slice(0, deckSize - climaxN);
  const stockNonClimaxIdx = nonClimaxIdx.slice(deckSize - climaxN);

  const deckCards = climaxIdx.map((i) => climaxPool[i]).concat(deckNonClimaxIdx.map((i) => nonClimaxPool[i]));
  shuffleInPlace(deckCards, rng);

  const triggerDeckStock = stockNonClimaxIdx.map((i) => nonClimaxPool[i]);

  return { deck: deckCards, stock: triggerDeckStock };
}

const _exports = { buildMainDeckAndStock, buildTriggerDeckAndStock };
if (typeof module !== "undefined") {
  module.exports = _exports;
} else {
  window.TCG = window.TCG || {};
  Object.assign(window.TCG, _exports);
}

})();
