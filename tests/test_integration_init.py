"""Tests for integration entry setup/unload lifecycle."""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD

sys.path.insert(0, ".")

from custom_components.goodwe_semsplus import (
    PLATFORMS,
    async_setup_entry,
    async_unload_entry,
    async_update_listener,
)
from custom_components.goodwe_semsplus.const import DOMAIN


@pytest.mark.asyncio
async def test_async_setup_entry_registers_coordinator_and_platforms():
    """Test setup creates coordinator, stores it and forwards platforms."""
    hass = MagicMock()
    hass.data = {}
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()

    coordinator = MagicMock()
    coordinator.async_config_entry_first_refresh = AsyncMock()

    entry = MagicMock()
    entry.entry_id = "entry-1"
    entry.data = {
        CONF_EMAIL: "user@example.com",
        CONF_PASSWORD: "secret",
    }
    entry.add_update_listener = MagicMock(return_value="remove_listener")
    entry.async_on_unload = MagicMock()

    with (
        patch("custom_components.goodwe_semsplus.SemsPlusClient") as mock_client_cls,
        patch("custom_components.goodwe_semsplus.SemsPlusCoordinator", return_value=coordinator),
    ):
        result = await async_setup_entry(hass, entry)

    assert result is True
    mock_client_cls.assert_called_once_with(email="user@example.com", password="secret")
    coordinator.async_config_entry_first_refresh.assert_awaited_once()
    hass.config_entries.async_forward_entry_setups.assert_awaited_once_with(entry, PLATFORMS)
    assert hass.data[DOMAIN]["entry-1"] is coordinator
    entry.add_update_listener.assert_called_once()
    entry.async_on_unload.assert_called_once_with("remove_listener")


@pytest.mark.asyncio
async def test_async_update_listener_reloads_entry():
    """Test options update listener triggers entry reload."""
    hass = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_reload = AsyncMock()

    entry = MagicMock()
    entry.entry_id = "entry-1"
    entry.options = {"command_delay_seconds": 120}

    await async_update_listener(hass, entry)

    hass.config_entries.async_reload.assert_awaited_once_with("entry-1")


@pytest.mark.asyncio
async def test_async_unload_entry_removes_data_when_successful():
    """Test unload removes stored coordinator when unload is successful."""
    hass = MagicMock()
    hass.data = {DOMAIN: {"entry-1": "coordinator"}}
    hass.config_entries = MagicMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

    entry = MagicMock()
    entry.entry_id = "entry-1"

    result = await async_unload_entry(hass, entry)

    assert result is True
    hass.config_entries.async_unload_platforms.assert_awaited_once_with(entry, PLATFORMS)
    assert "entry-1" not in hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_async_unload_entry_keeps_data_when_unsuccessful():
    """Test unload keeps stored coordinator when unload fails."""
    hass = MagicMock()
    hass.data = {DOMAIN: {"entry-1": "coordinator"}}
    hass.config_entries = MagicMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=False)

    entry = MagicMock()
    entry.entry_id = "entry-1"

    result = await async_unload_entry(hass, entry)

    assert result is False
    hass.config_entries.async_unload_platforms.assert_awaited_once_with(entry, PLATFORMS)
    assert hass.data[DOMAIN]["entry-1"] == "coordinator"
