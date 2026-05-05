"""Tests for GoodWe SEMS+ coordinator."""

import sys
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

sys.path.insert(0, ".")

from custom_components.goodwe_semsplus.api import SemsPlusApiError, SemsPlusAuthError
from custom_components.goodwe_semsplus.coordinator import SemsPlusCoordinator


@pytest.mark.asyncio
async def test_coordinator_update_data_success_nested_devices(hass):
    """Test coordinator update builds normalized station/device structure."""
    client = MagicMock()
    client.get_stations = MagicMock(
        return_value=[
            {"id": "station-1", "stationName": "Main Station"},
            {"stationName": "Missing ID"},
        ]
    )
    client.get_station_info = MagicMock(return_value={"id": "plant-1", "pac": 500})
    client.get_device_status = MagicMock(
        return_value={
            "deviceDetailList": [
                {
                    "statusDetailList": [
                        {"sn": "INV-001", "status": 1},
                        {"sn": "INV-002", "status": 3},
                    ]
                }
            ]
        }
    )

    async def run_executor_job(func, *args):
        return func(*args)

    hass.async_add_executor_job = AsyncMock(side_effect=run_executor_job)

    coordinator = SemsPlusCoordinator(hass, client)
    data = await coordinator._async_update_data()

    assert "station-1" in data["stations"]
    assert "" not in data["stations"]
    assert data["stations"]["station-1"]["name"] == "Main Station"
    assert len(data["stations"]["station-1"]["devices"]) == 2
    assert data["stations"]["station-1"]["devices"][0]["sn"] == "INV-001"


@pytest.mark.asyncio
async def test_coordinator_update_data_auth_error_raises_updatefailed(hass):
    """Test auth errors are wrapped as UpdateFailed."""
    client = MagicMock()
    client.get_stations = MagicMock(side_effect=SemsPlusAuthError("bad credentials"))

    async def run_executor_job(func, *args):
        return func(*args)

    hass.async_add_executor_job = AsyncMock(side_effect=run_executor_job)

    coordinator = SemsPlusCoordinator(hass, client)

    with pytest.raises(UpdateFailed, match="Authentication failed"):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_update_data_api_error_raises_updatefailed(hass):
    """Test API errors are wrapped as UpdateFailed."""
    client = MagicMock()
    client.get_stations = MagicMock(side_effect=SemsPlusApiError("api unavailable"))

    async def run_executor_job(func, *args):
        return func(*args)

    hass.async_add_executor_job = AsyncMock(side_effect=run_executor_job)

    coordinator = SemsPlusCoordinator(hass, client)

    with pytest.raises(UpdateFailed, match="API error"):
        await coordinator._async_update_data()
