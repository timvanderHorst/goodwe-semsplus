"""Tests for GoodWe SEMS+ sensor platform."""

import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, ".")

from custom_components.goodwe_semsplus.const import DOMAIN
from custom_components.goodwe_semsplus.sensor import (
    STATION_SENSORS,
    SemsPlusDeviceStatusSensor,
    SemsPlusStationSensor,
    async_setup_entry,
)


@pytest.mark.asyncio
async def test_sensor_async_setup_entry_creates_entities():
    """Test sensor setup creates station and device entities."""
    coordinator = MagicMock()
    coordinator.data = {
        "stations": {
            "station-1": {
                "name": "Main Station",
                "info": {"pac": 1000, "eDay": 5.5, "eMonth": 120, "eTotal": 2500},
                "devices": [
                    {"sn": "INV-001", "deviceName": "Inverter 1", "status": 1},
                    {"sn": "INV-002", "deviceName": "Inverter 2", "status": 3},
                ],
            }
        }
    }

    hass = MagicMock()
    hass.data = {DOMAIN: {"entry-1": coordinator}}

    entry = MagicMock()
    entry.entry_id = "entry-1"

    add_entities = MagicMock()

    await async_setup_entry(hass, entry, add_entities)

    add_entities.assert_called_once()
    entities = add_entities.call_args[0][0]
    # 4 station sensors + 2 device status sensors
    assert len(entities) == len(STATION_SENSORS) + 2


def test_station_sensor_native_value_from_nested_info():
    """Test station sensor can read value from nested info dict."""
    coordinator = MagicMock()
    coordinator.data = {
        "stations": {
            "station-1": {
                "info": {
                    "summary": {"pac": "1234.5"},
                }
            }
        }
    }

    sensor = SemsPlusStationSensor(
        coordinator=coordinator,
        station_id="station-1",
        station_name="Main Station",
        sensor_def=STATION_SENSORS[0],
    )

    assert sensor.native_value == 1234.5


def test_station_sensor_native_value_non_numeric_falls_back_to_raw():
    """Test station sensor returns raw value when not numeric."""
    coordinator = MagicMock()
    coordinator.data = {
        "stations": {
            "station-1": {
                "info": {
                    "pac": "n/a",
                }
            }
        }
    }

    sensor = SemsPlusStationSensor(
        coordinator=coordinator,
        station_id="station-1",
        station_name="Main Station",
        sensor_def=STATION_SENSORS[0],
    )

    assert sensor.native_value == "n/a"


def test_device_status_sensor_maps_status_and_unknown():
    """Test device status sensor maps known status and handles unknown device."""
    coordinator = MagicMock()
    coordinator.data = {
        "stations": {
            "station-1": {
                "devices": [
                    {"sn": "INV-001", "status": 3},
                ]
            }
        }
    }

    sensor_known = SemsPlusDeviceStatusSensor(
        coordinator=coordinator,
        station_id="station-1",
        device_sn="INV-001",
        device_name="Inverter 1",
    )
    assert sensor_known.native_value == "stopped"

    sensor_unknown = SemsPlusDeviceStatusSensor(
        coordinator=coordinator,
        station_id="station-1",
        device_sn="INV-404",
        device_name="Missing Inverter",
    )
    assert sensor_unknown.native_value == "unknown"
