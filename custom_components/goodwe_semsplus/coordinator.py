"""Data update coordinator for GoodWe SEMS+."""

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SemsPlusApiError, SemsPlusAuthError, SemsPlusClient
from .const import DOMAIN, SCAN_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)


class SemsPlusCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch data from SEMS+ API."""

    def __init__(self, hass: HomeAssistant, client: SemsPlusClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.client = client

    async def _async_update_data(self) -> dict:
        """Fetch data from SEMS+ API."""
        try:
            stations = await self.hass.async_add_executor_job(self.client.get_stations)

            data = {"stations": {}}

            for station in stations:
                station_id = station.get("id") or station.get("stationId", "")
                if not station_id:
                    continue

                station_info = await self.hass.async_add_executor_job(
                    self.client.get_station_info, station_id
                )
                device_data = await self.hass.async_add_executor_job(
                    self.client.get_device_status, station_id
                )

                # Extract device list from nested response
                devices = []
                if isinstance(device_data, dict):
                    for detail in device_data.get("deviceDetailList", []):
                        for dev in detail.get("statusDetailList", []):
                            devices.append(dev)
                elif isinstance(device_data, list):
                    devices = device_data

                data["stations"][station_id] = {
                    "info": station_info,
                    "devices": devices,
                    "name": station.get("stationName", station_id),
                }

            return data

        except SemsPlusAuthError as err:
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except SemsPlusApiError as err:
            raise UpdateFailed(f"API error: {err}") from err
