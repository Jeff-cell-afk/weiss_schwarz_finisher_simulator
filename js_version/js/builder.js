(function () {
// builder.js — turns a small JSON tree (edited via dropdowns in the UI)
// into DSL strings that js/grammar.js's parseOccurrence() can read.
// This is the "visible but simplified" layer: the user never types DSL,
// but the generated DSL is shown read-only so it stays inspectable.

const CARD_TYPE_LABELS = {
  card: "CARD",
  climax: "CLIMAX CARD",
  "non-climax": "NON CLIMAX CARD",
  character: "CHARACTER CARD",
  event: "EVENT CARD",
};

let _uid = 0;
function nextId() { return `n${++_uid}`; }

function defaultCondition() {
  return { id: nextId(), levelCmp: null, levelValue: 2, cardType: "climax", colors: [] };
}

function conditionToString(cond) {
  const parts = [];
  if (cond.levelCmp) parts.push(`LEVEL${cond.levelCmp}${cond.levelValue}`);
  const tail = [];
  if (cond.colors && cond.colors.length) tail.push(cond.colors.join(" OR "));
  tail.push(CARD_TYPE_LABELS[cond.cardType] || "CARD");
  parts.push(tail.join(" "));
  return parts.join(" ").trim();
}

/** Creates a default occurrence node for a given effect type. */
function defaultNode(effectType) {
  const base = { id: nextId(), cost: 0, effectType };
  switch (effectType) {
    case "BURN":
      return { ...base, n: 2, trigger: null, onReveal: null };
    case "MILL":
      return { ...base, n: 1, target: "self", edge: "top", mode: "count", offset: 0, condition: null, then: null };
    case "TOPCHECK":
      return { ...base, conditional: false, condition: null, then: null };
    case "STOCKSWAP":
    case "STOCKSHUFFLE":
      return base;
    case "SHUFFLEALL":
      return { ...base, x: 1 };
    case "SCRY":
      return { ...base, n: 2 };
    case "SHUFFLE":
      return { ...base, x: 1, costAfter: 0, then: defaultNode("BURN") };
    case "ONCANCEL":
      return { ...base, primary: defaultNode("BURN"), thenList: [defaultNode("BURN")] };
    default:
      throw new Error(`Unknown effect type: ${effectType}`);
  }
}

/** Renders a node (and everything nested under it) as a DSL string. */
function nodeToString(node) {
  if (node.effectType === "SHUFFLE") {
    const prefix = node.cost ? `(${node.cost})` : "";
    const after = node.costAfter ? `(${node.costAfter})` : "";
    return `${prefix}SHUFFLE(${node.x})${after}->${nodeToString(node.then)}`;
  }

  const prefix = node.cost ? `(${node.cost})` : "";
  const effectStr = effectToString(node);
  const suffix = node.followUp ? `[${nodeToString(node.followUp)}]` : "";
  return `${prefix}${effectStr}${suffix}`;
}

function effectToString(node) {
  switch (node.effectType) {
    case "BURN": {
      let s = `BURN(${node.n})`;
      if (node.trigger === "single") s += "/A";
      if (node.trigger === "twin") s += "/T";
      if (node.onReveal) {
        s += ` ONREVEAL "${conditionToString(node.onReveal.condition)}" THEN ${nodeToString(node.onReveal.then)}`;
      }
      return s;
    }
    case "MILL": {
      const head = `MILL(${node.n}) ${node.target.toUpperCase()} ${node.edge.toUpperCase()}`;
      if (node.mode === "count") return `${head} COUNT`;
      if (node.mode === "each") return `${head} EACH[${nodeToString(node.then)}]`;
      if (node.mode === "level") return `${head} LEVEL${node.offset ? `+${node.offset}` : ""}`;
      // if
      return `${head} IF "${conditionToString(node.condition)}" THEN ${nodeToString(node.then)}`;
    }
    case "TOPCHECK":
      if (!node.conditional) return "TOPCHECK";
      return `TOPCHECK IF "${conditionToString(node.condition)}" THEN ${nodeToString(node.then)}`;
    case "STOCKSWAP": return "STOCKSWAP";
    case "STOCKSHUFFLE": return "STOCKSHUFFLE";
    case "SHUFFLEALL": return `SHUFFLEALL(${node.x})`;
    case "SCRY": return `SCRY(${node.n})`;
    case "ONCANCEL":
      return `ONCANCEL[${node.thenList.map(nodeToString).join(";")}] ON ${nodeToString(node.primary)}`;
    default:
      throw new Error(`Unknown effect type: ${node.effectType}`);
  }
}

const EFFECT_LABELS = {
  BURN: "Burn (direct damage)",
  MILL: "Mill (discard from a deck)",
  TOPCHECK: "TopCheck (look at the top of the trigger deck)",
  STOCKSWAP: "StockSwap (refresh the main stock)",
  STOCKSHUFFLE: "StockShuffle (shuffle stock into the main deck)",
  SHUFFLEALL: "ShuffleAll (shuffle the discard pile into the deck)",
  SCRY: "Scry (look at/reorder the top of the deck)",
  SHUFFLE: "Shuffle (reshuffle N cards from discard, simultaneous cost)",
  ONCANCEL: "OnCancel (triggered if the primary effect is canceled)",
};

const _exports = { defaultNode, nodeToString, conditionToString, defaultCondition, EFFECT_LABELS, CARD_TYPE_LABELS };
if (typeof module !== "undefined") {
  module.exports = _exports;
} else {
  window.TCG = window.TCG || {};
  Object.assign(window.TCG, _exports);
}

})();
