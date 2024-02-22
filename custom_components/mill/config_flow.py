"""Adds config flow for Mill."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, CONF_TOKEN
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import (
    MillApiClient,
    MillApiClientAuthenticationError,
    MillApiClientCommunicationError,
    MillApiClientError,
)
from .const import DOMAIN, LOGGER


class MillFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Mill."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
        if user_input is not None:
            try:
                user_input[CONF_TOKEN] = await self._test_credentials(
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                )
            except MillApiClientAuthenticationError as exception:
                LOGGER.warning(exception)
                _errors["base"] = "auth"
            except MillApiClientCommunicationError as exception:
                LOGGER.error(exception)
                _errors["base"] = "connection"
            except MillApiClientError as exception:
                LOGGER.exception(exception)
                _errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=user_input[CONF_USERNAME],
                    data=user_input,
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
            errors=_errors,
        )

    async def _test_credentials(self, username: str, password: str) -> None:
        """Validate credentials."""
        client = MillApiClient(
            username=username,
            password=password,
            session=async_create_clientsession(self.hass),
            token=None,
        )
        await client.async_get_data()
        return client.token
