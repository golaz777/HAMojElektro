# Changelog

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
