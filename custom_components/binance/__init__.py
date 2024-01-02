from datetime import timedelta
import logging
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException
import voluptuous as vol
from homeassistant.const import CONF_API_KEY, CONF_NAME
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.discovery import load_platform
from homeassistant.util import Throttle

__version__ = "1.0.1"
REQUIREMENTS = ["python-binance==1.0.10"]

DOMAIN = "binance"
DATA_BINANCE = "binance_cache"

# Configuration defaults and constants
DEFAULT_NAME = "Binance"
DEFAULT_DOMAIN = "us"
DEFAULT_CURRENCY = "USD"
CONF_API_SECRET = "api_secret"
CONF_BALANCES = "balances"
CONF_EXCHANGES = "exchanges"
CONF_DOMAIN = "domain"
CONF_NATIVE_CURRENCY = "native_currency"
SCAN_INTERVAL = timedelta(seconds=1)
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=1)

_LOGGER = logging.getLogger(__name__)

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


def setup(hass, config):
    """Set up the Binance component."""
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    for instance in config[DOMAIN]:
        setup_instance(hass, instance)

    return True


def setup_instance(hass, instance):
    """Set up a particular instance of Binance integration."""
    name = instance.get(CONF_NAME)
    api_key = instance[CONF_API_KEY]
    api_secret = instance[CONF_API_SECRET]
    tld = instance.get(CONF_DOMAIN)
    native_currency = instance.get(CONF_NATIVE_CURRENCY).upper()

    binance_data = BinanceData(api_key, api_secret, tld)
    hass.data[DOMAIN][name] = binance_data

    setup_sensors(hass, binance_data, instance, native_currency)


def setup_sensors(hass, binance_data, instance, native_currency):
    """Set up Binance sensors."""
    balances = instance.get(CONF_BALANCES)
    tickers = instance.get(CONF_EXCHANGES)
    name = instance.get(CONF_NAME)

    load_balance_sensors(hass, binance_data, balances, name, native_currency)
    load_ticker_sensors(hass, binance_data, tickers, name)


def load_balance_sensors(hass, binance_data, balances, name, native_currency):
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
                load_platform(hass, "sensor", DOMAIN, balance_info, instance)


def load_ticker_sensors(hass, binance_data, tickers, name):
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
                    load_platform(hass, "sensor", DOMAIN, ticker_info, instance)


class BinanceData:
    """Representation of Binance data fetching."""

    def __init__(self, api_key, api_secret, tld):
        """Initialize the Binance data object."""
        self.client = Client(api_key, api_secret, tld=tld)
        self.balances = []
        self.tickers = {}
        self.tld = tld
        self.update()

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Fetch data from Binance API."""
        try:
            self.update_balances()
            self.update_tickers()
        except (BinanceAPIException, BinanceRequestException) as e:
            _LOGGER.error(f"Error fetching data from Binance: {e}")
            return False

    def update_balances(self):
        """Fetch balances from Binance API."""
        account_info = self.client.get_account()
        balances = account_info.get("balances", [])
        if balances:
            self.balances = balances
            _LOGGER.debug(f"Balances updated from Binance.")

    def update_tickers(self):
        """Fetch tickers from Binance API."""
        prices = self.client.get_all_tickers()
        if prices:
            self.tickers = prices
            _LOGGER.debug(f"Tickers updated from Binance.")
