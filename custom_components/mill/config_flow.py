from __future__ import annotations

import pydash
import aiohttp
import voluptuous as vol
from homeassistant import config_entries, core, exceptions
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, CONF_ACCESS_TOKEN, CONF_CLIENT_ID
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
        auth = {"Authorization": "Bearer " + results.get('token')}
        async with aiohttp.ClientSession() as session:
            async with session.get(URL+"/session_init?refresh_token=true",headers=auth) as r:
                results = await r.json()
                data[CONF_ACCESS_TOKEN] = pydash.get(results,"data.attributes.authToken")
                data[CONF_CLIENT_ID] = pydash.get(results,"data.attributes.userId")
        return data
    else:
        raise AuthenticationError()

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
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
