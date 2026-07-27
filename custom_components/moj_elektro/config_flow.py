"""Config flow for the Moj Elektro integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MojElektroApiClient, MojElektroApiError, MojElektroAuthError
from .const import (
    ALL_FEATURES,
    CONF_FEATURES,
    CONF_METER_ID,
    CONF_SCAN_INTERVAL_HOURS,
    CONF_TOKEN,
    DEFAULT_SCAN_INTERVAL_HOURS,
    DOMAIN,
    FEATURE_BLOCKS,
    FEATURE_EXPORT,
    FEATURE_HELPERS,
    FEATURE_INTERVALS,
    FEATURE_TARIFF_SPLIT,
    MAX_SCAN_INTERVAL_HOURS,
    MIN_SCAN_INTERVAL_HOURS,
)

_LOGGER = logging.getLogger(__name__)

# The user's own key for the metering-location id entered in step one.
CONF_LOCATION_ID = "location_id"

_FEATURE_LABELS = {
    FEATURE_EXPORT: "Solar export (A-)",
    FEATURE_TARIFF_SPLIT: "Peak/off-peak split (VT/MT)",
    FEATURE_BLOCKS: "5 time-blocks (blok 1-5)",
    FEATURE_INTERVALS: "15-minute interval detail",
    FEATURE_HELPERS: "Helper sensors (current block, agreed/peak power)",
}
_FEATURE_OPTIONS = [
    selector.SelectOptionDict(value=key, label=label)
    for key, label in _FEATURE_LABELS.items()
]


def _options_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Build the options schema (scan interval + feature groups)."""
    return vol.Schema(
        {
            vol.Required(
                CONF_SCAN_INTERVAL_HOURS,
                default=defaults.get(
                    CONF_SCAN_INTERVAL_HOURS, DEFAULT_SCAN_INTERVAL_HOURS
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=MIN_SCAN_INTERVAL_HOURS,
                    max=MAX_SCAN_INTERVAL_HOURS,
                    step=1,
                    unit_of_measurement="hours",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_FEATURES,
                default=defaults.get(CONF_FEATURES, ALL_FEATURES),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=_FEATURE_OPTIONS,
                    multiple=True,
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
        }
    )


class MojElektroConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the Moj Elektro config flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialise transient state carried between steps."""
        self._token: str | None = None
        self._location_id: str | None = None
        self._points: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step one: collect the API token and metering-location id."""
        errors: dict[str, str] = {}

        if user_input is not None:
            token = user_input[CONF_TOKEN].strip()
            location_id = user_input[CONF_LOCATION_ID].strip()
            session = async_get_clientsession(self.hass)
            client = MojElektroApiClient(session, token)
            try:
                self._points = await client.async_get_metering_points(location_id)
            except MojElektroAuthError:
                errors["base"] = "invalid_auth"
            except MojElektroApiError:
                errors["base"] = "cannot_connect"
            else:
                self._token = token
                self._location_id = location_id
                return await self.async_step_meter()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TOKEN): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD
                        )
                    ),
                    vol.Required(CONF_LOCATION_ID): str,
                }
            ),
            errors=errors,
        )

    async def async_step_meter(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step two: pick which metering point (usage point) to read."""
        if user_input is not None:
            usage_point = user_input[CONF_METER_ID]
            await self.async_set_unique_id(usage_point)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"Moj Elektro {usage_point}",
                data={CONF_TOKEN: self._token, CONF_METER_ID: usage_point},
                options={
                    CONF_SCAN_INTERVAL_HOURS: DEFAULT_SCAN_INTERVAL_HOURS,
                    CONF_FEATURES: ALL_FEATURES,
                },
            )

        return self.async_show_form(
            step_id="meter",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_METER_ID, default=self._location_id
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=self._point_options(),
                            mode=selector.SelectSelectorMode.LIST,
                        )
                    )
                }
            ),
        )

    def _point_options(self) -> list[selector.SelectOptionDict]:
        """Build selector options: the whole location plus each metering point."""
        options = [
            selector.SelectOptionDict(
                value=str(self._location_id),
                label=f"Whole location ({self._location_id})",
            )
        ]
        for point in self._points:
            gsrn = point.get("gsrn")
            if not gsrn:
                continue
            vrsta = point.get("vrsta") or "point"
            options.append(
                selector.SelectOptionDict(value=str(gsrn), label=f"{vrsta} — {gsrn}")
            )
        return options

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> MojElektroOptionsFlow:
        """Return the options flow handler."""
        return MojElektroOptionsFlow()


class MojElektroOptionsFlow(OptionsFlow):
    """Handle Moj Elektro options (refresh interval + enabled features)."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(
                data={
                    CONF_SCAN_INTERVAL_HOURS: int(
                        user_input[CONF_SCAN_INTERVAL_HOURS]
                    ),
                    CONF_FEATURES: user_input[CONF_FEATURES],
                }
            )

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(dict(self.config_entry.options)),
        )
