"""
Binance exchange sensor
"""

from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant.components.sensor import SensorEntity

CURRENCY_ICONS = {
    "BTC": "mdi:currency-btc",
    "ETH": "mdi:ethereum",
    "EUR": "mdi:currency-eur",
    "LTC": "mdi:litecoin",
    "USD": "mdi:currency-usd",
}

QUOTE_ASSETS = ["USD", "BTC", "USDT", "BUSD", "USDC"]

DEFAULT_COIN_ICON = "mdi:currency-usd"

ATTRIBUTION = "Data provided by Binance"
ATTR_FREE = "free"
ATTR_LOCKED = "locked"
ATTR_NATIVE_BALANCE = "native_balance"

DATA_BINANCE = "binance_cache"


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Setup the Binance sensors."""

    if discovery_info is None:
        return
    if all(i in discovery_info for i in ["name", "asset", "free", "locked", "native"]):
        name = discovery_info["name"]
        asset = discovery_info["asset"]
        free = discovery_info["free"]
        locked = discovery_info["locked"]
        native = discovery_info["native"]

        sensor = BinanceSensor(
            hass.data[DATA_BINANCE], name, asset, free, locked, native
        )
    elif all(i in discovery_info for i in ["name", "symbol", "price"]):
        name = discovery_info["name"]
        symbol = discovery_info["symbol"]
        price = discovery_info["price"]

        sensor = BinanceExchangeSensor(hass.data[DATA_BINANCE], name, symbol, price)

    add_entities([sensor], True)


class BinanceSensor(SensorEntity):
    """Representation of a Sensor."""

    def __init__(self, binance_data, name, asset, free, locked, native):
        """Initialize the sensor."""
        self._binance_data = binance_data
        self._name = f"{name} {asset} Balance"
        self._asset = asset
        self._free = free
        self._locked = locked
        self._native = native
        self._unit_of_measurement = asset
        self._state = None
        self._native_balance = None

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

    def update(self):
        """Update current values."""
        self._binance_data.update()
        for balance in self._binance_data.balances:
            if balance["asset"] == self._asset:
                self._state = balance["free"]
                self._free = balance["free"]
                self._locked = balance["locked"]

                if balance["asset"] == self._native:
                    self._native_balance = round(float(balance["free"]), 2)
                break

        for ticker in self._binance_data.tickers:
            if ticker["symbol"] == self._asset + self._native:
                self._native_balance = round(
                    float(ticker["price"]) * float(self._free), 2
                )
                break


class BinanceExchangeSensor(SensorEntity):
    """Representation of a Sensor."""

    def __init__(self, binance_data, name, symbol, price):
        """Initialize the sensor."""
        self._binance_data = binance_data
        self._name = f"{name} {symbol} Exchange"
        self._symbol = symbol
        self._price = price
        self._unit_of_measurement = None
        self._state = None

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

    def update(self):
        """Update current values."""
        self._binance_data.update()
        for ticker in self._binance_data.tickers:
            if ticker["symbol"] == self._symbol:
                self._state = ticker["price"]
                if ticker["symbol"][-4:] in QUOTE_ASSETS[2:5]:
                    self._unit_of_measurement = ticker["symbol"][-4:]
                elif ticker["symbol"][-3:] in QUOTE_ASSETS[:2]:
                    self._unit_of_measurement = ticker["symbol"][-3:]
                break
