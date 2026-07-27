/*
 * Moj Elektro dashboard card.
 *
 * A dependency-free custom Lovelace card that auto-discovers the sensors created
 * by the Moj Elektro integration and renders them grouped. Registered with the
 * frontend by the integration, so it appears in the "Add card" picker as
 * "Moj Elektro" — no manual YAML required.
 *
 * Optional config:
 *   type: custom:mojelektro-card
 *   title: Moj Elektro          # card header (default "Moj Elektro")
 *   prefix: sensor.moj_elektro_ # entity-id prefix to match (default this)
 */

const DEFAULT_PREFIX = "sensor.moj_elektro_";

// Section title -> ordered list of entity-id suffixes to show if present.
const SECTIONS = [
  {
    title: "Consumption",
    rows: [
      ["daily_consumption", "Daily total"],
      ["daily_consumption_peak", "Daily peak (VT)"],
      ["daily_consumption_off_peak", "Daily off-peak (MT)"],
    ],
  },
  {
    title: "Export (solar)",
    rows: [
      ["daily_export", "Daily total"],
      ["daily_export_peak", "Daily peak (VT)"],
      ["daily_export_off_peak", "Daily off-peak (MT)"],
    ],
  },
  {
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
  setConfig(config) {
    this._config = config || {};
    this._prefix = this._config.prefix || DEFAULT_PREFIX;
    this._built = false;
    this._rows = {}; // entity_id -> value <span>
    this.innerHTML = "";
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._built) {
      this._build();
    }
    this._update();
  }

  _present(suffix) {
    const id = this._prefix + suffix;
    return this._hass && this._hass.states[id] ? id : null;
  }

  _build() {
    const card = document.createElement("ha-card");
    card.header = this._config.title || "Moj Elektro";

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
    `;
    card.appendChild(style);

    let anyRow = false;
    for (const section of SECTIONS) {
      const present = section.rows.filter(([suffix]) => this._present(suffix));
      if (present.length === 0) continue;
      anyRow = true;

      const wrap = document.createElement("div");
      wrap.className = "section";
      const h = document.createElement("h3");
      h.textContent = section.title;
      wrap.appendChild(h);

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

        // Clicking a row opens the entity's more-info dialog.
        row.style.cursor = "pointer";
        row.addEventListener("click", () => this._moreInfo(id));

        wrap.appendChild(row);
      }
      card.appendChild(wrap);
    }

    if (!anyRow) {
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
    const ev = new Event("hass-more-info", { bubbles: true, composed: true });
    ev.detail = { entityId };
    this.dispatchEvent(ev);
  }

  getCardSize() {
    return 8;
  }

  static getStubConfig() {
    return { title: "Moj Elektro" };
  }
}

customElements.define("mojelektro-card", MojElektroCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "mojelektro-card",
  name: "Moj Elektro",
  description: "All Moj Elektro sensors (consumption, export, blocks, power).",
  preview: false,
});
