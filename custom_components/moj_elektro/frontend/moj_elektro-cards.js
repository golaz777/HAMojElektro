/*
 * Moj Elektro dashboard cards.
 *
 * Dependency-free custom Lovelace cards that auto-discover the sensors created by
 * the Moj Elektro integration. Registered with the frontend by the integration,
 * so they appear in the "Add card" picker — no manual YAML required.
 *
 * Cards (each addable on its own):
 *   custom:moj-elektro-card              — everything (daily graph + all sections)
 *   custom:moj-elektro-daily-card        — daily usage (kWh) bar chart only
 *   custom:moj-elektro-consumption-card  — consumption (total / peak / off-peak)
 *   custom:moj-elektro-export-card       — solar export
 *   custom:moj-elektro-blocks-card       — current block + daily kWh per block
 *   custom:moj-elektro-power-card        — monthly peak + agreed power
 *
 * Optional config (all optional):
 *   title: ...                  # card header
 *   prefix: sensor.moj_elektro_ # entity-id prefix to match (default this)
 *   sections: [consumption, export, blocks, power]  # which groups to show
 *   daily_graph: true|false     # show the daily-usage kWh bar chart
 *   days_to_show: 30            # days in the daily-usage chart (default 30)
 *   statistic: moj_elektro:..._energy_consumption  # override auto-detection
 */

const DEFAULT_PREFIX = "sensor.moj_elektro_";

// Section id -> title + ordered list of [entity-id suffix, label].
const SECTIONS = [
  {
    id: "consumption",
    title: "Consumption",
    rows: [
      ["daily_consumption", "Daily total"],
      ["daily_consumption_peak", "Daily peak (VT)"],
      ["daily_consumption_off_peak", "Daily off-peak (MT)"],
    ],
  },
  {
    id: "export",
    title: "Export (solar)",
    rows: [
      ["daily_export", "Daily total"],
      ["daily_export_peak", "Daily peak (VT)"],
      ["daily_export_off_peak", "Daily off-peak (MT)"],
    ],
  },
  {
    id: "blocks",
    title: "Time blocks (daily)",
    rows: [
      ["current_tariff_block", "Current block (now)"],
      ["daily_consumption_block_1", "Block 1"],
      ["daily_consumption_block_2", "Block 2"],
      ["daily_consumption_block_3", "Block 3"],
      ["daily_consumption_block_4", "Block 4"],
      ["daily_consumption_block_5", "Block 5"],
    ],
  },
  {
    id: "power",
    title: "Power & contract",
    rows: [
      ["monthly_peak_power", "Monthly peak power"],
      ["agreed_power_block_1", "Agreed power — block 1"],
      ["agreed_power_block_2", "Agreed power — block 2"],
      ["agreed_power_block_3", "Agreed power — block 3"],
      ["agreed_power_block_4", "Agreed power — block 4"],
      ["agreed_power_block_5", "Agreed power — block 5"],
    ],
  },
];

class MojElektroCard extends HTMLElement {
  // Subclasses override this to preset a title / sections / daily_graph.
  static get presets() {
    return {};
  }

  setConfig(config) {
    this._config = Object.assign({}, this.constructor.presets, config || {});
    this._prefix = this._config.prefix || DEFAULT_PREFIX;
    this._built = false;
    this._graphBuilt = false;
    this._graphEl = null;
    this._rows = {}; // entity_id -> value <span>
    this.innerHTML = "";
  }

  set hass(hass) {
    this._hass = hass;
    try {
      if (!this._built) {
        this._build();
      }
      this._update();
      if (this._graphEl) {
        this._graphEl.hass = hass;
      }
    } catch (err) {
      // Never surface as a Lovelace error card — degrade quietly.
      console.error("moj-elektro-card render error", err);
    }
  }

  _present(suffix) {
    const id = this._prefix + suffix;
    return this._hass && this._hass.states[id] ? id : null;
  }

  _wantedSections() {
    const wanted = this._config.sections;
    if (!Array.isArray(wanted)) return SECTIONS;
    return SECTIONS.filter((s) => wanted.includes(s.id));
  }

  _showGraph() {
    return this._config.daily_graph !== false;
  }

