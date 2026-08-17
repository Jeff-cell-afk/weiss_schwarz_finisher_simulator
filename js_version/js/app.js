// app.js — wires the whole UI together. Vanilla JS, no build step:
// re-renders a section's DOM from `state` on every change (inputs use the
// 'change' event, not 'input', so focus isn't yanked away mid-typing).

(function () {
  const {
    makeCard, COLORS,
    buildPools: _unused1,
  } = window.TCG;
  const { generateTable } = window.TCG;
  const { defaultNode, nodeToString, EFFECT_LABELS, CARD_TYPE_LABELS } = window.TCG;
  const { parseOccurrence } = window.TCG;

  const COLOR_LABELS = { yellow: "Yellow", green: "Green", red: "Red", blue: "Blue", purple: "Purple" };
  const CARD_TYPE_ORDER = ["card", "climax", "non-climax", "character", "event"];

  let uid = 0;
  const nid = () => `r${++uid}`;

  // -----------------------------------------------------------------
  // Default state — Geoffroy's own example deck from main.py, scaled
  // down to a trial count that stays snappy in a single-threaded tab.
  // -----------------------------------------------------------------
  function poolRow(level, nTriggers, category, color, count) {
    return { id: nid(), level, nTriggers, category, color, count };
  }

  const state = {
    shareTriggerWithMain: true,
    pools: {
      main: {
        nonClimax: [
          poolRow(0, 0, "character", "yellow", 17),
          poolRow(1, 0, "character", "yellow", 12),
          poolRow(2, 1, "character", "yellow", 3),
          poolRow(3, 0, "character", "yellow", 3),
          poolRow(3, 1, "character", "yellow", 7),
        ],
        climax: [
          poolRow(0, 0, "climax", "yellow", 4),
          poolRow(0, 1, "climax", "yellow", 4),
        ],
      },
      trigger: {
        nonClimax: [poolRow(0, 0, "character", "yellow", 17)],
        climax: [poolRow(0, 0, "climax", "yellow", 4)],
      },
    },
    deck: {
      deckSizeList: "20, 25, 30",
      climaxList: "4, 6, 8",
      triggerDeckSize: 16,
      triggerDeckClimax: 0,
      triggerDeckStockSize: 2,
      mainDeckStockSize: 2,
    },
    occurrences: [
      (() => { const n = defaultNode("BURN"); n.n = 4; return n; })(),
      (() => { const n = defaultNode("BURN"); n.n = 3; n.trigger = "single"; return n; })(),
      (() => { const n = defaultNode("BURN"); n.n = 4; return n; })(),
      (() => { const n = defaultNode("BURN"); n.n = 3; n.trigger = "single"; return n; })(),
      (() => { const n = defaultNode("BURN"); n.n = 4; return n; })(),
      (() => { const n = defaultNode("BURN"); n.n = 3; n.trigger = "single"; return n; })(),
    ],
    sim: { nTrials: 3000, seed: "", checkInvariants: false },
    lastResult: null,
  };

  // -----------------------------------------------------------------
  // DOM helpers
  // -----------------------------------------------------------------
  function el(tag, props = {}, children = []) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(props)) {
      if (v === undefined || v === null) continue;
      if (k === "class") e.className = v;
      else if (k === "text") e.textContent = v;
      else if (k === "html") e.innerHTML = v;
      else if (k.startsWith("on") && typeof v === "function") e.addEventListener(k.slice(2).toLowerCase(), v);
      else e.setAttribute(k, v);
    }
    for (const c of [].concat(children)) {
      if (c === null || c === undefined) continue;
      e.appendChild(typeof c === "string" || typeof c === "number" ? document.createTextNode(String(c)) : c);
    }
    return e;
  }

  function selectEl(options, value, onChange, props = {}) {
    const s = el("select", { ...props, onchange: (e) => onChange(e.target.value) });
    for (const [val, label] of options) {
      const o = el("option", { value: val, text: label });
      if (String(val) === String(value)) o.setAttribute("selected", "selected");
      s.appendChild(o);
    }
    return s;
  }

  function numberInput(value, onChange, props = {}) {
    return el("input", {
      type: "number", value: String(value), ...props,
      onchange: (e) => onChange(e.target.value === "" ? "" : Number(e.target.value)),
    });
  }

  function textInput(value, onChange, props = {}) {
    return el("input", { type: "text", value: String(value), ...props, onchange: (e) => onChange(e.target.value) });
  }

  // -----------------------------------------------------------------
  // Pools section
  // -----------------------------------------------------------------
  function poolTable(rows, { fixedCategory } = {}, onChange) {
    const table = el("table", { class: "pool-table" });
    const head = el("tr", {}, [
      el("th", { text: "Level" }),
      el("th", { text: "Triggers (\u2665)" }),
      ...(fixedCategory ? [] : [el("th", { text: "Type" })]),
      el("th", { text: "Color" }),
      el("th", { text: "Copies" }),
      el("th", { text: "" }),
    ]);
    table.appendChild(el("thead", {}, [head]));
    const body = el("tbody");

    rows.forEach((row, i) => {
      const tr = el("tr", {}, [
        el("td", {}, numberInput(row.level, (v) => { row.level = v; onChange(); }, { min: "0" })),
        el("td", {}, numberInput(row.nTriggers, (v) => { row.nTriggers = v; onChange(); }, { min: "0" })),
        ...(fixedCategory ? [] : [el("td", {}, selectEl(
          [["character", "Character"], ["event", "Event"]], row.category,
          (v) => { row.category = v; onChange(); },
        ))]),
        el("td", {}, selectEl(
          COLORS.map((c) => [c, COLOR_LABELS[c]]), row.color, (v) => { row.color = v; onChange(); },
        )),
        el("td", {}, numberInput(row.count, (v) => { row.count = v; onChange(); }, { min: "1" })),
        el("td", {}, el("button", {
          class: "btn-icon", text: "\u2715", title: "Remove this card",
          onclick: () => { rows.splice(i, 1); onChange(); },
        })),
      ]);
      body.appendChild(tr);
    });
    table.appendChild(body);

    const wrap = el("div", { class: "pool-table-wrap" }, [table]);
    wrap.appendChild(el("button", {
      class: "btn-secondary", text: "+ Add a card",
      onclick: () => {
        rows.push(fixedCategory
          ? poolRow(0, 0, "climax", "yellow", 1)
          : poolRow(0, 0, "character", "yellow", 1));
        onChange();
      },
    }));
    return wrap;
  }

  function renderPools() {
    const container = document.getElementById("pools-section");
    container.innerHTML = "";

    container.appendChild(el("p", {
      class: "section-help",
      text: "Describe the cards available to build random decks: how many copies of each card (level, number of triggers, color) exist in your pool.",
    }));

    container.appendChild(el("h3", { text: "Main deck \u2014 non-climax cards" }));
    container.appendChild(poolTable(state.pools.main.nonClimax, {}, renderPools));

    container.appendChild(el("h3", { text: "Main deck \u2014 climax cards" }));
    container.appendChild(poolTable(state.pools.main.climax, { fixedCategory: "climax" }, renderPools));

    const shareLabel = el("label", { class: "checkbox-label" }, [
      el("input", {
        type: "checkbox", ...(state.shareTriggerWithMain ? { checked: "checked" } : {}),
        onchange: (e) => { state.shareTriggerWithMain = e.target.checked; renderPools(); },
      }),
      " Use the same card pool for the trigger deck",
    ]);
    container.appendChild(shareLabel);

    if (!state.shareTriggerWithMain) {
      container.appendChild(el("h3", { text: "Trigger deck \u2014 non-climax cards" }));
      container.appendChild(poolTable(state.pools.trigger.nonClimax, {}, renderPools));
      container.appendChild(el("h3", { text: "Trigger deck \u2014 climax cards" }));
      container.appendChild(poolTable(state.pools.trigger.climax, { fixedCategory: "climax" }, renderPools));
    }
  }

  // -----------------------------------------------------------------
  // Deck configuration section
  // -----------------------------------------------------------------
  function renderDeckConfig() {
    const container = document.getElementById("deck-config-section");
    container.innerHTML = "";
    const d = state.deck;

    const field = (labelText, inputEl, help) => el("div", { class: "field" }, [
      el("label", { text: labelText }), inputEl,
      help ? el("div", { class: "field-help", text: help }) : null,
    ]);

    container.appendChild(el("div", { class: "field-grid" }, [
      field("Deck sizes tested", textInput(d.deckSizeList, (v) => { d.deckSizeList = v; }),
        "Comma-separated list, e.g. 20, 25, 30"),
      field("Climax counts tested", textInput(d.climaxList, (v) => { d.climaxList = v; }),
        "Comma-separated list, e.g. 4, 6, 8"),
      field("Trigger deck size", numberInput(d.triggerDeckSize, (v) => { d.triggerDeckSize = v; }, { min: "1" })),
      field("Climax in the trigger deck", numberInput(d.triggerDeckClimax, (v) => { d.triggerDeckClimax = v; }, { min: "0" })),
      field("Trigger deck stock", numberInput(d.triggerDeckStockSize, (v) => { d.triggerDeckStockSize = v; }, { min: "0" }),
        "Trigger cards already held in reserve at the start (to pay costs)"),
      field("Main deck stock", numberInput(d.mainDeckStockSize, (v) => { d.mainDeckStockSize = v; }, { min: "0" }),
        "Main deck cards already held in reserve at the start"),
    ]));
  }

  // -----------------------------------------------------------------
  // Condition editor (used by MILL...IF, TOPCHECK...IF, BURN ONREVEAL)
  // -----------------------------------------------------------------
  function conditionEditor(cond, onChange) {
    const wrap = el("div", { class: "condition-editor" });
    const cmpRow = el("div", { class: "inline-fields" }, [
      selectEl(
        [["", "No level condition"], ["=", "Level ="], [">=", "Level \u2265"], ["<=", "Level \u2264"]],
        cond.levelCmp || "",
        (v) => { cond.levelCmp = v || null; if (v && cond.levelValue == null) cond.levelValue = 0; onChange(); },
      ),
      cond.levelCmp ? numberInput(cond.levelValue ?? 0, (v) => { cond.levelValue = v; onChange(); }, { min: "0", style: "width:4.5em" }) : null,
    ]);
    wrap.appendChild(cmpRow);

    wrap.appendChild(selectEl(
      CARD_TYPE_ORDER.map((t) => [t, CARD_TYPE_LABELS[t]]), cond.cardType,
      (v) => { cond.cardType = v; onChange(); },
    ));

    const colorsRow = el("div", { class: "inline-fields color-checks" });
    for (const c of COLORS) {
      const upper = c.toUpperCase();
      const checked = cond.colors.includes(upper);
      colorsRow.appendChild(el("label", { class: "checkbox-chip" }, [
        el("input", {
          type: "checkbox", ...(checked ? { checked: "checked" } : {}),
          onchange: (e) => {
            if (e.target.checked) cond.colors.push(upper);
            else cond.colors = cond.colors.filter((x) => x !== upper);
            onChange();
          },
        }),
        COLOR_LABELS[c],
      ]));
    }
    wrap.appendChild(el("div", { class: "field-help", text: "Colors (none checked = all colors):" }));
    wrap.appendChild(colorsRow);
    return wrap;
  }

  // -----------------------------------------------------------------
  // Recursive occurrence (mechanic) editor
  // -----------------------------------------------------------------
  function occurrenceEditor(node, onChange, depth) {
    const box = el("div", { class: `occ-node occ-${node.effectType.toLowerCase()}`, style: `margin-left:${depth * 18}px` });

    const headerRow = el("div", { class: "occ-header" }, [
      numberInput(node.cost, (v) => { node.cost = v; onChange(); }, { min: "0", class: "cost-input", title: "Cost in trigger stock cards" }),
      selectEl(
        Object.keys(EFFECT_LABELS).map((k) => [k, EFFECT_LABELS[k]]), node.effectType,
        (v) => { Object.assign(node, defaultNode(v)); node.id = node.id; onChange(); },
      ),
    ]);
    box.appendChild(headerRow);

    const body = el("div", { class: "occ-body" });
    box.appendChild(body);

    switch (node.effectType) {
      case "BURN": {
        body.appendChild(el("div", { class: "inline-fields" }, [
          el("label", { text: "Damage (n):" }), numberInput(node.n, (v) => { node.n = v; onChange(); }, { min: "0" }),
          el("label", { text: "Trigger check:" }), selectEl(
            [["", "None"], ["single", "Single check"], ["twin", "Twin drive"]], node.trigger || "",
            (v) => { node.trigger = v || null; if (!v) node.onReveal = null; onChange(); },
          ),
        ]));
        if (node.trigger) {
          const hasReveal = !!node.onReveal;
          body.appendChild(el("label", { class: "checkbox-label" }, [
            el("input", {
              type: "checkbox", ...(hasReveal ? { checked: "checked" } : {}),
              onchange: (e) => {
                node.onReveal = e.target.checked
                  ? { condition: { levelCmp: null, levelValue: null, cardType: "climax", colors: [] }, then: defaultNode("BURN") }
                  : null;
                onChange();
              },
            }),
            " ONREVEAL \u2014 trigger an additional effect if the revealed card matches a condition",
          ]));
          if (node.onReveal) {
            body.appendChild(el("div", { class: "nested-block" }, [
              el("div", { class: "nested-label", text: "Condition on the revealed card:" }),
              conditionEditor(node.onReveal.condition, onChange),
              el("div", { class: "nested-label", text: "Triggered effect:" }),
              occurrenceEditor(node.onReveal.then, onChange, depth + 1),
            ]));
          }
        }
        break;
      }
      case "MILL": {
        body.appendChild(el("div", { class: "inline-fields" }, [
          el("label", { text: "Number of cards (n):" }), numberInput(node.n, (v) => { node.n = v; onChange(); }, { min: "1" }),
          selectEl([["self", "My trigger deck"], ["opp", "Opponent's main deck"]], node.target, (v) => { node.target = v; onChange(); }),
          selectEl([["top", "From the top"], ["bottom", "From the bottom"]], node.edge, (v) => { node.edge = v; onChange(); }),
        ]));
        body.appendChild(el("div", { class: "inline-fields" }, [
          el("label", { text: "Effect:" }),
          selectEl(
            [["count", "Deals damage equal to climax cards discarded"],
             ["each", "Triggers an effect for each climax discarded"],
             ["level", "Deals damage equal to the card's level (1 card)"],
             ["if", "Triggers an effect if the card matches a condition (1 card)"]],
            node.mode,
            (v) => {
              node.mode = v; node.then = null; node.condition = null; node.offset = 0;
              if (["level", "if"].includes(v)) node.n = 1;
              if (v === "each") node.then = defaultNode("BURN");
              if (v === "if") { node.condition = { levelCmp: null, levelValue: null, cardType: "climax", colors: [] }; node.then = defaultNode("BURN"); }
              onChange();
            },
          ),
        ]));
        if (node.mode === "level") {
          body.appendChild(el("div", { class: "inline-fields" }, [
            el("label", { text: "Level bonus/malus:" }), numberInput(node.offset, (v) => { node.offset = v; onChange(); }),
          ]));
        }
        if (node.mode === "each") {
          body.appendChild(el("div", { class: "nested-block" }, [
            el("div", { class: "nested-label", text: "Effect repeated per climax discarded:" }),
            occurrenceEditor(node.then, onChange, depth + 1),
          ]));
        }
        if (node.mode === "if") {
          body.appendChild(el("div", { class: "nested-block" }, [
            el("div", { class: "nested-label", text: "Condition on the discarded card:" }),
            conditionEditor(node.condition, onChange),
            el("div", { class: "nested-label", text: "Effect if the condition is true:" }),
            occurrenceEditor(node.then, onChange, depth + 1),
          ]));
        }
        break;
      }
      case "TOPCHECK": {
        body.appendChild(el("label", { class: "checkbox-label" }, [
          el("input", {
            type: "checkbox", ...(node.conditional ? { checked: "checked" } : {}),
            onchange: (e) => {
              node.conditional = e.target.checked;
              if (node.conditional && !node.condition) {
                node.condition = { levelCmp: null, levelValue: null, cardType: "climax", colors: [] };
                node.then = defaultNode("BURN");
              } else if (!node.conditional) { node.condition = null; node.then = null; }
              onChange();
            },
          }),
          " Conditional effect (otherwise: automatically deals damage equal to the card's level)",
        ]));
        if (node.conditional) {
          body.appendChild(el("div", { class: "nested-block" }, [
            el("div", { class: "nested-label", text: "Condition on the top card:" }),
            conditionEditor(node.condition, onChange),
            el("div", { class: "nested-label", text: "Effect if the condition is true:" }),
            occurrenceEditor(node.then, onChange, depth + 1),
          ]));
        }
        break;
      }
      case "SHUFFLEALL":
        body.appendChild(el("div", { class: "inline-fields" }, [
          el("label", { text: "Climax kept in the discard pile:" }), numberInput(node.x, (v) => { node.x = v; onChange(); }, { min: "0" }),
        ]));
        break;
      case "SCRY":
        body.appendChild(el("div", { class: "inline-fields" }, [
          el("label", { text: "Cards looked at:" }), numberInput(node.n, (v) => { node.n = v; onChange(); }, { min: "1" }),
        ]));
        break;
      case "SHUFFLE":
        body.appendChild(el("div", { class: "inline-fields" }, [
          el("label", { text: "Cards shuffled back (x):" }), numberInput(node.x, (v) => { node.x = v; onChange(); }, { min: "0" }),
          el("label", { text: "Cost after (simultaneous):" }), numberInput(node.costAfter, (v) => { node.costAfter = v; onChange(); }, { min: "0" }),
        ]));
        body.appendChild(el("div", { class: "nested-block" }, [
          el("div", { class: "nested-label", text: "Then:" }),
          occurrenceEditor(node.then, onChange, depth + 1),
        ]));
        break;
      case "ONCANCEL": {
        body.appendChild(el("div", { class: "nested-block" }, [
          el("div", { class: "nested-label", text: "Primary effect (watched for cancellation):" }),
          occurrenceEditor(node.primary, onChange, depth + 1),
        ]));
        const thenWrap = el("div", { class: "nested-block" }, [
          el("div", { class: "nested-label", text: "If canceled, trigger:" }),
        ]);
        node.thenList.forEach((sub, i) => {
          const row = el("div", { class: "oncancel-then-row" }, [
            occurrenceEditor(sub, onChange, depth + 1),
            node.thenList.length > 1 ? el("button", {
              class: "btn-icon", text: "\u2715", title: "Remove this effect",
              onclick: () => { node.thenList.splice(i, 1); onChange(); },
            }) : null,
          ]);
          thenWrap.appendChild(row);
        });
        thenWrap.appendChild(el("button", {
          class: "btn-secondary btn-small", text: "+ Add an effect",
          onclick: () => { node.thenList.push(defaultNode("BURN")); onChange(); },
        }));
        body.appendChild(thenWrap);
        break;
      }
      case "STOCKSWAP":
      case "STOCKSHUFFLE":
        body.appendChild(el("div", { class: "field-help", text: "No parameters." }));
        break;
      default:
        break;
    }

    // follow_up chaining (not available for SHUFFLE: its own `then` plays that role)
    if (node.effectType !== "SHUFFLE") {
      const hasFollowUp = !!node.followUp;
      body.appendChild(el("label", { class: "checkbox-label followup-toggle" }, [
        el("input", {
          type: "checkbox", ...(hasFollowUp ? { checked: "checked" } : {}),
          onchange: (e) => { node.followUp = e.target.checked ? defaultNode("BURN") : null; onChange(); },
        }),
        " Immediately chain another effect after this one",
      ]));
      if (node.followUp) {
        body.appendChild(el("div", { class: "nested-block" }, [
          occurrenceEditor(node.followUp, onChange, depth + 1),
        ]));
      }
    }

    return box;
  }

  function renderOccurrences() {
    const container = document.getElementById("occurrences-section");
    container.innerHTML = "";
    container.appendChild(el("p", {
      class: "section-help",
      text: "Build the sequence of actions played on each simulated trial (e.g. the effects triggered by your characters during a turn). Each block below becomes an 'occurrence' executed in order.",
    }));

    const list = el("div", { class: "occ-list" });
    state.occurrences.forEach((node, i) => {
      const row = el("div", { class: "occ-top-row" }, [
        el("div", { class: "occ-top-index", text: `#${i + 1}` }),
        occurrenceEditor(node, renderOccurrences, 0),
        el("button", {
          class: "btn-icon", text: "\u2715", title: "Remove this action",
          onclick: () => { state.occurrences.splice(i, 1); renderOccurrences(); },
        }),
      ]);
      list.appendChild(row);
    });
    container.appendChild(list);

    container.appendChild(el("button", {
      class: "btn-secondary", text: "+ Add an action",
      onclick: () => { state.occurrences.push(defaultNode("BURN")); renderOccurrences(); },
    }));

    // Live DSL preview, with per-line parse validation.
    const preview = el("div", { class: "dsl-preview" });
    preview.appendChild(el("div", { class: "nested-label", text: "Preview (read-only):" }));
    state.occurrences.forEach((node, i) => {
      let str, error = null;
      try { str = nodeToString(node); parseOccurrence(str); } catch (e) { str = nodeToString(node); error = e.message; }
      preview.appendChild(el("div", { class: error ? "dsl-line dsl-error" : "dsl-line" }, [
        el("code", { text: `${i + 1}. ${str}` }),
        error ? el("div", { class: "dsl-error-msg", text: error }) : null,
      ]));
    });
    container.appendChild(preview);
  }

  // -----------------------------------------------------------------
  // Simulation controls + results
  // -----------------------------------------------------------------
  function parseIntList(text) {
    return text.split(",").map((s) => s.trim()).filter(Boolean).map((s) => {
      const n = parseInt(s, 10);
      if (!Number.isFinite(n)) throw new Error(`Non-numeric value: ${JSON.stringify(s)}`);
      return n;
    });
  }

  function specsFromRows(rows) {
    return rows.map((r) => ({ card: makeCard(Number(r.level), Number(r.nTriggers), r.category, r.color), count: Number(r.count) }));
  }

  function buildConfig() {
    const d = state.deck;
    const deckSizeList = parseIntList(d.deckSizeList);
    const climaxList = parseIntList(d.climaxList);

    const mainNonClimaxSpecs = specsFromRows(state.pools.main.nonClimax);
    const mainClimaxSpecs = specsFromRows(state.pools.main.climax);
    const triggerNonClimaxSpecs = state.shareTriggerWithMain ? mainNonClimaxSpecs : specsFromRows(state.pools.trigger.nonClimax);
    const triggerClimaxSpecs = state.shareTriggerWithMain ? mainClimaxSpecs : specsFromRows(state.pools.trigger.climax);

    const occurrences = state.occurrences.map(nodeToString);

    const seed = state.sim.seed === "" || state.sim.seed === null ? undefined : Number(state.sim.seed);

    return {
      deckSizeList, climaxList, occurrences,
      nTrials: Number(state.sim.nTrials),
      mainNonClimaxSpecs, mainClimaxSpecs, triggerNonClimaxSpecs, triggerClimaxSpecs,
      triggerDeckSize: Number(d.triggerDeckSize),
      triggerDeckClimax: Number(d.triggerDeckClimax),
      triggerDeckStockSize: Number(d.triggerDeckStockSize),
      mainDeckStockSize: Number(d.mainDeckStockSize),
      checkInvariants: state.sim.checkInvariants,
      seed,
    };
  }

  function probColor(p) {
    const lightness = 88 - p * 55;
    const alpha = 0.15 + p * 0.55;
    return `hsla(151, 55%, ${lightness}%, ${alpha})`;
  }

  function sparkline(probs) {
    const w = 140, h = 30, pad = 2;
    const max = Math.max(1, ...probs);
    const step = (w - 2 * pad) / Math.max(1, probs.length - 1);
    const pts = probs.map((p, i) => `${(pad + i * step).toFixed(1)},${(h - pad - (p / max) * (h - 2 * pad)).toFixed(1)}`).join(" ");
    return `<svg viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" class="sparkline"><polyline points="${pts}" fill="none" stroke="var(--accent)" stroke-width="1.6"/></svg>`;
  }

  function renderResults(result, statusText) {
    const container = document.getElementById("results-section");
    container.innerHTML = "";
    if (statusText) container.appendChild(el("p", { class: "status-text", text: statusText }));
    if (!result) return;

    const { columns, rows, thresholds } = result;
    const table = el("table", { class: "results-table" });
    const head = el("tr", {}, [
      el("th", { text: "Deck" }), el("th", { text: "Climax" }),
      ...thresholds.map((t) => el("th", { text: `\u2265${t}` })),
      el("th", { text: "Curve" }),
    ]);
    table.appendChild(el("thead", {}, [head]));
    const body = el("tbody");
    rows.forEach((row) => {
      const tr = el("tr", {}, [
        el("td", { text: String(row.main_deck_size) }),
        el("td", { text: String(row.climax_number) }),
        ...row.probs.map((p) => el("td", { text: p.toFixed(4), style: `background:${probColor(p)}` })),
        el("td", { html: sparkline(row.probs) }),
      ]);
      body.appendChild(tr);
    });
    table.appendChild(body);
    container.appendChild(el("div", { class: "results-table-wrap" }, [table]));

    container.appendChild(el("button", {
      class: "btn-secondary", text: "Download as CSV",
      onclick: () => downloadCsv(columns, rows),
    }));
  }

  function downloadCsv(columns, rows) {
    const header = ["main_deck_size", "climax_number", ...columns].join(",");
    const lines = rows.map((r) => [r.main_deck_size, r.climax_number, ...r.probs].join(","));
    const csv = [header, ...lines].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const a = el("a", { href: URL.createObjectURL(blob), download: "simulation_results.csv" });
    document.body.appendChild(a);
    a.click();
    a.remove();
  }

  function renderSim() {
    const container = document.getElementById("sim-section");
    container.innerHTML = "";
    const s = state.sim;

    container.appendChild(el("div", { class: "field-grid" }, [
      el("div", { class: "field" }, [
        el("label", { text: "Number of trials per combination" }),
        numberInput(s.nTrials, (v) => { s.nTrials = v; }, { min: "100", step: "100" }),
        el("div", { class: "field-help", text: "Runs entirely in your browser (single-threaded): keep it reasonable (a few thousand) for a first try." }),
      ]),
      el("div", { class: "field" }, [
        el("label", { text: "Random seed (optional)" }),
        textInput(s.seed, (v) => { s.seed = v; }, { placeholder: "leave empty = random" }),
      ]),
      el("div", { class: "field" }, [
        el("label", { class: "checkbox-label" }, [
          el("input", {
            type: "checkbox", ...(s.checkInvariants ? { checked: "checked" } : {}),
            onchange: (e) => { s.checkInvariants = e.target.checked; },
          }),
          " Verify card conservation on every trial (slower, useful for debugging)",
        ]),
      ]),
    ]));

    const runBtn = el("button", { class: "btn-primary", text: "Run simulation" });
    runBtn.addEventListener("click", () => runSimulation(runBtn));
    container.appendChild(runBtn);
  }

  async function runSimulation(runBtn) {
    renderResults(null, null);
    let config;
    try {
      config = buildConfig();
    } catch (e) {
      renderResults(null, `Configuration error: ${e.message}`);
      return;
    }

    runBtn.disabled = true;
    runBtn.textContent = "Running simulation\u2026";
    const start = performance.now();

    try {
      const result = await generateTable(config, (p) => {
        const pct = Math.round((p.trialsDone / p.trialsTotal) * 100);
        renderResults(null, `Combination ${p.combinationIndex + 1}/${p.totalCombinations} ` +
          `(deck=${p.size}, climax=${p.climaxN}) \u2014 ${pct}%`);
      });
      const elapsed = ((performance.now() - start) / 1000).toFixed(1);
      state.lastResult = result;
      renderResults(result, `Done in ${elapsed}s \u2014 ${result.rows.length} combination(s), ` +
        `${config.nTrials} trials each.`);
    } catch (e) {
      renderResults(null, `Error: ${e.message}`);
    } finally {
      runBtn.disabled = false;
      runBtn.textContent = "Run simulation";
    }
  }

  // -----------------------------------------------------------------
  function renderAll() {
    renderPools();
    renderDeckConfig();
    renderOccurrences();
    renderSim();
    renderResults(state.lastResult, null);
  }

  document.addEventListener("DOMContentLoaded", renderAll);
})();
