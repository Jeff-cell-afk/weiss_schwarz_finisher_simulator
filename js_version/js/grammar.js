(function () {
// grammar.js — port of grammar.py
// Faithful translation of the occurrence DSL: tokenizer, recursive-descent
// parser, Effect classes, and the Occurrence wrapper (cost / follow_up).

const TRIGGER_DAMAGE_BONUS = { null: 0, single: 2, twin: 4 };
const TRIGGER_STOCK_BONUS = { null: 0, single: 1, twin: 2 };
const TRIGGER_CHECK_COUNT = { null: 0, single: 1, twin: 2 };
const COLOR_WORDS = new Set(["YELLOW", "GREEN", "RED", "BLUE", "PURPLE"]);

// ---------------------------------------------------------------------
// Effects
// ---------------------------------------------------------------------

class Effect {
  static JOINT_COST = false;
  resolve(_gs) { throw new Error("not implemented"); }
  maxDamage(_ctx) { throw new Error("not implemented"); }
}

class Burn extends Effect {
  constructor(n, trigger = null, onReveal = null) {
    super();
    if (n < 0) throw new Error(`Burn.n must be >= 0, got ${n}`);
    if (![null, "single", "twin"].includes(trigger)) throw new Error(`invalid trigger: ${trigger}`);
    if (onReveal !== null && trigger === null) {
      throw new Error(
        "Burn.on_reveal requires a trigger ('single' or 'twin'): ONREVEAL inspects the " +
        "card(s) revealed by the trigger check, so there must be a trigger check to hook into."
      );
    }
    this.n = n;
    this.trigger = trigger;
    this.onReveal = onReveal; // [condition, thenOccurrence] | null
  }

  resolve(gs) {
    if (this.onReveal === null) return gs.resolution(this.n, this.trigger);
    const [condition, then] = this.onReveal;
    const nChecks = TRIGGER_CHECK_COUNT[this.trigger];
    const { bonus, cards } = gs.revealTriggerCards(nChecks);
    for (const card of cards) {
      if (condition.matches(card)) then.resolve(gs);
    }
    return gs.resolutionCore(this.n + bonus);
  }

  maxDamage(ctx) {
    let base = this.n + TRIGGER_DAMAGE_BONUS[this.trigger];
    if (this.onReveal !== null) {
      const nChecks = TRIGGER_CHECK_COUNT[this.trigger];
      const [, then] = this.onReveal;
      base += nChecks * then.maxDamage(ctx);
    }
    return base;
  }
}

class Shuffle extends Effect {
  static JOINT_COST = true;
  constructor(x, then) {
    super();
    if (x < 0) throw new Error(`Shuffle.x must be >= 0, got ${x}`);
    this.x = x;
    this.then = then;
  }

  resolve(_gs) {
    throw new TypeError(
      "Shuffle.resolve() must not be called directly - Occurrence.resolve() dispatches " +
      "JOINT_COST effects to resolveJoint() instead."
    );
  }

  resolveJoint(gs, costAfter) {
    gs.shuffleDiscardIntoMain(this.x);
    if (costAfter) gs.payTrigger(costAfter);
    return this.then.resolve(gs);
  }

  maxDamage(ctx) { return this.then.maxDamage(ctx); }
}

class OnCancel extends Effect {
  constructor(primary, then) {
    super();
    this.primary = primary;
    this.then = then; // array of Occurrence
  }

  resolve(gs) {
    const canceled = this.primary.resolve(gs);
    if (canceled) for (const occ of this.then) occ.resolve(gs);
    return canceled;
  }

  maxDamage(ctx) {
    const xValue = this.primary.maxDamage(ctx);
    const thenValue = this.then.reduce((s, o) => s + o.maxDamage(ctx), 0);
    return Math.max(xValue, thenValue);
  }
}

class Mill extends Effect {
  constructor(n, target, edge, mode, then = null, offset = 0, condition = null) {
    super();
    if (n < 1) throw new Error(`Mill.n must be >= 1, got ${n}`);
    if (!["self", "opp"].includes(target)) throw new Error(`invalid Mill target: ${target} (expected 'self' or 'opp')`);
    if (!["top", "bottom"].includes(edge)) throw new Error(`invalid Mill edge: ${edge} (expected 'top' or 'bottom')`);
    if (!["count", "each", "level", "if"].includes(mode)) throw new Error(`invalid Mill mode: ${mode}`);
    if (["each", "if"].includes(mode) && then === null) throw new Error(`Mill(...)${mode.toUpperCase()}... requires an inner occurrence`);
    if (!["each", "if"].includes(mode) && then !== null) throw new Error(`Mill mode ${mode} does not take an inner occurrence`);
    if (["level", "if"].includes(mode) && n !== 1) {
      throw new Error(
        `Mill(...)${mode.toUpperCase()} is only valid for a single milled card (n=1), got n=${n}. ` +
        `A single-card check (level or condition) has no defined meaning for several cards milled at ` +
        `once - use MILL(${n})...COUNT (climax count) or MILL(${n})...EACH[...] instead if that's what you intended.`
      );
    }
    if (offset !== 0 && mode !== "level") throw new Error("Mill.offset is only meaningful in LEVEL mode");
    if (mode === "if" && condition === null) throw new Error('Mill(...)IF "..." THEN ... requires a condition');
    if (mode !== "if" && condition !== null) throw new Error("Mill.condition is only meaningful in IF mode");

    this.n = n; this.target = target; this.edge = edge; this.mode = mode;
    this.then = then; this.offset = offset; this.condition = condition;
  }

  resolve(gs) {
    const { climaxCount, milled } = gs.mill(this.n, this.target, this.edge);
    if (this.mode === "count") return gs.resolution(climaxCount, null);
    if (this.mode === "level") {
      const card = milled[0];
      return gs.resolution(card.level + this.offset, null);
    }
    if (this.mode === "if") {
      const card = milled[0];
      if (this.condition.matches(card)) return this.then.resolve(gs);
      return false;
    }
    // each
    for (let i = 0; i < climaxCount; i++) this.then.resolve(gs);
    return false;
  }

  maxDamage(ctx) {
    if (this.mode === "count") return this.n;
    if (this.mode === "level") {
      const maxLevel = this.target === "self" ? ctx.maxTriggerLevel : ctx.maxMainLevel;
      return maxLevel + this.offset;
    }
    if (this.mode === "if") return this.then.maxDamage(ctx);
    return this.n * this.then.maxDamage(ctx);
  }
}

class Condition {
  constructor({ colors = null, cardType = "card", levelCmp = null, levelValue = null } = {}) {
    if (levelCmp !== null && !["=", ">=", "<="].includes(levelCmp)) throw new Error(`invalid level comparator: ${levelCmp}`);
    if ((levelCmp === null) !== (levelValue === null)) throw new Error("levelCmp and levelValue must be both set or both null");
    this.colors = colors; // array of uppercase color words | null
    this.cardType = cardType;
    this.levelCmp = levelCmp;
    this.levelValue = levelValue;
  }

  matches(card) {
    if (this.colors !== null && !this.colors.includes(card.color.toUpperCase())) return false;
    if (this.levelCmp !== null) {
      if (this.levelCmp === "=" && card.level !== this.levelValue) return false;
      if (this.levelCmp === ">=" && card.level < this.levelValue) return false;
      if (this.levelCmp === "<=" && card.level > this.levelValue) return false;
    }
    if (this.cardType === "card") return true;
    if (this.cardType === "climax") return card.category === "climax";
    if (this.cardType === "non-climax") return card.category !== "climax";
    return card.category === this.cardType;
  }
}

class TopCheck extends Effect {
  constructor(condition = null, then = null) {
    super();
    if ((condition === null) !== (then === null)) {
      throw new Error("TopCheck: condition and then must be both set (conditional form) or both null (bare peek-level form)");
    }
    this.condition = condition;
    this.then = then;
  }

  resolve(gs) {
    const card = gs.peekTriggerTop();
    if (this.condition === null) return new Occurrence({ effect: new Burn(card.level) }).resolve(gs);
    if (this.condition.matches(card)) return this.then.resolve(gs);
    return false;
  }

  maxDamage(ctx) {
    if (this.condition === null) return ctx.maxTriggerLevel;
    return this.then.maxDamage(ctx);
  }
}

class ZeroDamageEffect extends Effect {
  maxDamage(_ctx) { return 0; }
}

class StockSwap extends ZeroDamageEffect {
  resolve(gs) { gs.stockSwap(); return false; }
}

class StockShuffle extends ZeroDamageEffect {
  resolve(gs) { gs.stockShuffle(); return false; }
}

class ShuffleAll extends ZeroDamageEffect {
  constructor(x) {
    super();
    if (x < 0) throw new Error(`ShuffleAll.x must be >= 0, got ${x}`);
    this.x = x;
  }
  resolve(gs) { gs.shuffleAllButClimaxReserve(this.x); return false; }
}

class Scry extends ZeroDamageEffect {
  constructor(n) {
    super();
    if (n < 1) throw new Error(`Scry.n must be >= 1, got ${n}`);
    this.n = n;
  }
  resolve(gs) { gs.scry(this.n); return false; }
}

// ---------------------------------------------------------------------
// Occurrence
// ---------------------------------------------------------------------

class Occurrence {
  constructor({ effect, cost = 0, postCost = 0, followUp = null }) {
    if (cost < 0 || postCost < 0) throw new Error("cost/postCost must be >= 0");
    if (effect.constructor.JOINT_COST) {
      if (followUp !== null) {
        throw new Error(
          `${effect.constructor.name} does not support a chained follow_up via [next]: its own ` +
          `inner 'then'/'->' occurrence already plays that role.`
        );
      }
    } else if (postCost !== 0) {
      throw new Error(
        `postCost is only meaningful for JOINT_COST effects (Shuffle); ${effect.constructor.name} has ` +
        `none. To express a second, independently-gated cost, chain a follow_up occurrence with its own ` +
        `leading cost instead (e.g. 'BURN(3)[(1)BURN(4)]').`
      );
    }
    this.effect = effect;
    this.cost = cost;
    this.postCost = postCost;
    this.followUp = followUp;
  }

  resolve(gs) {
    if (this.effect.constructor.JOINT_COST) {
      const total = this.cost + this.postCost;
      if (total > 0 && !gs.canPayTrigger(total)) return false;
      if (this.cost) gs.payTrigger(this.cost);
      return this.effect.resolveJoint(gs, this.postCost);
    }

    if (this.cost > 0) {
      if (!gs.canPayTrigger(this.cost)) return false;
      gs.payTrigger(this.cost);
    }

    const canceled = this.effect.resolve(gs);
    if (this.followUp !== null) this.followUp.resolve(gs);
    return canceled;
  }

  maxDamage(ctx) {
    let value = this.effect.maxDamage(ctx);
    if (this.followUp !== null) value += this.followUp.maxDamage(ctx);
    return value;
  }
}

function boundContext(maxTriggerLevel = 0, maxMainLevel = 0) {
  return { maxTriggerLevel, maxMainLevel };
}

function* walkOccurrences(occ, mult = 1) {
  yield [occ, mult];
  if (occ.followUp !== null) yield* walkOccurrences(occ.followUp, mult);

  const effect = occ.effect;
  if (effect instanceof OnCancel) {
    yield* walkOccurrences(effect.primary, mult);
    for (const sub of effect.then) yield* walkOccurrences(sub, mult);
  } else if (effect instanceof Shuffle) {
    yield* walkOccurrences(effect.then, mult);
  } else if (effect instanceof Burn && effect.onReveal !== null) {
    const [, then] = effect.onReveal;
    yield* walkOccurrences(then, mult * TRIGGER_CHECK_COUNT[effect.trigger]);
  } else if (effect instanceof Mill) {
    if (effect.mode === "each") yield* walkOccurrences(effect.then, mult * effect.n);
    else if (effect.mode === "if") yield* walkOccurrences(effect.then, mult);
  } else if (effect instanceof TopCheck) {
    if (effect.then !== null) yield* walkOccurrences(effect.then, mult);
  }
}

function maxPossibleStockGain(occurrences, triggerDeckStockSize = 0) {
  let total = triggerDeckStockSize;
  for (const occ of occurrences) {
    for (const [o, mult] of walkOccurrences(occ)) {
      if (o.effect instanceof Burn) total += mult * TRIGGER_STOCK_BONUS[o.effect.trigger];
    }
  }
  return total;
}

function validateOccurrenceCosts(occurrences, triggerDeckStockSize = 0) {
  const maxStock = maxPossibleStockGain(occurrences, triggerDeckStockSize);
  for (const occ of occurrences) {
    for (const [o] of walkOccurrences(occ)) {
      if (o.effect.constructor.JOINT_COST) {
        const totalCost = o.cost + o.postCost;
        if (totalCost > maxStock) {
          throw new Error(
            `Structurally unpayable cost: ${o.effect.constructor.name} requires cost + postCost = ${totalCost} ` +
            `paid simultaneously (no trigger check happens between the two payments), but at most ${maxStock} ` +
            `cards can theoretically be found in trigger_deck_stock during a trial (trigger_deck_stock_size=` +
            `${triggerDeckStockSize} + trigger checks at best across the whole sequence). This cost can never ` +
            `be paid - check its value or increase trigger_deck_stock_size.`
          );
        }
      } else if (o.cost > maxStock) {
        throw new Error(
          `Structurally unpayable cost: occurrence requires a cost of ${o.cost}, but at most ${maxStock} cards ` +
          `can theoretically be found in trigger_deck_stock during a trial (trigger_deck_stock_size=` +
          `${triggerDeckStockSize} + trigger checks at best across the whole sequence). This cost can never be ` +
          `paid - check its value or increase trigger_deck_stock_size.`
        );
      }
    }
  }
}

function maxPossibleDamage(occurrences, deckSizeList = null, maxTriggerLevel = 0, maxMainLevel = 0) {
  const ctx = boundContext(maxTriggerLevel, maxMainLevel);
  const base = occurrences.reduce((s, occ) => s + occ.maxDamage(ctx), 0);
  if (!deckSizeList || deckSizeList.length === 0) return base;
  const maxRefreshes = Math.ceil(base / Math.min(...deckSizeList));
  return base + maxRefreshes;
}

// ---------------------------------------------------------------------
// Tokenizer / parser
// ---------------------------------------------------------------------

const BRACKET_PAIRS = { ")": "(", "]": "[" };

function checkBalanced(spec) {
  const stack = [];
  for (let i = 0; i < spec.length; i++) {
    const ch = spec[i];
    if (ch === "(" || ch === "[") stack.push([ch, i]);
    else if (ch === ")" || ch === "]") {
      if (stack.length === 0 || stack[stack.length - 1][0] !== BRACKET_PAIRS[ch]) {
        throw new Error(`Unbalanced parenthesis/bracket at position ${i} in ${JSON.stringify(spec)} ('${ch}' with no matching '${BRACKET_PAIRS[ch]}').`);
      }
      stack.pop();
    }
  }
  if (stack.length) {
    const [char, pos] = stack[0];
    throw new Error(`'${char}' opened at position ${pos} is never closed in ${JSON.stringify(spec)}.`);
  }
}

const TOKEN_RE = /(?<STRING>"[^"]*")|(?<NUMBER>\d+)|(?<ARROW>->)|(?<SLASHTRIG>\/[ATat])|(?<IDENT>[A-Za-z]+)|(?<PLUS>\+)|(?<LPAREN>\()|(?<RPAREN>\))|(?<LBRACKET>\[)|(?<RBRACKET>\])|(?<SEMI>;)|(?<WS>\s+)|(?<UNKNOWN>.)/g;

function tokenize(spec) {
  const tokens = [];
  TOKEN_RE.lastIndex = 0;
  let m;
  while ((m = TOKEN_RE.exec(spec)) !== null) {
    const groups = m.groups;
    const kind = Object.keys(groups).find((k) => groups[k] !== undefined);
    if (kind === "WS") continue;
    if (kind === "UNKNOWN") throw new Error(`Unexpected character ${JSON.stringify(m[0])} at position ${m.index} in ${JSON.stringify(spec)}`);
    tokens.push({ kind, value: m[0], pos: m.index });
    if (m[0].length === 0) TOKEN_RE.lastIndex++; // safety against zero-length matches
  }
  return tokens;
}

class Parser {
  constructor(tokens, original) {
    this.tokens = tokens;
    this.i = 0;
    this.original = original;
  }
  peek() { return this.i < this.tokens.length ? this.tokens[this.i] : null; }
  peekIdent() { const t = this.peek(); return t && t.kind === "IDENT" ? t.value.toUpperCase() : null; }
  advance() {
    const t = this.peek();
    if (t === null) throw new Error(`Unexpected end of spec in ${JSON.stringify(this.original)}`);
    this.i++;
    return t;
  }
  expect(kind) {
    const t = this.peek();
    if (t === null || t.kind !== kind) {
      const got = t ? `${t.kind}(${JSON.stringify(t.value)})` : "end of input";
      throw new Error(`Expected ${kind} but got ${got} in ${JSON.stringify(this.original)}`);
    }
    return this.advance();
  }
  expectIdent(...names) {
    const t = this.peek();
    const val = t && t.kind === "IDENT" ? t.value.toUpperCase() : null;
    if (!names.includes(val)) {
      const got = t ? `${t.kind}(${JSON.stringify(t.value)})` : "end of input";
      throw new Error(`Expected one of ${names} but got ${got} in ${JSON.stringify(this.original)}`);
    }
    this.advance();
    return val;
  }
  expectInt() { return parseInt(this.expect("NUMBER").value, 10); }
  atEnd() { return this.i >= this.tokens.length; }

  parseSequence(depth = 0) {
    this.expect("LBRACKET");
    const occs = [this.parseOccurrence(depth + 1)];
    while (this.peek() !== null && this.peek().kind === "SEMI") {
      this.advance();
      occs.push(this.parseOccurrence(depth + 1));
    }
    this.expect("RBRACKET");
    return occs;
  }

  parseOccurrence(depth = 0) {
    const ident = this.peekIdent();
    if (ident === "SHUFFLE") return this.parseShuffle(depth, 0);

    let cost = 0;
    if (this.peek() !== null && this.peek().kind === "LPAREN") {
      this.advance();
      cost = this.expectInt();
      this.expect("RPAREN");
      if (this.peekIdent() === "SHUFFLE") return this.parseShuffle(depth, cost);
    }

    const effect = this.parseEffect(depth);

    let followUp = null;
    if (this.peek() !== null && this.peek().kind === "LBRACKET") {
      this.advance();
      followUp = this.parseOccurrence(depth + 1);
      this.expect("RBRACKET");
    }

    return new Occurrence({ effect, cost, followUp });
  }

  parseShuffle(depth, costBefore) {
    this.expectIdent("SHUFFLE");
    this.expect("LPAREN");
    const x = this.expectInt();
    this.expect("RPAREN");

    let costAfter = 0;
    if (this.peek() !== null && this.peek().kind === "LPAREN") {
      this.advance();
      costAfter = this.expectInt();
      this.expect("RPAREN");
    }

    this.expect("ARROW");
    const then = this.parseOccurrence(depth + 1);

    return new Occurrence({ effect: new Shuffle(x, then), cost: costBefore, postCost: costAfter });
  }

  parseEffect(depth) {
    const ident = this.peekIdent();
    if (ident === "BURN") return this.parseBurn(depth);
    if (ident === "ONCANCEL") return this.parseOnCancel(depth);
    if (ident === "MILL") return this.parseMill(depth);
    if (ident === "TOPCHECK") return this.parseTopCheck(depth);
    if (ident === "STOCKSWAP") { this.advance(); return new StockSwap(); }
    if (ident === "STOCKSHUFFLE") { this.advance(); return new StockShuffle(); }
    if (ident === "SHUFFLEALL") return this.parseShuffleAll();
    if (ident === "SCRY") return this.parseScry();
    const tok = this.peek();
    const got = tok ? `${tok.kind}(${JSON.stringify(tok.value)})` : "end of input";
    throw new Error(`Expected one of BURN/SHUFFLE/ONCANCEL/MILL/TOPCHECK/STOCKSWAP/STOCKSHUFFLE/SHUFFLEALL/SCRY but got ${got} in ${JSON.stringify(this.original)}`);
  }

  parseBurn(depth = 0) {
    this.expectIdent("BURN");
    this.expect("LPAREN");
    const n = this.expectInt();
    this.expect("RPAREN");
    let trigger = null;
    if (this.peek() !== null && this.peek().kind === "SLASHTRIG") {
      const tok = this.advance();
      const suffix = tok.value[1].toUpperCase();
      trigger = suffix === "A" ? "single" : "twin";
    }

    let onReveal = null;
    if (this.peekIdent() === "ONREVEAL") {
      this.advance();
      const raw = this.expect("STRING").value.slice(1, -1);
      const condition = parseCondition(raw);
      this.expectIdent("THEN");
      const then = this.parseOccurrence(depth + 1);
      onReveal = [condition, then];
    }

    return new Burn(n, trigger, onReveal);
  }

  parseShuffleAll() {
    this.expectIdent("SHUFFLEALL");
    this.expect("LPAREN");
    const x = this.expectInt();
    this.expect("RPAREN");
    return new ShuffleAll(x);
  }

  parseScry() {
    this.expectIdent("SCRY");
    this.expect("LPAREN");
    const n = this.expectInt();
    this.expect("RPAREN");
    return new Scry(n);
  }

  parseOnCancel(depth) {
    this.expectIdent("ONCANCEL");
    const then = this.parseSequence(depth);
    this.expectIdent("ON");
    const primary = this.parseOccurrence(depth + 1);
    return new OnCancel(primary, then);
  }

  parseMill(depth) {
    this.expectIdent("MILL");
    this.expect("LPAREN");
    const n = this.expectInt();
    this.expect("RPAREN");
    const targetKw = this.expectIdent("SELF", "OPP");
    const target = targetKw === "SELF" ? "self" : "opp";
    const edge = this.expectIdent("TOP", "BOTTOM").toLowerCase();

    const modeKw = this.expectIdent("COUNT", "EACH", "LEVEL", "IF");
    if (modeKw === "COUNT") return new Mill(n, target, edge, "count");
    if (modeKw === "EACH") {
      this.expect("LBRACKET");
      const then = this.parseOccurrence(depth + 1);
      this.expect("RBRACKET");
      return new Mill(n, target, edge, "each", then);
    }
    if (modeKw === "IF") {
      const raw = this.expect("STRING").value.slice(1, -1);
      const condition = parseCondition(raw);
      this.expectIdent("THEN");
      const then = this.parseOccurrence(depth + 1);
      return new Mill(n, target, edge, "if", then, 0, condition);
    }
    let offset = 0;
    if (this.peek() !== null && this.peek().kind === "PLUS") {
      this.advance();
      offset = this.expectInt();
    }
    return new Mill(n, target, edge, "level", null, offset);
  }

  parseTopCheck(depth) {
    this.expectIdent("TOPCHECK");
    if (this.peek() === null || this.peekIdent() !== "IF") return new TopCheck();
    this.advance();
    const raw = this.expect("STRING").value.slice(1, -1);
    const condition = parseCondition(raw);
    this.expectIdent("THEN");
    const then = this.parseOccurrence(depth + 1);
    return new TopCheck(condition, then);
  }
}

const LEVEL_CLAUSE_RE = /^LEVEL\s*(=|>=|<=)\s*(\d+)\s*/;

function parseCondition(text) {
  let normalized = text.toUpperCase().replace(/-/g, " ").split(/\s+/).filter(Boolean).join(" ");
  if (!normalized) throw new Error("Empty condition string");

  let levelCmp = null;
  let levelValue = null;
  const levelMatch = LEVEL_CLAUSE_RE.exec(normalized);
  if (levelMatch) {
    levelCmp = levelMatch[1];
    levelValue = parseInt(levelMatch[2], 10);
    normalized = normalized.slice(levelMatch[0].length).trim();
  }

  const typeMap = {
    "NON CLIMAX CARD": "non-climax",
    "CLIMAX CARD": "climax",
    "CHARACTER CARD": "character",
    "EVENT CARD": "event",
    "CARD": "card",
  };
  let cardType = null;
  let colorPart = normalized;
  if (normalized) {
    const phrases = Object.keys(typeMap).sort((a, b) => b.length - a.length);
    for (const phrase of phrases) {
      if (normalized.endsWith(phrase)) {
        cardType = typeMap[phrase];
        colorPart = normalized.slice(0, normalized.length - phrase.length).trim();
        break;
      }
    }
  }

  if (cardType === null) {
    if (levelCmp === null) {
      throw new Error(
        `Condition ${JSON.stringify(text)}: no recognized card type suffix (expected one of ` +
        `${JSON.stringify(Object.values(typeMap).sort())}, or a leading LEVEL clause to make it optional)`
      );
    }
    cardType = "card";
  }

  let colors = null;
  if (colorPart) {
    const colorWords = colorPart.split(/\s+/).filter((w) => w !== "OR");
    for (const w of colorWords) {
      if (!COLOR_WORDS.has(w)) throw new Error(`Condition ${JSON.stringify(text)}: unknown color ${JSON.stringify(w)}`);
    }
    colors = colorWords;
  }

  return new Condition({ colors, cardType, levelCmp, levelValue });
}

function parseOccurrence(spec) {
  checkBalanced(spec);
  const tokens = tokenize(spec);
  const parser = new Parser(tokens, spec);
  const occ = parser.parseOccurrence();
  if (!parser.atEnd()) {
    const tok = parser.peek();
    throw new Error(`Invalid occurrence (extra characters after parsing): ${JSON.stringify(spec)} (unexpected ${tok.kind}(${JSON.stringify(tok.value)}) at position ${tok.pos})`);
  }
  return occ;
}

function parseOccurrences(specs) {
  return specs.map((s) => parseOccurrence(String(s)));
}

const _exports = {
  Effect, Burn, Shuffle, OnCancel, Mill, Condition, TopCheck, StockSwap,
  StockShuffle, ShuffleAll, Scry, Occurrence, boundContext, walkOccurrences,
  maxPossibleStockGain, validateOccurrenceCosts, maxPossibleDamage,
  checkBalanced, tokenize, Parser, parseCondition, parseOccurrence, parseOccurrences,
  TRIGGER_CHECK_COUNT,
};
if (typeof module !== "undefined") {
  module.exports = _exports;
} else {
  window.TCG = window.TCG || {};
  Object.assign(window.TCG, _exports);
}

})();
