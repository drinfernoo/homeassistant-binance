"""
Binance exchange sensor
"""
from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

CURRENCY_ICONS = {
    "BTC": "mdi:currency-btc",
    "ETH": "mdi:currency-eth",
    "EUR": "mdi:currency-eur",
    "LTC": "mdi:litecoin",
    "USD": "mdi:currency-usd",
}

DOMAIN = "binance"

QUOTE_ASSETS = ["USD", "BTC", "USDT", "BUSD", "USDC"]

DEFAULT_COIN_ICON = "mdi:currency-usd-circle"

ATTRIBUTION = "Data provided by Binance"
ATTR_FREE = "free"
ATTR_LOCKED = "locked"
ATTR_NATIVE_BALANCE = "native_balance"

DATA_BINANCE = "binance_cache"


async def async_setup_platform(hass, config, add_entities, discovery_info=None):
    """Setup the Binance sensors."""

    if discovery_info is None:
        return

    instance_name = discovery_info.get("name")
    binance_data = hass.data[DOMAIN][instance_name]

    if all(i in discovery_info for i in ["asset", "free", "locked", "native"]):
        asset = discovery_info["asset"]
        free = discovery_info["free"]
        locked = discovery_info["locked"]
        native = discovery_info["native"]

        sensor = BinanceSensor(
            binance_data, instance_name, asset, free, locked, native
        )
    elif all(i in discovery_info for i in ["symbol", "price"]):
        symbol = discovery_info["symbol"]
        price = discovery_info["price"]

        sensor = BinanceExchangeSensor(binance_data, instance_name, symbol, price)

    add_entities([sensor], True)


class BinanceSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Sensor."""

    def __init__(self, coordinator, name, asset, free, locked, native):
        """Initialise le capteur."""
        super().__init__(coordinator)
        self.coordinator = coordinator
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

    async def async_update(self):
        """Mise à jour des valeurs actuelles."""
        await self.coordinator.async_request_refresh()
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


class BinanceExchangeSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Sensor."""

    def __init__(self, coordinator, name, symbol, price):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._name = f"{name} {symbol} Exchange"
        self._symbol = symbol
        self._price = price
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

    async def async_update(self):
        """Mise à jour des valeurs actuelles."""
        await self.coordinator.async_request_refresh()
        for ticker in self._binance_data.tickers:
            if ticker["symbol"] == self._symbol:
                self._state = ticker["price"]
                if ticker["symbol"][-4:] in QUOTE_ASSETS[2:5]:
                    self._unit_of_measurement = ticker["symbol"][-4:]
                elif ticker["symbol"][-3:] in QUOTE_ASSETS[:2]:
                    self._unit_of_measurement = ticker["symbol"][-3:]
                break
