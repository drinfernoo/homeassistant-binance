"""
Binance exchange sensor
"""

from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant.components.sensor import SensorEntity

CURRENCY_ICONS = {
    "BTC": "mdi:currency-btc",
    "ETH": "mdi:currency-eth",
    "EUR": "mdi:currency-eur",
    "LTC": "mdi:litecoin",
    "USD": "mdi:currency-usd",
}

QUOTE_ASSETS = ["USD", "BTC", "USDT", "BUSD", "USDC"]

DEFAULT_COIN_ICON = "mdi:currency-usd-circle"

ATTRIBUTION = "Data provided by Binance"
ATTR_FREE = "free"
ATTR_LOCKED = "locked"
ATTR_NATIVE_BALANCE = "native_balance"

DATA_BINANCE = "binance_cache"


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Setup the Binance sensors."""

    if discovery_info is None:
        return
    if "balance" in discovery_info:
        sensor = setup_balance_sensor(hass, discovery_info)
    elif "ticker" in discovery_info:
        sensor = setup_exchange_sensor(hass, discovery_info)

    async_add_entities([sensor], True)


def setup_balance_sensor(hass, asset):
    name = asset["name"]
    balance = asset["balance"]
    native = asset["native"]

    return BinanceBalanceSensor(hass.data[DATA_BINANCE], name, balance, native)


def setup_exchange_sensor(hass, exchange):
    pair = exchange["ticker"]
    name = exchange["name"]

    return BinanceExchangeSensor(hass.data[DATA_BINANCE], name, pair)


class BinanceBalanceSensor(SensorEntity):
    """Representation of a Sensor."""

    def __init__(self, binance_data, name, balance, native):
        """Initialize the sensor."""
        self._binance_data = binance_data

        self._asset = balance["asset"]
        self._free = balance["free"]
        self._locked = balance["locked"]
        self._native = native
        self._native_balance = None

        self._name = f"{name} {self._asset} Balance"
        self._state = None
        self._unit_of_measurement = self._asset

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement this sensor expresses itself in."""
        return self._unit_of_measurement

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return CURRENCY_ICONS.get(self._asset, DEFAULT_COIN_ICON)

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""

        return {
            ATTR_ATTRIBUTION: ATTRIBUTION,
            ATTR_NATIVE_BALANCE: f"{self._native_balance} {self._native}",
            ATTR_FREE: f"{self._free} {self._unit_of_measurement}",
            ATTR_LOCKED: f"{self._locked} {self._unit_of_measurement}",
        }

    async def async_update(self):
        """Update current values."""
        balance = await self._binance_data.async_get_balance(asset=self._asset)
        if not balance:
            return

        self._state = balance["free"]
        self._free = balance["free"]
        self._locked = balance["locked"]

        if balance["asset"] == self._native:
            self._native_balance = round(float(balance["free"]), 2)
        else:
            ticker = await self._binance_data.async_get_exchange(
                pair=self._asset + self._native
            )
            if ticker:
                self._native_balance = round(
                    float(ticker["price"]) * float(self._free), 2
                )


class BinanceExchangeSensor(SensorEntity):
    """Representation of a Sensor."""

    def __init__(self, binance_data, name, ticker):
        """Initialize the sensor."""
        self._binance_data = binance_data
        self._symbol = ticker["symbol"]
        self._price = ticker["price"]

        self._name = f"{name} {self._symbol} Exchange"
        self._state = None
        self._unit_of_measurement = self._decide_unit(self._symbol)

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement this sensor expresses itself in."""
        return self._unit_of_measurement

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return CURRENCY_ICONS.get(self._unit_of_measurement, DEFAULT_COIN_ICON)

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""

        return {
            ATTR_ATTRIBUTION: ATTRIBUTION,
        }

    def _decide_unit(self, pair):
        if pair[-4:] in QUOTE_ASSETS[2:5]:
            return pair[-4:]
        elif pair[-3:] in QUOTE_ASSETS[:2]:
            return pair[-3:]

    async def async_update(self):
        """Update current values."""
        ticker = await self._binance_data.async_get_exchange(pair=self._symbol)
        if not ticker:
            return

        self._state = ticker["price"]
