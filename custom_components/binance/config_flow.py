import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_NAME
import homeassistant.helpers.config_validation as cv

DOMAIN = 'binance'
CONF_DOMAIN = 'com'
CONF_API_KEY = 'api_key'
CONF_API_SECRET = 'api_secret'
CONF_NATIVE_CURRENCY = 'USD'
CONF_BALANCES = 'balances'
CONF_EXCHANGES = 'exchanges'

class BinanceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

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
