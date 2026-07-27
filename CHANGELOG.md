# Changelog

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
