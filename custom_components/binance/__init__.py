from datetime import timedelta
import logging

from binance.client import AsyncClient
from binance.exceptions import BinanceAPIException, BinanceRequestException
import voluptuous as vol

from homeassistant.const import CONF_API_KEY, CONF_NAME
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.util import Throttle

__version__ = "1.0.0"
REQUIREMENTS = ["python-binance==1.0.10"]

DOMAIN = "binance"

DEFAULT_NAME = "Binance"
DEFAULT_DOMAIN = "us"
DEFAULT_CURRENCY = "USD"
CONF_API_SECRET = "api_secret"
CONF_BALANCES = "balances"
CONF_EXCHANGES = "exchanges"
CONF_DOMAIN = "domain"
CONF_NATIVE_CURRENCY = "native_currency"

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


async def async_setup(hass, config):
    api_key = config[DOMAIN][CONF_API_KEY]
    api_secret = config[DOMAIN][CONF_API_SECRET]
    name = config[DOMAIN].get(CONF_NAME)
    balances = config[DOMAIN].get(CONF_BALANCES)
    tickers = config[DOMAIN].get(CONF_EXCHANGES)
    native_currency = config[DOMAIN].get(CONF_NATIVE_CURRENCY).upper()
    tld = config[DOMAIN].get(CONF_DOMAIN).lower()

    binance_data = BinanceData(api_key, api_secret, tld)
    hass.data[DATA_BINANCE] = binance_data

    if not balances:
        response = await binance_data.async_get_balance(all=True)
        if response:
            for balance in response:
                hass.async_create_task(
                    async_load_platform(
                        hass,
                        "sensor",
                        DOMAIN,
                        {"balance": balance, "name": name, "native": native_currency},
                        config,
                    )
                )
    else:
        _LOGGER.info(f"Initializing balance sensors for {balances}")
        for balance in [i.upper() for i in balances]:
            response = await binance_data.async_get_balance(asset=balance)
            if response:
                hass.async_create_task(
                    async_load_platform(
                        hass,
                        "sensor",
                        DOMAIN,
                        {
                            "balance": response,
                            "name": name,
                            "native": native_currency,
                        },
                        config,
                    )
                )

    if not tickers:
        response = await binance_data.async_get_exchange(all=True)
        if response:
            for ticker in response:
                hass.async_create_task(
                    async_load_platform(
                        hass,
                        "sensor",
                        DOMAIN,
                        {"ticker": ticker, "name": name},
                        config,
                    )
                )
    else:
        _LOGGER.info(f"Initializing exchange sensors for {tickers}")
        for ticker in [i.upper() for i in tickers]:
            response = await binance_data.async_get_exchange(pair=ticker)
            if response:
                hass.async_create_task(
                    async_load_platform(
                        hass,
                        "sensor",
                        DOMAIN,
                        {
                            "ticker": response,
                            "name": name,
                        },
                        config,
                    )
                )

    return True


class BinanceData:
    def __init__(self, api_key, api_secret, tld):
        """Initialize."""
        self._api_key = api_key
        self._api_secret = api_secret
        self._tld = tld

    async def async_connect(self):
        try:
            _LOGGER.debug(f"Connecting to binance.{self._tld}")
            client = await AsyncClient.create(
                self._api_key, self._api_secret, tld=self._tld
            )
        except (BinanceAPIException, BinanceRequestException) as e:
            _LOGGER.error(f"Error connecting to binance.{self._tld}: {e.message}")
            return None

        return client

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_get_balance(self, asset=None, all=False):
        response = {}
        client = await self.async_connect()
        if client:
            try:
                if asset and not all:
                    _LOGGER.debug(
                        f"Fetching balance for {asset} from binance.{self._tld}"
                    )
                    response = await client.get_asset_balance(asset=asset)
                elif all:
                    _LOGGER.debug(f"Fetching balances from binance.{self._tld}")
                    account_info = await client.get_account()
                    response = account_info.get("balances", [])
            except (BinanceAPIException, BinanceRequestException) as e:
                _LOGGER.error(
                    f"Error fetching data from binance.{self._tld}: {e.message}"
                )
            finally:
                await client.close_connection()

        return response

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_get_exchange(self, pair=None, all=False):
        response = {}
        client = await self.async_connect()
        if client:
            try:
                if pair and not all:
                    _LOGGER.debug(
                        f"Fetching exchange rate for {pair} from binance.{self._tld}"
                    )
                    response = await client.get_all_tickers(symbol=pair)
                elif all:
                    _LOGGER.debug(f"Fetching exchange rates from binance.{self._tld}")
                    response = await client.get_all_tickers()
            except (BinanceAPIException, BinanceRequestException) as e:
                _LOGGER.error(
                    f"Error fetching data from binance.{self._tld}: {e.message}"
                )
            finally:
                await client.close_connection()

        return response
