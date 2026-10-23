"""Adds config flow for Mill."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_TOKEN, CONF_USERNAME
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import (
    MillApiClient,
    MillApiClientAuthenticationError,
    MillApiClientCommunicationError,
    MillApiClientError,
)
from .const import DOMAIN, LOGGER


class MillFlowHandler(ConfigFlow, domain=DOMAIN):
    """Config flow for Mill."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        errors: dict[str, str] = {}
        if user_input is not None:
            username = user_input[CONF_USERNAME].strip()
            try:
                token = await self._test_credentials(
                    username=username,
                    password=user_input[CONF_PASSWORD],
                )
            except MillApiClientAuthenticationError as exception:
                LOGGER.warning(exception)
                errors["base"] = "invalid_auth"
            except MillApiClientCommunicationError as exception:
                LOGGER.error(exception)
                errors["base"] = "cannot_connect"
            except MillApiClientError as exception:
                LOGGER.exception(exception)
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(username.lower())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=username,
                    data={
                        CONF_USERNAME: username,
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_TOKEN: token,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USERNAME,
                        default=(user_input or {}).get(CONF_USERNAME),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT
                        ),
                    ),
                    vol.Required(CONF_PASSWORD): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD
                        ),
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start re-authentication after Mill rejected the stored credentials."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the account password again."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()
        if user_input is not None:
            try:
                token = await self._test_credentials(
                    username=reauth_entry.data[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                )
            except MillApiClientAuthenticationError as exception:
                LOGGER.warning(exception)
                errors["base"] = "invalid_auth"
            except MillApiClientCommunicationError as exception:
                LOGGER.error(exception)
                errors["base"] = "cannot_connect"
            except MillApiClientError as exception:
                LOGGER.exception(exception)
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates={
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_TOKEN: token,
                    },
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PASSWORD): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD
                        ),
                    ),
                }
            ),
            description_placeholders={"username": reauth_entry.data[CONF_USERNAME]},
            errors=errors,
        )

    async def _test_credentials(self, username: str, password: str) -> str | None:
        """Validate credentials and return the session token."""
        client = MillApiClient(
            username=username,
            password=password,
            session=async_create_clientsession(self.hass),
            token=None,
        )
        await client.async_get_data()
        return client._token
