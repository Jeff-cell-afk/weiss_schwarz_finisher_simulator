(function () {
// models.js — port of models.py
// Card is a plain frozen-like object (validated at creation, never mutated).

const CATEGORIES = ["character", "event", "climax"];
const COLORS = ["yellow", "green", "red", "blue", "purple"];

function isValidPositiveInt(value) {
  return Number.isInteger(value) && value > 0;
}

function isValidNonNegativeInt(value) {
  return Number.isInteger(value) && value >= 0;
}

function validateField(name, value, allowZero) {
  const ok = allowZero ? isValidNonNegativeInt(value) : isValidPositiveInt(value);
  if (!ok) {
    throw new TypeError(
      `invalid ${name}: ${JSON.stringify(value)} (expected an integer ${allowZero ? ">= 0" : "> 0"})`
    );
  }
}

/**
 * Creates and validates a Card. Cards are immutable plain objects.
 * @param {number} level
 * @param {number} nTriggers
 * @param {string} category - one of CATEGORIES
 * @param {string} color - one of COLORS
 */
function makeCard(level, nTriggers, category, color) {
  validateField("level", level, true);
  validateField("nTriggers", nTriggers, true);
  if (!CATEGORIES.includes(category)) {
    throw new Error(`invalid category: ${JSON.stringify(category)} (expected one of ${CATEGORIES})`);
  }
  if (!COLORS.includes(color)) {
    throw new Error(`invalid color: ${JSON.stringify(color)} (expected one of ${COLORS})`);
  }
  return Object.freeze({ level, nTriggers, category, color });
}

/**
 * Pools: the four card pools that decks are drawn from.
 * @param {Array} mainClimax
 * @param {Array} mainNonClimax
 * @param {Array} triggerClimax
 * @param {Array} triggerNonClimax
 */
function makePools(mainClimax, mainNonClimax, triggerClimax, triggerNonClimax) {
  const maxLevel = (pools) => pools.reduce((m, c) => Math.max(m, c.level), 0);
  return {
    mainClimax,
    mainNonClimax,
    triggerClimax,
    triggerNonClimax,
    get maxTriggerLevel() {
      return maxLevel([...triggerClimax, ...triggerNonClimax]);
    },
    get maxMainLevel() {
      return maxLevel([...mainClimax, ...mainNonClimax]);
    },
  };
}

const _exports = {
  CATEGORIES, COLORS, isValidPositiveInt, isValidNonNegativeInt,
  makeCard, makePools,
};
if (typeof module !== "undefined") {
  module.exports = _exports;
} else {
  window.TCG = window.TCG || {};
  Object.assign(window.TCG, _exports);
}

})();
