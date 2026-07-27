# Changelog

## 1.1.1

- Daily usage card: fixed the duplicated "Daily usage" header, and the header's
  chevron now opens the daily-consumption more-info popup instead of navigating away
  to the full History page.
- Long-term statistics are now stored as a from-zero running sum of daily consumption
  instead of the raw meter register, so the bar chart no longer shows a huge false
  spike on the series' first day (the whole meter reading rendered as one day).
  Existing series' historical first-day bar scrolls out of the 30-day window on its
  own; clear + re-import the statistic in Developer Tools for an immediate clean slate.

## 1.1.0

- Split the dashboard card into separate, individually addable cards so you can place
  each block where you want: `moj-elektro-daily-card` (daily usage graph),
  `moj-elektro-consumption-card`, `moj-elektro-export-card`, `moj-elektro-blocks-card`,
  `moj-elektro-power-card`. The combined `moj-elektro-card` still shows everything.
- The combined card also accepts `sections:` and `daily_graph:` to tailor what it shows.

## 1.0.1

- Dashboard card: the registered JS url now carries a `?v=<version>` cache-buster so
  aggressive caches (Fully Kiosk / Android WebView) load the current card after an
  update instead of a stale copy — fixes a red "configuration error" card on kiosk
  tablets after the v1.0.0 rename.
- Fixed the row-tap more-info handler (`CustomEvent`) and made the card degrade
  quietly instead of ever rendering as an error card.

## 1.0.0 — BREAKING: domain renamed

The integration domain changed from `mojelektro` to **`moj_elektro`** so it has its
own brand (the old `mojelektro` domain/brand belongs to `frlequ/homeassistant-mojelektro`).

**You must remove and re-add the integration:**

1. Settings → Devices & Services → Moj Elektro → delete the entry.
2. Update to 1.0.0 in HACS and restart Home Assistant.
3. Add the integration again (token + metering point).
4. Re-select the statistics in the Energy Dashboard — the ids changed from
   `mojelektro:<meter>_…` to `moj_elektro:<meter>_…`, so previous statistics history
   stays under the old ids (removable via Developer Tools → Statistics).

The custom card type is now `custom:moj-elektro-card` (auto-registered as before).

The bundled brand icon/logo now render natively (HA 2026.3+ serves the `brand/` folder
via its local brands proxy — no home-assistant/brands submission needed).

## 0.4.0

- The **Moj Elektro** dashboard card now shows a **daily usage (kWh) bar chart** at
  the top, built from long-term statistics. The consumption statistic is auto-detected
  (override with `statistic:`; adjust range with `days_to_show:`; hide with
  `daily_graph: false`).

## 0.3.1

- Added brand assets (device icon + logo) under `custom_components/mojelektro/brand/`.
  To make them render in the Home Assistant UI they also need submitting to the
  [home-assistant/brands](https://github.com/home-assistant/brands) repository.

## 0.3.0

- Bundled **Moj Elektro dashboard card**: the integration registers a custom
  Lovelace card, so you can add it from **Add card → Moj Elektro** (no YAML
  pasting). It auto-discovers and groups all sensors. May require one browser
  refresh / cache clear after updating.

## 0.2.0

Expanded data (all opt-out-able in the integration's **Configure** dialog):

- **Solar export (A−)** daily sensors + statistics (total/peak/off-peak) → Energy
  Dashboard "return to grid".
- **Peak/off-peak split (VT/MT)** daily import sensors + statistics.
- **5 network time-blocks (blok 1–5)** daily kWh sensors + statistics.
- **15-minute detail**: A+/A− aggregated to hourly-resolution statistics.
- **Helper sensors**: current active tariff block (1–5), monthly peak 15-minute
  power (kW), and agreed/contracted power per block (kW, diagnostic).

The original `daily_consumption` sensor and its `mojelektro:<meter>_energy_consumption`
statistic are unchanged.

## 0.1.1

- Fix `Invalid statistic_id` setup error for metering points whose id contains
  hyphens or uppercase (e.g. `3-8110057`); the external statistic id is now
  slugified to `mojelektro:3_8110057_energy_consumption`.

## 0.1.0

- Initial release.
- Config flow: enter Moj Elektro API token, then pick a metering point from the account.
- Daily consumption sensor (kWh) for the last completed day.
- Energy Dashboard support via imported long-term statistics
  (`mojelektro:<meter>_energy_consumption`) placed on the correct historical days.
