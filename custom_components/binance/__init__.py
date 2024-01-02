import asyncio
import voluptuous as vol
from homeassistant.const import CONF_API_KEY, CONF_NAME, Platform
import homeassistant.helpers.config_validation as cv
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.util import Throttle
from datetime import timedelta
import logging
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

__version__ = "1.0.1"
REQUIREMENTS = ["python-binance==1.0.19"]

_LOGGER = logging.getLogger(__name__)

DOMAIN = "binance"
DATA_BINANCE = "binance_cache"

# Configuration defaults and constants
DEFAULT_NAME = "Binance"
DEFAULT_DOMAIN = "com"
DEFAULT_CURRENCY = "USD"
CONF_API_SECRET = "api_secret"
CONF_BALANCES = "balances"
CONF_EXCHANGES = "exchanges"
CONF_DOMAIN = "domain"
CONF_NATIVE_CURRENCY = "native_currency"
SCAN_INTERVAL = timedelta(seconds=1)
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=1)

# Schema for individual instance configuration
INSTANCE_SCHEMA = vol.Schema({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_DOMAIN, default=DEFAULT_DOMAIN): cv.string,
    vol.Optional(CONF_NATIVE_CURRENCY, default=DEFAULT_CURRENCY): cv.string,
    vol.Required(CONF_API_KEY): cv.string,
    vol.Required(CONF_API_SECRET): cv.string,
    vol.Optional(CONF_BALANCES, default=[]): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_EXCHANGES, default=[]): vol.All(cv.ensure_list, [cv.string]),
})

