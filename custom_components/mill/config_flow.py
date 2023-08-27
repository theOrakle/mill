from __future__ import annotations

import aiohttp
import voluptuous as vol
from homeassistant import config_entries, core, exceptions
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from .exceptions import ApiException, AuthenticationError
from .const import DOMAIN, URL, _LOGGER

DATA_SCHEMA = vol.Schema(
  {
    vol.Required(CONF_USERNAME): str,
    vol.Required(CONF_PASSWORD): str
  }
)

async def validate_input(hass: core.HomeAssistant, data):
    creds = {
        "email":    data[CONF_USERNAME],
        "password": data[CONF_PASSWORD]
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(URL+"/tokens",data=creds) as r:
                results = await r.json()
    except:
        _LOGGER.error('Troubles talking to the API')
        raise ApiException()
    if r.status == 201:
        return data
    else:
        raise AuthenticationError()

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                return self.async_create_entry(title=user_input[CONF_USERNAME], data=info)
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )   
