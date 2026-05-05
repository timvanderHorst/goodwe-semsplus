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
        _LOGGER.debug(
            "Initializing SemsPlusCoordinator with scan interval: %d seconds", SCAN_INTERVAL_SECONDS
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.client = client
        _LOGGER.debug("SemsPlusCoordinator initialized")

    async def _async_update_data(self) -> dict:
        """Fetch data from SEMS+ API."""
        _LOGGER.debug("Starting data update from SEMS+ API")
        try:
            _LOGGER.debug("Fetching stations list")
            stations = await self.hass.async_add_executor_job(self.client.get_stations)
            _LOGGER.debug("Received %d stations", len(stations))

            data = {"stations": {}}

            for station in stations:
                station_id = station.get("id") or station.get("stationId", "")
                if not station_id:
                    _LOGGER.debug("Skipping station without ID: %s", station)
                    continue

                _LOGGER.debug("Processing station: %s", station_id)
                station_info = await self.hass.async_add_executor_job(
                    self.client.get_station_info, station_id
                )
                _LOGGER.debug(
                    "Retrieved station info for %s: %s",
                    station_id,
                    list(station_info.keys())
                    if isinstance(station_info, dict)
                    else type(station_info),
                )

                device_data = await self.hass.async_add_executor_job(
                    self.client.get_device_status, station_id
                )
                _LOGGER.debug(
                    "Retrieved device data for %s: type=%s", station_id, type(device_data)
                )

                # Extract device list from nested response
                devices = []
                if isinstance(device_data, dict):
                    for detail in device_data.get("deviceDetailList", []):
                        for dev in detail.get("statusDetailList", []):
                            devices.append(dev)
                elif isinstance(device_data, list):
                    devices = device_data

                _LOGGER.debug("Station %s has %d devices", station_id, len(devices))
                data["stations"][station_id] = {
                    "info": station_info,
                    "devices": devices,
                    "name": station.get("stationName", station_id),
                }

            _LOGGER.info(
                "Data update complete: %d stations with %d total devices",
                len(data["stations"]),
                sum(len(s["devices"]) for s in data["stations"].values()),
            )
            return data

        except SemsPlusAuthError as err:
            _LOGGER.error("Authentication failed during data update: %s", err, exc_info=True)
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except SemsPlusApiError as err:
            _LOGGER.error("API error during data update: %s", err, exc_info=True)
            raise UpdateFailed(f"API error: {err}") from err