# Schema for overall configuration
CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.All(cv.ensure_list, [INSTANCE_SCHEMA])
}, extra=vol.ALLOW_EXTRA)

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Binance component from configuration.yaml."""
    _LOGGER.warning("[BINANCE] Starting Binance setup")
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    for instance in config[DOMAIN]:
        api_key = instance[CONF_API_KEY]
        api_secret = instance[CONF_API_SECRET]
        tld = instance.get(CONF_DOMAIN)

        coordinator = BinanceCoordinator(hass, api_key, api_secret, tld)
        await coordinator.async_refresh()

        hass.data[DOMAIN][instance.get(CONF_NAME)] = {
            "data": coordinator.binance_data,
            "coordinator": coordinator
        }

        await async_setup_instance(hass, instance, coordinator)
    _LOGGER.warning("[BINANCE] Binance setup completed")
    return True


async def async_setup_instance(hass, instance, coordinator):
    """Set up a particular instance of Binance integration."""
    native_currency = instance.get(CONF_NATIVE_CURRENCY).upper()

    await async_setup_sensors(hass, coordinator, instance, native_currency)
    _LOGGER.debug("[BINANCE] Finished setting up Binance instance")

async def async_setup_sensors(hass, binance_data, instance, native_currency):
    _LOGGER.debug("[BINANCE] Setting up sensors")
    """Set up Binance sensors."""
    balances = instance.get(CONF_BALANCES)
    tickers = instance.get(CONF_EXCHANGES)
    name = instance.get(CONF_NAME)

    await async_load_balance_sensors(hass,instance, binance_data, balances, name, native_currency)
    await async_load_ticker_sensors(hass,instance, binance_data, tickers, name)

async def async_load_balance_sensors(hass,instance, binance_data, balances, name, native_currency):
    _LOGGER.debug("[BINANCE] load_balance_sensors")
    """Load balance sensors for given currencies."""
    if hasattr(binance_data, "balances"):
        for balance in binance_data.balances:
            if not balances or balance["asset"] in balances:
                balance_info = {
                    "name": name,
                    "asset": balance["asset"],
                    "free": balance["free"],
                    "locked": balance["locked"],
                    "native": native_currency
                }
                hass.async_create_task(
                    async_load_platform(hass, "sensor", DOMAIN, balance_info, instance)
                )

async def async_load_ticker_sensors(hass,instance, binance_data, tickers, name):
    _LOGGER.debug("[BINANCE] load_ticker_sensors")
    """Load ticker sensors for given symbols."""
    if tickers and len(tickers) > 0:
        if hasattr(binance_data, "tickers"):
            for ticker in binance_data.tickers:
                if ticker["symbol"] in tickers:
                    ticker_info = {
                        "name": name,
                        "symbol": ticker["symbol"],
                        "price": ticker["price"]
                    }
                    hass.async_create_task(
                        async_load_platform(hass, "sensor", DOMAIN, ticker_info, instance)
                    )

class BinanceData:
    """Representation of Binance data fetching."""
    def __init__(self, hass: HomeAssistant, api_key, api_secret, tld):
        """Initialize the Binance data object."""
        self.hass = hass
        self.api_key = api_key
        self.api_secret = api_secret
        self.tld = tld
        self.balances = []
        self.tickers = {}
        self.client = None
        self.client_initialized = False  # Nouvel attribut pour suivre l'initialisation du client
        self.balances_initialized = False  # Nouvel attribut pour suivre l'initialisation des balances
        self.tickers_initialized = False  # Nouvel attribut pour suivre l'initialisation des tickers

        hass.async_create_task(self.init_client())
        hass.async_create_task(self.async_update())

    async def init_client(self):
        _LOGGER.debug("[BINANCE] Initializing Binance client")
        try:
            self.client = await self.hass.async_add_executor_job(
                lambda: Client(self.api_key, self.api_secret, tld=self.tld))
            self.client_initialized = True
            _LOGGER.debug("[BINANCE] Binance client successfully initialized")
        except Exception as e:
            _LOGGER.error(f"Error initializing Binance client: {e}")
            self.client = None
            self.client_initialized = False

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_update(self):
        while not self.client_initialized:
            _LOGGER.warning("[BINANCE] Waiting for Binance client to initialize...")
            await asyncio.sleep(5)  # Attendre 5 secondes avant de réessayer

        _LOGGER.debug("[BINANCE] Binance client is initialized, proceeding with update")
        try:
            await self.hass.async_add_executor_job(self.update_balances)
            await self.hass.async_add_executor_job(self.update_tickers)
        except (BinanceAPIException, BinanceRequestException) as e:
            _LOGGER.error(f"Error fetching data from Binance: {e}")
            return False
        _LOGGER.error("Binance data update completed")

    def update_balances(self):
        _LOGGER.debug("Updating balances")
        if not self.client:
            _LOGGER.warning("Binance client is not initialized.")
            return
        try:
            account_info = self.client.get_account()
            balances = account_info.get("balances", [])
            self.balances = balances
            self.balances_initialized = True
            _LOGGER.debug(f"Balances updated: {self.balances}")
        except Exception as e:
            _LOGGER.exception(f"Error updating balances: {e}")

    def update_tickers(self):
        _LOGGER.debug("Updating tickers")
        if not self.client:
            _LOGGER.warning("Binance client is not initialized.")
            return
        try:
            prices = self.client.get_all_tickers()
            self.tickers = prices
            self.tickers_initialized = True
            _LOGGER.debug(f"Tickers updated: {self.tickers}")
        except Exception as e:
            _LOGGER.exception(f"Error updating tickers: {e}")
   
    async def async_wait_until_initialized(self):
        while not self.tickers_initialized or not self.balances_initialized:
            await asyncio.sleep(1)  # Attendre 1 seconde avant de réessayer
        _LOGGER.debug("[BINANCE] Binance client is fully initialized")

class BinanceCoordinator(DataUpdateCoordinator):
    """Classe pour gérer les mises à jour des données Binance."""

    def __init__(self, hass, api_key, api_secret, tld):
        """Initialise le coordinateur."""
        self.binance_data = BinanceData(hass, api_key, api_secret, tld)

        super().__init__(
            hass,
            _LOGGER,
            name="Binance Coordinator",
            update_interval=SCAN_INTERVAL,
        )

    async def _async_update_data(self):
        """Mettre à jour les données de l'API Binance."""
        try:
            if not self.binance_data.client_initialized:
                await self.binance_data.init_client()

            await self.binance_data.async_update()
            return self.binance_data
        except Exception as e:
            raise UpdateFailed(f"Erreur lors de la mise à jour des données Binance : {e}")
