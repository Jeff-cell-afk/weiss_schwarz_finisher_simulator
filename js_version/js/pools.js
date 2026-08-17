(function () {
// pools.js — port of pools.py
// Works both under Node (CommonJS, used by test.js) and in the browser,
// where every module's exports are merged into a flat `window.TCG` object
// loaded in dependency order by index.html.
const dep = (name) => (typeof module !== "undefined" ? require(name) : window.TCG);

/**
 * @param {Array<{card: object, count: number}>} cardCounts - list of {card, count}
 * (JS objects can't be used as Map keys the way Python dataclasses are dict keys,
 * so we use an array of {card, count} pairs instead of a dict.)
 */
function expandPool(cardCounts) {
  const pool = [];
  for (const { card, count } of cardCounts) {
    if (!Number.isInteger(count) || count <= 0) {
      throw new Error(`Invalid count for card: ${JSON.stringify(count)} (expected an integer > 0).`);
    }
    for (let i = 0; i < count; i++) pool.push(card);
  }
  return pool;
}

function buildPools(mainNonClimaxSpecs, mainClimaxSpecs, triggerNonClimaxSpecs, triggerClimaxSpecs) {
  const { makePools } = dep("./models");
  return makePools(
    expandPool(mainClimaxSpecs),
    expandPool(mainNonClimaxSpecs),
    expandPool(triggerClimaxSpecs),
    expandPool(triggerNonClimaxSpecs),
  );
}

function validatePools(pools, deckSizeList, climaxList, triggerDeckSize, triggerDeckClimax,
                        triggerDeckStockSize = 0, mainDeckStockSize = 0) {
  if (triggerDeckClimax > triggerDeckSize) {
    throw new Error(
      `trigger_deck_climax (${triggerDeckClimax}) cannot exceed trigger_deck_size (${triggerDeckSize}).`
    );
  }
  if (triggerDeckStockSize < 0) {
    throw new Error(`trigger_deck_stock_size (${triggerDeckStockSize}) cannot be negative.`);
  }
  if (mainDeckStockSize < 0) {
    throw new Error(`main_deck_stock_size (${mainDeckStockSize}) cannot be negative.`);
  }

  const validPairs = [];
  for (const s of deckSizeList) {
    for (const c of climaxList) {
      if (c < s) validPairs.push([s, c]);
    }
  }
  if (validPairs.length === 0) {
    throw new Error("No valid (deck_size, climax_n) combination: climax_n < deck_size is required for at least one tested pair.");
  }

  const poolSizes = {
    main_climax: pools.mainClimax.length,
    main_non_climax: pools.mainNonClimax.length,
    trigger_climax: pools.triggerClimax.length,
    trigger_non_climax: pools.triggerNonClimax.length,
  };

  const needed = {
    main_climax: Math.max(...climaxList),
    main_non_climax: Math.max(...validPairs.map(([s, c]) => s - c)) + mainDeckStockSize,
    trigger_climax: triggerDeckClimax,
    trigger_non_climax: (triggerDeckSize - triggerDeckClimax) + triggerDeckStockSize,
  };

  for (const field of Object.keys(needed)) {
    if (poolSizes[field] < needed[field]) {
      throw new Error(
        `Pool '${field}' only contains ${poolSizes[field]} copies, but at least ${needed[field]} are needed. ` +
        `Increase the number of copies per card in the corresponding specs.`
      );
    }
  }
}

const _exports = { expandPool, buildPools, validatePools };
if (typeof module !== "undefined") {
  module.exports = _exports;
} else {
  window.TCG = window.TCG || {};
  Object.assign(window.TCG, _exports);
}

})();
