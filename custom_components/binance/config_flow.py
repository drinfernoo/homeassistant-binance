import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_NAME
import homeassistant.helpers.config_validation as cv
import logging

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'binance1'
CONF_DOMAIN = 'domain'  # It should match with the actual expected configuration key
CONF_API_KEY = 'api_key'
CONF_API_SECRET = 'api_secret'
CONF_NATIVE_CURRENCY = 'native_currency'  # It should match with the actual expected configuration key
CONF_BALANCES = 'balances'
CONF_EXCHANGES = 'exchanges'

class BinanceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_import(self, import_config):
        """Handle a flow import."""

        existing_entry = await self._async_find_existing_entry(import_config)
        if existing_entry:
            # Update the existing entry if an API key match is found
            self.hass.config_entries.async_update_entry(existing_entry, data=import_config)
            return self.async_abort(reason="already_configured")
        
        return self.async_create_entry(title="Binance (imported from YAML)", data=import_config)
    
    async def _async_find_existing_entry(self, import_config):
        """Find an existing config entry."""
        for entry in self._async_current_entries():
            if entry.data[CONF_API_KEY] == import_config[CONF_API_KEY]:
                return entry
        return None
    
    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            # Check if API key and API secret are provided
            if not user_input[CONF_API_KEY] or not user_input[CONF_API_SECRET]:
                errors["base"] = "auth"

            if not errors:
                # Create a new entry with the provided user input
                return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        # Show the form to the user
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_DOMAIN): str,
                vol.Required(CONF_NATIVE_CURRENCY): str,
                vol.Required(CONF_API_KEY): str,
                vol.Required(CONF_API_SECRET): str,
                vol.Optional(CONF_BALANCES, default=[]): vol.All(cv.ensure_list, [str]),
                vol.Optional(CONF_EXCHANGES, default=[]): vol.All(cv.ensure_list, [str]),
            }),
            errors=errors,
        )
