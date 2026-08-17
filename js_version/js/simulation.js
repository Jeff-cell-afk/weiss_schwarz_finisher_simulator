(function () {
// simulation.js — port of simulation.py, adapted to run in the browser
// (async chunked loop instead of a multiprocessing pool; a small seedable
// PRNG instead of numpy.random.Generator).
const dep = (name) => (typeof module !== "undefined" ? require(name) : window.TCG);

function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function makeRng(seed) {
  return seed === null || seed === undefined ? Math.random : mulberry32(seed);
}

function probsFromResults(results, thresholds) {
  const sorted = Float64Array.from(results).sort();
  const n = sorted.length;
  return thresholds.map((t) => {
    // first index with sorted[idx] >= t
    let lo = 0, hi = n;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (sorted[mid] < t) lo = mid + 1; else hi = mid;
    }
    const count = n - lo;
    return Math.round((count / n) * 10000) / 10000;
  });
}

/**
 * Runs one (deckSize, climaxN) combination for nTrials, yielding to the
 * event loop every `chunkSize` trials so the tab doesn't freeze.
 */
async function runCombination(params, pools, occurrences, onProgress) {
  const {
    buildMainDeckAndStock, buildTriggerDeckAndStock,
  } = dep("./deck");
  const { runTrialFromDecks } = dep("./gameSystem");

  const {
    size, climaxN, triggerDeckSize, triggerDeckClimax, triggerDeckStockSize,
    mainDeckStockSize, nTrials, checkInvariants, seed,
  } = params;

  const rng = makeRng(seed);
  const results = new Float64Array(nTrials);
  const chunkSize = 200;

  for (let i = 0; i < nTrials; i++) {
    const { deck: mainDeck, stock: mainStock } = buildMainDeckAndStock(
      pools.mainClimax, pools.mainNonClimax, size, climaxN, mainDeckStockSize, rng,
    );
    const { deck: triggerDeck, stock: triggerStock } = buildTriggerDeckAndStock(
      pools.triggerClimax, pools.triggerNonClimax, triggerDeckSize, triggerDeckClimax, triggerDeckStockSize, rng,
    );
    results[i] = runTrialFromDecks(mainDeck, triggerDeck, triggerStock, mainStock, occurrences, checkInvariants, rng);

    if (i % chunkSize === chunkSize - 1) {
      if (onProgress) onProgress(i + 1, nTrials);
      // eslint-disable-next-line no-await-in-loop
      await new Promise((resolve) => setTimeout(resolve, 0));
    }
  }
  if (onProgress) onProgress(nTrials, nTrials);
  return results;
}

/**
 * @param {object} config - see buildDefaultConfig() in app.js for shape
 * @param {function} [onProgress] - ({combinationIndex, totalCombinations, size, climaxN, trialsDone, trialsTotal}) => void
 */
async function generateTable(config, onProgress) {
  const { buildPools, validatePools } = dep("./pools");
  const { parseOccurrences, validateOccurrenceCosts, maxPossibleDamage } = dep("./grammar");

  const pools = buildPools(
    config.mainNonClimaxSpecs, config.mainClimaxSpecs,
    config.triggerNonClimaxSpecs, config.triggerClimaxSpecs,
  );
  validatePools(
    pools, config.deckSizeList, config.climaxList,
    config.triggerDeckSize, config.triggerDeckClimax,
    config.triggerDeckStockSize, config.mainDeckStockSize,
  );
  const occurrences = parseOccurrences(config.occurrences);
  validateOccurrenceCosts(occurrences, config.triggerDeckStockSize);

  const maxTriggerLevel = pools.maxTriggerLevel;
  const maxMainLevel = pools.maxMainLevel;

  const maxDamageColumn = config.maxDamageColumn ?? maxPossibleDamage(
    occurrences, config.deckSizeList, maxTriggerLevel, maxMainLevel,
  );
  const thresholds = Array.from({ length: maxDamageColumn + 1 }, (_, i) => i);
  const columns = thresholds.map((t) => `P(total_damage>=${t})`);

  const combinations = [];
  for (const size of config.deckSizeList) {
    for (const climaxN of config.climaxList) {
      if (climaxN < size) combinations.push([size, climaxN]);
    }
  }

  const rows = [];
  for (let ci = 0; ci < combinations.length; ci++) {
    const [size, climaxN] = combinations[ci];
    const params = {
      size, climaxN,
      triggerDeckSize: config.triggerDeckSize,
      triggerDeckClimax: config.triggerDeckClimax,
      triggerDeckStockSize: config.triggerDeckStockSize,
      mainDeckStockSize: config.mainDeckStockSize,
      nTrials: config.nTrials,
      checkInvariants: !!config.checkInvariants,
      seed: config.seed === null || config.seed === undefined ? undefined : config.seed + ci,
    };
    // eslint-disable-next-line no-await-in-loop
    const results = await runCombination(params, pools, occurrences, (trialsDone, trialsTotal) => {
      if (onProgress) {
        onProgress({
          combinationIndex: ci, totalCombinations: combinations.length,
          size, climaxN, trialsDone, trialsTotal,
        });
      }
    });
    const probs = probsFromResults(results, thresholds);
    rows.push({ main_deck_size: size, climax_number: climaxN, probs });
  }

  return { columns, thresholds, rows, maxDamageColumn };
}

const _exports = { mulberry32, makeRng, probsFromResults, runCombination, generateTable };
if (typeof module !== "undefined") {
  module.exports = _exports;
} else {
  window.TCG = window.TCG || {};
  Object.assign(window.TCG, _exports);
}

})();
