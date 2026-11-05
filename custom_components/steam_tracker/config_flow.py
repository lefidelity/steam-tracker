"""Config flow for the Steam Tracker integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY, CONF_NAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .api import (
    SteamAccountNotFound,
    SteamAuthError,
    SteamConnectionError,
    SteamResponseError,
    fetch_player_summary,
)
from .const import CONF_STEAM_ID, DEFAULT_NAME, DOMAIN


KEY_SELECTOR = selector.TextSelector(
    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
)
DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_STEAM_ID): str,
        vol.Required(CONF_API_KEY): KEY_SELECTOR,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
    }
)
KEY_SCHEMA = vol.Schema({vol.Required(CONF_API_KEY): KEY_SELECTOR})


class SteamTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow to create a Steam Tracker entry."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            data = self._sanitize_user_input(user_input)

            errors = await self._async_validate(data, check_unique_id=True)
            if not errors:
                return self.async_create_entry(title=data[CONF_NAME], data=data)

            user_input = {key: value for key, value in data.items() if key != CONF_API_KEY}
        else:
            user_input = {}

        schema = self.add_suggested_values_to_schema(DATA_SCHEMA, user_input)
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_import(self, user_input: dict[str, str]) -> FlowResult:
        """Handle YAML import by creating a config entry."""
        data = self._sanitize_user_input(user_input)
        if not data[CONF_STEAM_ID] or not data[CONF_API_KEY]:
            return self.async_abort(reason="missing_import_data")
        errors = await self._async_validate(data, check_unique_id=True)
        if errors:
            return self.async_abort(reason=next(iter(errors.values())))
        return self.async_create_entry(title=data[CONF_NAME], data=data)

    async def async_step_reconfigure(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Change the API key of an existing account."""
        return await self._async_key_step(
            "reconfigure", self._get_reconfigure_entry(), user_input
        )

    async def async_step_reauth(self, entry_data: dict[str, str]) -> FlowResult:
        """Request a working key after Steam denied access."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Validate a replacement key for the same account."""
        return await self._async_key_step(
            "reauth_confirm", self._get_reauth_entry(), user_input
        )

    async def _async_key_step(
        self,
        step_id: str,
        entry: config_entries.ConfigEntry,
        user_input: dict[str, str] | None,
    ) -> FlowResult:
        """Update only a confirmed API key and reload the existing entry."""
        errors: dict[str, str] = {}
        if user_input is not None:
            api_key = str(user_input.get(CONF_API_KEY, "")).strip()
            data = {**entry.data, CONF_API_KEY: api_key}
            errors = await self._async_validate(data)
            if CONF_STEAM_ID in errors:
                errors = {"base": errors[CONF_STEAM_ID]}
            if not errors:
                await self.async_set_unique_id(data[CONF_STEAM_ID])
                self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_API_KEY: api_key}
                )

        return self.async_show_form(
            step_id=step_id,
            data_schema=KEY_SCHEMA,
            errors=errors,
            description_placeholders={CONF_NAME: entry.title},
        )

    async def _async_validate(
        self, data: dict[str, str], *, check_unique_id: bool = False
    ) -> dict[str, str]:
        """Validate input locally, then check Steam access in the executor."""
        steam_id = data.get(CONF_STEAM_ID, "")
        if not steam_id:
            return {CONF_STEAM_ID: "steam_id_required"}
        if (
            not steam_id.isascii()
            or not steam_id.isdecimal()
            or len(steam_id) != 17
            or int(steam_id) == 0
        ):
            return {CONF_STEAM_ID: "invalid_steam_id"}
        if not data.get(CONF_API_KEY):
            return {CONF_API_KEY: "api_key_required"}
        if check_unique_id:
            await self.async_set_unique_id(steam_id)
            self._abort_if_unique_id_configured()
        try:
            await self.hass.async_add_executor_job(
                fetch_player_summary, data[CONF_API_KEY], steam_id
            )
        except SteamAuthError:
            return {CONF_API_KEY: "invalid_auth"}
        except SteamConnectionError:
            return {"base": "cannot_connect"}
        except SteamResponseError:
            return {"base": "invalid_response"}
        except SteamAccountNotFound:
            return {CONF_STEAM_ID: "account_not_found"}
        return {}

    @staticmethod
    def _sanitize_user_input(user_input: dict[str, str]) -> dict[str, str]:
        """Strip whitespace and provide defaults."""
        steam_id = str(user_input.get(CONF_STEAM_ID, "")).strip()
        api_key = str(user_input.get(CONF_API_KEY, "")).strip()
        name = str(user_input.get(CONF_NAME, "")).strip() or DEFAULT_NAME

        return {
            CONF_STEAM_ID: steam_id,
            CONF_API_KEY: api_key,
            CONF_NAME: name,
        }
