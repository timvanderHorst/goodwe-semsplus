"""Sensor platform for GoodWe SEMS+."""

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEVICE_STATUS_MAP, DOMAIN
from .coordinator import SemsPlusCoordinator

_LOGGER = logging.getLogger(__name__)


STATION_SENSORS = [
    {
        "key": "pac",
        "name": "Current Power",
        "unit": UnitOfPower.WATT,
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "key": "eDay",
        "name": "Energy Today",
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
    },
    {
        "key": "eMonth",
        "name": "Energy This Month",
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
    },
    {
        "key": "eTotal",
        "name": "Total Energy",
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
    },
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SEMS+ sensors from a config entry."""
    coordinator: SemsPlusCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = []

    for station_id, station_data in coordinator.data.get("stations", {}).items():
        station_name = station_data.get("name", station_id)

        # Station-level sensors
        for sensor_def in STATION_SENSORS:
            entities.append(
                SemsPlusStationSensor(
                    coordinator=coordinator,
                    station_id=station_id,
                    station_name=station_name,
                    sensor_def=sensor_def,
                )
            )

        # Device-level sensors (inverters)
        for device in station_data.get("devices", []):
            device_sn = device.get("sn", device.get("deviceSn", ""))
            device_name = device.get("name", device.get("deviceName", device_sn))
            entities.append(
                SemsPlusDeviceStatusSensor(
                    coordinator=coordinator,
                    station_id=station_id,
                    device_sn=device_sn,
                    device_name=device_name,
                )
            )

    async_add_entities(entities)


class SemsPlusStationSensor(CoordinatorEntity, SensorEntity):
    """Sensor for station-level data."""

    def __init__(
        self,
        coordinator: SemsPlusCoordinator,
        station_id: str,
        station_name: str,
        sensor_def: dict,
    ) -> None:
        super().__init__(coordinator)
        self._station_id = station_id
        self._key = sensor_def["key"]
        self._attr_name = f"{station_name} {sensor_def['name']}"
        self._attr_unique_id = f"{station_id}_{self._key}"
        self._attr_native_unit_of_measurement = sensor_def["unit"]
        self._attr_device_class = sensor_def["device_class"]
        self._attr_state_class = sensor_def["state_class"]
        self._attr_device_info = {
            "identifiers": {(DOMAIN, station_id)},
            "name": station_name,
            "manufacturer": "GoodWe",
        }

    @property
    def native_value(self):
        """Return the sensor value."""
        station = self.coordinator.data.get("stations", {}).get(self._station_id, {})
        info = station.get("info", {})
        # Try nested paths common in SEMS+ responses
        value = info.get(self._key)
        if value is None and isinstance(info, dict):
            for sub in info.values():
                if isinstance(sub, dict) and self._key in sub:
                    value = sub[self._key]
                    break
        if value is not None:
            try:
                return float(value)
            except (ValueError, TypeError):
                return value
        return None


class SemsPlusDeviceStatusSensor(CoordinatorEntity, SensorEntity):
    """Sensor for individual device (inverter) status."""

    def __init__(
        self,
        coordinator: SemsPlusCoordinator,
        station_id: str,
        device_sn: str,
        device_name: str,
    ) -> None:
        super().__init__(coordinator)
        self._station_id = station_id
        self._device_sn = device_sn
        self._attr_name = f"{device_name} Status"
        self._attr_unique_id = f"{device_sn}_status"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device_sn)},
            "name": device_name,
            "manufacturer": "GoodWe",
            "via_device": (DOMAIN, station_id),
        }

    @property
    def native_value(self):
        """Return device status."""
        station = self.coordinator.data.get("stations", {}).get(self._station_id, {})
        for device in station.get("devices", []):
            sn = device.get("sn", device.get("deviceSn", ""))
            if sn == self._device_sn:
                status = device.get("status", device.get("deviceStatus", "unknown"))
                return DEVICE_STATUS_MAP.get(status, str(status))
        return "unknown"
