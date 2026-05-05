"""The GoodWe SEMS+ integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant

from .api import SemsPlusClient
from .const import DOMAIN
from .coordinator import SemsPlusCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.BUTTON]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up GoodWe SEMS+ from a config entry."""
    _LOGGER.info("Setting up GoodWe SEMS+ integration for entry: %s", entry.entry_id)
    _LOGGER.debug("Config entry data keys: %s", list(entry.data.keys()))

    client = SemsPlusClient(
        email=entry.data[CONF_EMAIL],
        password=entry.data[CONF_PASSWORD],
    )
    _LOGGER.debug("SemsPlusClient created")

    coordinator = SemsPlusCoordinator(hass, client)
    _LOGGER.debug("Performing initial coordinator refresh")
    await coordinator.async_config_entry_first_refresh()
    _LOGGER.debug("Initial coordinator refresh complete")

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    _LOGGER.debug("Coordinator registered in hass.data")

    _LOGGER.debug("Setting up platforms: %s", PLATFORMS)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.debug("Platforms setup complete")

    # Set up listener for options updates
    entry.async_on_unload(entry.add_update_listener(async_update_listener))
    _LOGGER.debug("Options update listener registered")

    _LOGGER.info("GoodWe SEMS+ setup complete for entry: %s", entry.entry_id)
    return True


async def async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options updates."""
    _LOGGER.info("Options updated for entry: %s, reloading", entry.entry_id)
    _LOGGER.debug("Updated options: %s", entry.options)
    # Reload the entry when options change
    await hass.config_entries.async_reload(entry.entry_id)
    _LOGGER.debug("Entry reload initiated")


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading GoodWe SEMS+ entry: %s", entry.entry_id)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.debug("Entry removed from hass.data")
    _LOGGER.info("GoodWe SEMS+ unload complete for entry: %s", entry.entry_id)
    return unload_ok
