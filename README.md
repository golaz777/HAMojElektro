# Moj Elektro for Home Assistant

A [HACS](https://hacs.xyz/) custom integration that brings your Slovenian
electricity metering data from [Moj Elektro](https://mojelektro.si) into Home
Assistant, including the **Energy Dashboard**.

The Moj Elektro API publishes consumption once per day with a ~24 hour delay, so
this integration imports **long-term statistics using each reading's real
timestamp** — your usage lands on the correct day in the Energy Dashboard rather
than on the day it happened to be fetched.

## Features

- Config flow (UI): enter your API token, then pick a metering point.
- `sensor.moj_elektro_daily_consumption` — the last completed day's consumption (kWh).
- Energy Dashboard statistic `mojelektro:<meter>_energy_consumption`.

### Optional data (toggle in **Configure**)

All enabled by default; turn off what you don't need (e.g. export if you have no solar):

| Group | Sensors | Statistics |
| --- | --- | --- |
| Solar export (A−) | daily export total/peak/off-peak | `…_daily_export*` → **Return to grid** |
| Peak/off-peak split | daily consumption peak / off-peak | `…_daily_consumption_peak/_offpeak` |
| 5 time-blocks | daily kWh per block (1–5) | `…_blok_1…5` |
| 15-minute detail | — | `…_import_15min`, `…_export_15min` (hourly) |
| Helper sensors | current tariff block, monthly peak power, agreed power per block | — |

**Energy Dashboard mapping:** keep `…_energy_consumption` as your grid **consumption**
source and `…_daily_export` as **return to grid**. Peak/off-peak and per-block statistics
are for their own history/cards — don't add two overlapping totals as consumption. The
15-minute statistics are a finer-resolution alternative to the daily total, not an addition.

## Getting an API token

1. Log in at [mojelektro.si](https://mojelektro.si).
2. Go to **Moj Profil → Kreiraj žeton** (Create token), choose unlimited
   expiration, and create it.
3. Copy the token. You will also need your **metering-location id** (merilno
   mesto) shown in your account.

## Installation (HACS)

1. In HACS → three-dot menu → **Custom repositories**, add
   `https://github.com/golaz777/HAMojElektro` with category **Integration**.
2. Install **Moj Elektro**, then restart Home Assistant.
3. **Settings → Devices & Services → Add Integration → Moj Elektro**, enter the
   token and metering-location id, and pick the metering point.

Updates then arrive through HACS like any other integration.

## Dashboard card

The integration bundles a **Moj Elektro** dashboard card and registers it with the
frontend automatically. Just add it from the UI:

**Dashboard → Edit → ＋ Add card → search "Moj Elektro"**

The card auto-discovers every sensor and groups them (consumption, export, time blocks,
power & contract) — no YAML. If it doesn't show right after updating, hard-refresh the
browser (Ctrl/Cmd-Shift-R) to clear the cached resource.

Optional config (all optional):

```yaml
type: custom:mojelektro-card
title: Moj Elektro
prefix: sensor.moj_elektro_   # change only if HA gave your entities a different prefix
```

A plain built-in-cards version (no custom card) is also available as
[`dashboards/mojelektro_card.yaml`](dashboards/mojelektro_card.yaml) for manual pasting.

## Energy Dashboard

After setup, go to **Settings → Dashboards → Energy → Add consumption** and
select `mojelektro:<meter>_energy_consumption`. Because data is delayed ~24h, the
most recent day fills in the following day.

## Notes / roadmap

Only daily consumption is exposed today. 15-minute intervals, tariff/time-block
breakdown, and energy production (net metering) are possible follow-ups — see
[`frlequ/homeassistant-mojelektro`](https://github.com/frlequ/homeassistant-mojelektro)
for reference implementations.
