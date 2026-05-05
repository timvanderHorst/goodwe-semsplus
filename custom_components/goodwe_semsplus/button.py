"""Button platform for GoodWe SEMS+."""

import asyncio
import logging
from datetime import datetime

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_COMMAND_DELAY, DEFAULT_COMMAND_DELAY, DOMAIN
from .coordinator import SemsPlusCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SEMS+ buttons from a config entry."""
    coordinator: SemsPlusCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Get command delay from options or use default
    command_delay = entry.options.get(CONF_COMMAND_DELAY, DEFAULT_COMMAND_DELAY)

    entities: list[ButtonEntity] = []

    for station_id, station_data in coordinator.data.get("stations", {}).items():
        station_name = station_data.get("name", station_id)

        # Device-level control buttons (inverters)
        for device in station_data.get("devices", []):
            device_sn = device.get("sn", device.get("deviceSn", ""))
            device_name = device.get("deviceName", device_sn)

            if not device_sn:
                continue

            # Get plant_id from station info
            station_info = station_data.get("info", {})
            plant_id = station_info.get("id") or station_info.get("stationId", station_id)

            # Create stop button
            entities.append(
                SemsPlusControlButton(
                    coordinator=coordinator,
                    station_id=station_id,
                    station_name=station_name,
                    device_sn=device_sn,
                    device_name=device_name,
                    plant_id=plant_id,
                    action="stop",
                    command_delay=command_delay,
                )
            )

            # Create start button
            entities.append(
                SemsPlusControlButton(
                    coordinator=coordinator,
                    station_id=station_id,
                    station_name=station_name,
                    device_sn=device_sn,
                    device_name=device_name,
                    plant_id=plant_id,
                    action="start",
                    command_delay=command_delay,
                )
            )

            # Create restart button
            entities.append(
                SemsPlusControlButton(
                    coordinator=coordinator,
                    station_id=station_id,
                    station_name=station_name,
                    device_sn=device_sn,
                    device_name=device_name,
                    plant_id=plant_id,
                    action="restart",
                    command_delay=command_delay,
                )
            )

    async_add_entities(entities)


class SemsPlusControlButton(CoordinatorEntity, ButtonEntity):
    """Button entity for inverter control commands."""

    _attr_entity_category = EntityCategory.CONFIG

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

        # Set device class based on action
        if action == "restart":
            self._attr_device_class = ButtonDeviceClass.RESTART
        # stop and start don't have specific device classes

        # Build entity ID and name
        action_title = action.capitalize()
        self._attr_name = f"{device_name} {action_title}"
        self._attr_unique_id = f"{device_sn}_{action}"

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
        return elapsed >= self._command_delay

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

            if self._action == "stop":
                await self.hass.async_add_executor_job(
                    self.coordinator.client.stop_inverter,
                    self._device_sn,
                    self._plant_id,
                    self._device_name,
                )
            elif self._action == "start":
                await self.hass.async_add_executor_job(
                    self.coordinator.client.start_inverter,
                    self._device_sn,
                    self._plant_id,
                    self._device_name,
                )
            elif self._action == "restart":
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
                await asyncio.sleep(self._command_delay)
                await self.coordinator.async_request_refresh()
                _LOGGER.debug(
                    "Refreshing status for %s after %ds command delay",
                    self._device_name,
                    self._command_delay,
                )

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
