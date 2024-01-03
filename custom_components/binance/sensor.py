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

DOMAIN = "binance1"
DEFAULT_COIN_ICON = "mdi:currency-usd-circle"
ATTRIBUTION = "Data provided by Binance"
ATTR_FREE = "free"
ATTR_LOCKED = "locked"
ATTR_NATIVE_BALANCE = "native_balance"
QUOTE_ASSETS = ["USD", "BTC", "USDT", "BUSD", "USDC"]

async def async_setup_platform(hass, config, add_entities, discovery_info=None):
    """Setup the Binance sensors."""
    if discovery_info is None:
        return

    entry_id = discovery_info.get('entry_id')
    coordinator = hass.data[DOMAIN][entry_id]

    sensors = []
    for balance in coordinator.data["balances"]:
        sensors.append(BinanceSensor(coordinator, entry_id, balance))

    for ticker in coordinator.data["tickers"]:
        sensors.append(BinanceExchangeSensor(coordinator, entry_id, ticker))

    add_entities(sensors, True)


class BinanceSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Binance Sensor."""

    def __init__(self, coordinator, name, balance):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._name = f"{name} {balance['asset']} Balance"
        self._asset = balance["asset"]
        self._state = balance["free"]
        self._free = balance["free"]
        self._locked = balance["locked"]
        self._native = coordinator.native_currency
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
        """Return the unit of measurement."""
        return self._asset

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
            ATTR_FREE: f"{self._free} {self._asset}",
            ATTR_LOCKED: f"{self._locked} {self._asset}",
        }

    async def async_update(self):
        """Update sensor values."""
        await self.coordinator.async_request_refresh()
        # Update logic for native balance based on ticker data
        for ticker in self.coordinator.data["tickers"]:
            if ticker["symbol"] == self._asset + self._native:
                self._native_balance = round(
                    float(ticker["price"]) * float(self._free), 2
                )
                break


class BinanceExchangeSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Binance Exchange Sensor."""

    def __init__(self, coordinator, name, ticker):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._name = f"{name} {ticker['symbol']} Exchange"
        self._symbol = ticker["symbol"]
        self._state = ticker["price"]
        self._unit_of_measurement = self._determine_unit(ticker["symbol"])

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
        """Return the unit of measurement."""
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

    def _determine_unit(self, symbol):
        """Determine the unit of measurement based on the symbol."""
        if symbol[-4:] in QUOTE_ASSETS[2:5]:
            return symbol[-4:]
        elif symbol[-3:] in QUOTE_ASSETS[:2]:
            return symbol[-3:]

    async def async_update(self):
        """Update sensor values."""
        await self.coordinator.async_request_refresh()
        self._state = next((ticker["price"] for ticker in self.coordinator.data["tickers"] if ticker["symbol"] == self._symbol), None)