  _build() {
    const card = document.createElement("ha-card");
    if (this._config.title) card.header = this._config.title;

    const style = document.createElement("style");
    style.textContent = `
      .section { padding: 4px 16px 8px; }
      .section h3 {
        margin: 8px 0 4px; font-size: 0.9em; font-weight: 500;
        color: var(--secondary-text-color);
      }
      .row {
        display: flex; align-items: center; justify-content: space-between;
        padding: 6px 0; border-top: 1px solid var(--divider-color);
      }
      .row:first-of-type { border-top: none; }
      .name { display: flex; align-items: center; gap: 10px; }
      .name ha-icon { color: var(--state-icon-color, var(--paper-item-icon-color)); }
      .value { font-variant-numeric: tabular-nums; white-space: nowrap; }
      .empty { padding: 16px; color: var(--secondary-text-color); }
      .graph { padding: 0 8px; }
    `;
    card.appendChild(style);

    // Slot for the daily-usage statistics graph (filled asynchronously).
    this._graphSlot = document.createElement("div");
    this._graphSlot.className = "graph";
    card.appendChild(this._graphSlot);

    let anyRow = false;
    for (const section of this._wantedSections()) {
      const present = section.rows.filter(([suffix]) => this._present(suffix));
      if (present.length === 0) continue;
      anyRow = true;

      const wrap = document.createElement("div");
      wrap.className = "section";
      // Only label sections when more than one is shown.
      if (this._wantedSections().length > 1) {
        const h = document.createElement("h3");
        h.textContent = section.title;
        wrap.appendChild(h);
      }

      for (const [suffix, label] of present) {
        const id = this._prefix + suffix;
        const st = this._hass.states[id];

        const row = document.createElement("div");
        row.className = "row";

        const name = document.createElement("div");
        name.className = "name";
        const icon = document.createElement("ha-icon");
        icon.icon = (st.attributes && st.attributes.icon) || "mdi:flash";
        name.appendChild(icon);
        const text = document.createElement("span");
        text.textContent = label;
        name.appendChild(text);
        row.appendChild(name);

        const value = document.createElement("span");
        value.className = "value";
        row.appendChild(value);
        this._rows[id] = value;

        row.style.cursor = "pointer";
        row.addEventListener("click", () => this._moreInfo(id));

        wrap.appendChild(row);
      }
      card.appendChild(wrap);
    }

    if (!anyRow && !this._showGraph()) {
      const empty = document.createElement("div");
      empty.className = "empty";
      empty.textContent =
        "No Moj Elektro sensors found yet. Wait for the first refresh, " +
        "or set a `prefix:` in the card config.";
      card.appendChild(empty);
    }

    this.innerHTML = "";
    this.appendChild(card);
    this._built = true;

    if (this._showGraph()) {
      this._buildGraph();
    }
  }

  async _buildGraph() {
    if (this._graphBuilt) return;
    this._graphBuilt = true;

    // Resolve the daily-consumption statistic id (auto-detect unless configured).
    let statId = this._config.statistic;
    if (!statId) {
      try {
        const ids = await this._hass.callWS({
          type: "recorder/list_statistic_ids",
          statistic_type: "sum",
        });
        const match = (ids || []).find(
          (s) =>
            s.statistic_id &&
            s.statistic_id.startsWith("moj_elektro:") &&
            s.statistic_id.endsWith("_energy_consumption")
        );
        statId = match && match.statistic_id;
      } catch (err) {
        // Recorder not available or WS unsupported — skip the graph.
        return;
      }
    }
    if (!statId || !this._graphSlot) return;

    try {
      const helpers = await window.loadCardHelpers();
      const el = helpers.createCardElement({
        type: "statistics-graph",
        title: this._config.title || "Daily usage",
        period: "day",
        chart_type: "bar",
        days_to_show: this._config.days_to_show || 30,
        stat_types: ["change"],
        entities: [statId],
      });
      el.hass = this._hass;
      this._graphEl = el;
      this._graphSlot.appendChild(el);
    } catch (err) {
      // loadCardHelpers unavailable — leave the slot empty.
    }
  }

  _update() {
    for (const [id, span] of Object.entries(this._rows)) {
      const st = this._hass.states[id];
      if (!st) continue;
      const unit = (st.attributes && st.attributes.unit_of_measurement) || "";
      const val = st.state;
      span.textContent = unit ? `${val} ${unit}` : val;
    }
  }

  _moreInfo(entityId) {
    this.dispatchEvent(
      new CustomEvent("hass-more-info", {
        detail: { entityId },
        bubbles: true,
        composed: true,
      })
    );
  }

  getCardSize() {
    const sections = this._wantedSections().length;
    return (this._showGraph() ? 4 : 0) + sections * 3 + 1;
  }
}

// --- Card variants -------------------------------------------------------

class MojElektroDailyCard extends MojElektroCard {
  static get presets() {
    return { title: "Daily usage", sections: [], daily_graph: true };
  }
}
class MojElektroConsumptionCard extends MojElektroCard {
  static get presets() {
    return { title: "Consumption", sections: ["consumption"], daily_graph: false };
  }
}
class MojElektroExportCard extends MojElektroCard {
  static get presets() {
    return { title: "Export (solar)", sections: ["export"], daily_graph: false };
  }
}
class MojElektroBlocksCard extends MojElektroCard {
  static get presets() {
    return { title: "Time blocks", sections: ["blocks"], daily_graph: false };
  }
}
class MojElektroPowerCard extends MojElektroCard {
  static get presets() {
    return { title: "Power & contract", sections: ["power"], daily_graph: false };
  }
}

const CARDS = [
  ["moj-elektro-card", MojElektroCard, "Moj Elektro (all)",
    "Daily graph plus every sensor, grouped."],
  ["moj-elektro-daily-card", MojElektroDailyCard, "Moj Elektro: Daily usage",
    "Daily usage (kWh) bar chart."],
  ["moj-elektro-consumption-card", MojElektroConsumptionCard,
    "Moj Elektro: Consumption", "Daily consumption total / peak / off-peak."],
  ["moj-elektro-export-card", MojElektroExportCard, "Moj Elektro: Export",
    "Daily solar export total / peak / off-peak."],
  ["moj-elektro-blocks-card", MojElektroBlocksCard, "Moj Elektro: Time blocks",
    "Current block and daily kWh per block."],
  ["moj-elektro-power-card", MojElektroPowerCard, "Moj Elektro: Power",
    "Monthly peak and agreed power per block."],
];

window.customCards = window.customCards || [];
for (const [type, cls, name, description] of CARDS) {
  if (!customElements.get(type)) {
    customElements.define(type, cls);
  }
  window.customCards.push({ type, name, description, preview: false });
}
