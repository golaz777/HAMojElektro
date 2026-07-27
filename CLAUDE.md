# HAMojElektro — developer notes

HACS custom integration (domain `moj_elektro`) for Slovenian Moj Elektro electricity
metering data. Structured after `golaz777/HAMotoGP`.

## Architecture

- `api.py` — thin aiohttp client. Auth via `X-API-TOKEN` header. Endpoints:
  `/merilno-mesto/{id}` (list metering points), `/meter-readings` (daily cumulative
  register, ReadingType `32.0.4.1.1.2.12.0.0.0.0.0.0.0.0.3.72.0`). Prod base only.
- `coordinator.py` — `DataUpdateCoordinator`, polls every `scan_interval_hours`
  (default 12). `_compute_daily` turns cumulative register readings into per-day
  consumption (`value[n] - value[n-1]`, attributed to the earlier day).
- `statistics.py` — pushes external long-term statistics
  (`moj_elektro:<meter>_energy_consumption`) via `async_add_external_statistics`,
  keyed on the reading's real timestamp so Energy Dashboard placement is correct
  despite the ~24h API delay. Every series is a from-zero running `sum` of per-period
  consumption (`async_import_computed`, seeded from `get_last_statistics`); starting at
  zero avoids a false first-day `change` spike. The trailing-window overlap is
  de-duped via the `start <= last_start` guard.
- `config_flow.py` — step 1 token + location id (validates via metering-points call,
  distinguishes `invalid_auth` vs `cannot_connect`); step 2 pick usage point.
- `sensor.py` — one daily-consumption sensor (kWh); the Energy Dashboard uses the
  statistic, not this sensor.

`recorder` is an `after_dependencies` (needed at runtime for statistics; not a hard
dep so the config flow doesn't force recorder setup).

## Testing

`pip install -r requirements-test.txt` then `pytest`. Logic tests
(`test_coordinator.py`, `test_statistics.py`) run without a live API; the config-flow
test mocks the metering-points endpoint. CI (`.github/workflows/validate.yml`) also
runs hassfest + HACS validation on Python 3.13.

## Not yet implemented

15-min intervals, tariff/time-block breakdown, energy production. See
`frlequ/homeassistant-mojelektro` for reference implementations.
