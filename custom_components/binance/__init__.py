import voluptuous as vol
from homeassistant.const import CONF_API_KEY, CONF_NAME
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.core import HomeAssistant
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException
import logging
from datetime import timedelta
from homeassistant import config_entries

_LOGGER = logging.getLogger(__name__)
DOMAIN = "binance1"
DATA_BINANCE = "binance_cache"
DEFAULT_NAME = "Binance"
DEFAULT_DOMAIN = "com"
DEFAULT_CURRENCY = "USD"
CONF_API_SECRET = "api_secret"
CONF_BALANCES = "balances"
CONF_EXCHANGES = "exchanges"
CONF_DOMAIN = "domain"
CONF_NATIVE_CURRENCY = "native_currency"
SCAN_INTERVAL = timedelta(minutes=1)

# Simplified configuration schema
CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.All(cv.ensure_list, [vol.Schema({
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_DOMAIN, default=DEFAULT_DOMAIN): cv.string,
        vol.Optional(CONF_NATIVE_CURRENCY, default=DEFAULT_CURRENCY): cv.string,
        vol.Required(CONF_API_KEY): cv.string,
        vol.Required(CONF_API_SECRET): cv.string,
        vol.Optional(CONF_BALANCES, default=[]): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(CONF_EXCHANGES, default=[]): vol.All(cv.ensure_list, [cv.string]),
    })])
}, extra=vol.ALLOW_EXTRA)

async def async_setup(hass, config):
    """Set up the Binance component from configuration.yaml."""
    hass.data.setdefault(DOMAIN, {})

    # Traiter les configurations du configuration.yaml
    if DOMAIN in config:
        for instance_config in config[DOMAIN]:
            hass.async_create_task(
                hass.config_entries.flow.async_init(
                    DOMAIN, context={'source': config_entries.SOURCE_IMPORT}, data=instance_config
                )
            )

    return True


async def async_setup_entry(hass, entry):
    """Set up Binance from a config entry."""
    coordinator = BinanceCoordinator(hass, entry.data)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    hass.async_create_task(
        async_load_platform(hass, 'sensor', DOMAIN, {'entry_id': entry.entry_id}, entry.data)
    )

    return True

async def async_unload_entry(hass, entry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ['sensor'])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class BinanceCoordinator(DataUpdateCoordinator):
    """Class to manage Binance data updates."""

    def __init__(self, hass: HomeAssistant, config):
        """Initialize the coordinator."""
        self.api_key = config[CONF_API_KEY]
        self.api_secret = config[CONF_API_SECRET]
        self.tld = config.get(CONF_DOMAIN, DEFAULT_DOMAIN)
        self.client = None
        self.balances = []
        self.tickers = {}
        self.native_currency = config.get(CONF_NATIVE_CURRENCY, DEFAULT_CURRENCY)
        _LOGGER.warning("__init__ ")

        super().__init__(
            hass,
            _LOGGER,
            name="Binance Coordinator",
            update_interval=SCAN_INTERVAL,
        )

    async def init_client(self):
        """Initialize Binance client."""
        _LOGGER.warning("init_client ")
        try:
            self.client = await self.hass.async_add_executor_job(
                lambda: Client(self.api_key, self.api_secret, tld=self.tld))
            _LOGGER.warning("[BINANCE] Binance client successfully initialize")
        except Exception as e:
            _LOGGER.error(f"Error initializing Binance client: {e}")
            self.client = None

    async def update_balances(self):
        """Update balance data."""
        _LOGGER.warning("update_balances ")
        if not self.client:
            _LOGGER.warning("Binance client is not initialized")
            return
        try:
            account_info = await self.hass.async_add_executor_job(self.client.get_account)
            self.balances = account_info.get("balances", [])
            _LOGGER.warning(f"Balances updated: {self.balances}")
        except Exception as e:
            _LOGGER.exception(f"Error updating balances: {e}")

    async def update_tickers(self):
        """Update ticker data."""
        if not self.client:
            _LOGGER.warning("Binance client is not initialized")
            return
        try:
            prices =  await self.hass.async_add_executor_job(self.client.get_all_tickers)
            self.tickers = prices
            _LOGGER.warning(f"Tickers updated: {self.tickers}")
        except Exception as e:
            _LOGGER.exception(f"Error updating tickers: {e}")

    async def _async_update_data(self):
        """Update data from Binance API."""
        if not self.client:
            await self.init_client()

        await self.update_balances()
        await self.update_tickers()
        return {"balances": self.balances, "tickers": self.tickers}

    async def async_config_entry_first_refresh(self):
        """Initial data fetch from Binance API."""
        await self.async_refresh()

