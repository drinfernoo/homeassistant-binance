from datetime import timedelta
import logging

from binance.spot import Spot
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException
import voluptuous as vol

from homeassistant.const import CONF_API_KEY, CONF_NAME
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.discovery import load_platform
from homeassistant.util import Throttle

__version__ = "1.0.1"
REQUIREMENTS = ["python-binance==1.0.10", "binance-connector==1.10.0"]

DOMAIN = "binance"

DEFAULT_NAME = "Binance"
DEFAULT_DOMAIN = "us"
DEFAULT_CURRENCY = "USD"
DEFAULT_WALLET_TYPE = "SPOT"
CONF_API_SECRET = "api_secret"
CONF_BALANCES = "balances"
CONF_EXCHANGES = "exchanges"
CONF_DOMAIN = "domain"
CONF_NATIVE_CURRENCY = "native_currency"
CONF_WALLET_TYPE = "wallet_type"

SCAN_INTERVAL = timedelta(minutes=1)
MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=1)

DATA_BINANCE = "binance_cache"

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
                vol.Optional(CONF_DOMAIN, default=DEFAULT_DOMAIN): cv.string,
                vol.Optional(CONF_WALLET_TYPE, default=DEFAULT_WALLET_TYPE): cv.string,
                vol.Optional(CONF_NATIVE_CURRENCY, default=DEFAULT_CURRENCY): cv.string,
                vol.Required(CONF_API_KEY): cv.string,
                vol.Required(CONF_API_SECRET): cv.string,
                vol.Optional(CONF_BALANCES, default=[]): vol.All(
                    cv.ensure_list, [cv.string]
                ),
                vol.Optional(CONF_EXCHANGES, default=[]): vol.All(
                    cv.ensure_list, [cv.string]
                ),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


def setup(hass, config):
    api_key = config[DOMAIN][CONF_API_KEY]
    api_secret = config[DOMAIN][CONF_API_SECRET]
    name = config[DOMAIN].get(CONF_NAME)
    balances = config[DOMAIN].get(CONF_BALANCES)
    tickers = config[DOMAIN].get(CONF_EXCHANGES)
    native_currency = config[DOMAIN].get(CONF_NATIVE_CURRENCY).upper()
    tld = config[DOMAIN].get(CONF_DOMAIN)
    wallet_type = config[DOMAIN].get(CONF_WALLET_TYPE)

    hass.data[DATA_BINANCE] = binance_data = BinanceData(api_key, api_secret, tld, wallet_type)

    if not hasattr(binance_data, "balances"):
        pass
    else:
        for balance in binance_data.balances:
            if not balances or balance["asset"] in balances:
                balance["name"] = name
                balance["native"] = native_currency
                load_platform(hass, "sensor", DOMAIN, balance, config)

    if not hasattr(binance_data, "tickers"):
        pass
    else:
        for ticker in binance_data.tickers:
            if not tickers or ticker["symbol"] in tickers:
                ticker["name"] = name
                load_platform(hass, "sensor", DOMAIN, ticker, config)

    return True


class BinanceData:
    def __init__(self, api_key, api_secret, tld, wallet_type):
        """Initialize."""
        self.client = Client(api_key, api_secret, tld=tld)
        self.clientSpot = Spot(key=api_key, secret=api_secret)
        self.balances = []
        self.tickers = {}
        self.tld = tld
        self.wallet_type = wallet_type
        self.update()

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        _LOGGER.debug(f"Fetching data from binance.{self.tld}")
        try:
            if self.wallet_type == "FUNDING":
                balances = self.clientSpot.funding_wallet()
            else:
                account_info = self.client.get_account()
                balances = account_info.get("balances", [])
            if balances:
                self.balances = balances
                _LOGGER.debug(f"{wallet_type} Balances updated from binance.{self.tld}")

            prices = self.client.get_all_tickers()
            if prices:
                self.tickers = prices
                _LOGGER.debug(f"Exchange rates updated from binance.{self.tld}")
        except (BinanceAPIException, BinanceRequestException) as e:
            _LOGGER.error(f"Error fetching data from binance.{self.tld}: {e.message}")
            return False
