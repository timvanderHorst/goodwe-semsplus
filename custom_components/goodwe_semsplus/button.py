"""Button platform for GoodWe SEMS+."""

import asyncio
import logging
from datetime import datetime

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_COMMAND_DELAY, DEFAULT_COMMAND_DELAY, DOMAIN
from .coordinator import SemsPlusCoordinator, _extract_devices

_LOGGER = logging.getLogger(__name__)


def _extract_device_sn(device: dict) -> str:
    """Extract device serial number from known keys."""
    return (
        device.get("sn")
        or device.get("deviceSn")
        or device.get("serialNum")
        or device.get("serialNo")
        or ""
    )


async def _build_station_data_from_api(
    hass: HomeAssistant, coordinator: SemsPlusCoordinator
) -> dict[str, dict]:
    """Build station/device data by querying the API directly."""
    stations = await hass.async_add_executor_job(coordinator.client.get_stations)
    rebuilt: dict[str, dict] = {}

    for station in stations:
        station_id = station.get("id") or station.get("stationId", "")
        if not station_id:
            continue

        station_info = await hass.async_add_executor_job(
            coordinator.client.get_station_info, station_id
        )
        device_data = await hass.async_add_executor_job(
            coordinator.client.get_device_status, station_id
        )

        devices = _extract_devices(device_data if isinstance(device_data, dict) else {})

        rebuilt[station_id] = {
            "info": station_info,
            "devices": devices,
            "name": station.get("name", station_id),
        }

    return rebuilt


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SEMS+ buttons from a config entry."""
    _LOGGER.info("Setting up SEMS+ button platform for entry: %s", entry.entry_id)
    coordinator: SemsPlusCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Get command delay from options or use default
    command_delay = entry.options.get(CONF_COMMAND_DELAY, DEFAULT_COMMAND_DELAY)
    _LOGGER.info("Command delay configured: %d seconds", command_delay)

    stations_data = coordinator.data.get("stations", {})
    total_devices = sum(len(station.get("devices", [])) for station in stations_data.values())
    if total_devices == 0:
        _LOGGER.warning(
            "No devices found in coordinator data during button setup; attempting direct API discovery"
        )
        try:
            stations_data = await _build_station_data_from_api(hass, coordinator)
            total_devices = sum(
                len(station.get("devices", [])) for station in stations_data.values()
            )
            _LOGGER.info("Direct API discovery found %d devices for button setup", total_devices)
        except Exception as err:
            _LOGGER.error("Direct API discovery for buttons failed: %s", err, exc_info=True)

    entities: list[ButtonEntity] = []
    seen_unique_ids: set[str] = set()

    for station_id, station_data in stations_data.items():
        station_name = station_data.get("name", station_id)
        _LOGGER.info("Processing station: %s (%s)", station_id, station_name)

        # Device-level control buttons (inverters)
        for device in station_data.get("devices", []):
            device_sn = _extract_device_sn(device)
            device_name = device.get("name") or device.get("deviceName") or device_sn

            if not device_sn:
                device_keys = list(device.keys()) if isinstance(device, dict) else []
                _LOGGER.info(
                    "Skipping device without serial number. Device keys: %s. Full device: %s",
                    device_keys,
                    device,
                )
                continue

            # Get plant_id from station info
            station_info = station_data.get("info", {})
            plant_id = (
                station_info.get("id")
                or station_info.get("stationId")
                or station_info.get("plantId")
                or station_id
            )
            _LOGGER.info(
                "Creating buttons for device: %s (sn=%s, plant_id=%s)",
                device_name,
                device_sn,
                plant_id,
            )

            for action in ("stop", "start", "restart"):
                unique_id = f"{device_sn}_{action}"
                if unique_id in seen_unique_ids:
                    continue
                seen_unique_ids.add(unique_id)

                entities.append(
                    SemsPlusControlButton(
                        coordinator=coordinator,
                        station_id=station_id,
                        station_name=station_name,
                        device_sn=device_sn,
                        device_name=device_name,
                        plant_id=plant_id,
                        action=action,
                        command_delay=command_delay,
                    )
                )

    _LOGGER.debug("Adding %d button entities to Home Assistant", len(entities))
    async_add_entities(entities)
    _LOGGER.info("Button platform setup complete: %d entities added", len(entities))


class SemsPlusControlButton(CoordinatorEntity, ButtonEntity):
    """Button entity for inverter control commands."""

    _attr_entity_registry_enabled_default = True

    def __init__(
        self,
        coordinator: SemsPlusCoordinator,
        station_id: str,
        station_name: str,
        device_sn: str,
        device_name: str,
        plant_id: str,
        action: str,
        command_delay: int,
    ) -> None:
        """Initialize button entity."""
        super().__init__(coordinator)
        self._station_id = station_id
        self._station_name = station_name
        self._device_sn = device_sn
        self._device_name = device_name
        self._plant_id = plant_id
        self._action = action
        self._command_delay = command_delay
        self._command_sent_time: datetime | None = None
        _LOGGER.info(
            "Initializing button: device=%s, action=%s, delay=%d", device_sn, action, command_delay
        )

        # Set device class based on action
        if action == "restart":
            self._attr_device_class = ButtonDeviceClass.RESTART
        # stop and start don't have specific device classes

        # Build entity ID and name
        action_title = action.capitalize()
        self._attr_name = f"{device_name} {action_title}"
        self._attr_unique_id = f"{device_sn}_{action}"
        _LOGGER.info(
            "Button entity created: unique_id=%s, name=%s", self._attr_unique_id, self._attr_name
        )

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._device_sn)},
            "name": self._device_name,
            "manufacturer": "GoodWe",
            "model": "Inverter",
            "via_device": (DOMAIN, self._station_id),
        }

    @property
    def available(self) -> bool:
        """Return True if button is available (delay period has passed)."""
        if self._command_sent_time is None:
            return True

        elapsed = (datetime.now() - self._command_sent_time).total_seconds()
        available = elapsed >= self._command_delay
        remaining = max(0, self._command_delay - elapsed)
        _LOGGER.debug(
            "Button %s availability check: elapsed=%.1f, delay=%d, available=%s, remaining=%.0f",
            self._attr_unique_id,
            elapsed,
            self._command_delay,
            available,
            remaining,
        )
        return available

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra state attributes."""
        attrs = {}

        if self._command_sent_time is not None:
            elapsed = (datetime.now() - self._command_sent_time).total_seconds()
            if elapsed < self._command_delay:
                remaining = self._command_delay - elapsed
                attrs["status_update_in"] = f"{int(remaining)}s"
                # Set status to unknown while waiting for update
                attrs["current_status"] = "unknown"
            else:
                # Clear the command time once delay has passed
                self._command_sent_time = None

        return attrs

    async def async_press(self) -> None:
        """Handle button press."""
        try:
            # Record when command was sent
            self._command_sent_time = datetime.now()
            _LOGGER.info(
                "Button pressed: device=%s, action=%s, timestamp=%s",
                self._device_sn,
                self._action,
                self._command_sent_time,
            )

            if self._action == "stop":
                _LOGGER.debug(
                    "Sending stop_inverter command: device=%s, plant=%s",
                    self._device_sn,
                    self._plant_id,
                )
                await self.hass.async_add_executor_job(
                    self.coordinator.client.stop_inverter,
                    self._device_sn,
                    self._plant_id,
                    self._device_name,
                )
            elif self._action == "start":
                _LOGGER.debug(
                    "Sending start_inverter command: device=%s, plant=%s",
                    self._device_sn,
                    self._plant_id,
                )
                await self.hass.async_add_executor_job(
                    self.coordinator.client.start_inverter,
                    self._device_sn,
                    self._plant_id,
                    self._device_name,
                )
            elif self._action == "restart":
                _LOGGER.debug(
                    "Sending restart_inverter command: device=%s, plant=%s",
                    self._device_sn,
                    self._plant_id,
                )
                await self.hass.async_add_executor_job(
                    self.coordinator.client.restart_inverter,
                    self._device_sn,
                    self._plant_id,
                    self._device_name,
                )

            _LOGGER.info(
                "Inverter %s %s command sent successfully (status will update in ~%ds)",
                self._device_name,
                self._action,
                self._command_delay,
            )

            # Schedule refresh after delay instead of immediately
            async def delayed_refresh():
                _LOGGER.debug(
                    "Waiting %d seconds before refreshing status for %s",
                    self._command_delay,
                    self._device_sn,
                )
                await asyncio.sleep(self._command_delay)
                _LOGGER.debug(
                    "Refreshing status for %s after %ds command delay",
                    self._device_name,
                    self._command_delay,
                )
                await self.coordinator.async_request_refresh()

            _LOGGER.debug("Scheduling delayed refresh task for %s", self._device_sn)
            self.hass.create_task(delayed_refresh())

        except Exception as err:
            _LOGGER.error(
                "Error sending %s command to %s: %s",
                self._action,
                self._device_name,
                err,
            )
            # Clear command time on error
            self._command_sent_time = None
            raise
