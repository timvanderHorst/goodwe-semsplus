"""Tests for Home Assistant integration components (buttons, sensors, etc.)."""

import sys
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
)

sys.path.insert(0, ".")

from custom_components.goodwe_semsplus.button import (
    SemsPlusControlButton,
    async_setup_entry,
)
from custom_components.goodwe_semsplus.const import DOMAIN
from custom_components.goodwe_semsplus.coordinator import SemsPlusCoordinator


def mock_create_task(coro):
    """Mock create_task that properly closes coroutines to avoid warnings."""
    coro.close()  # Close to avoid ResourceWarning about unawaited coroutine
    return MagicMock()


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock()
    hass.create_task = MagicMock(side_effect=mock_create_task)
    return hass


@pytest.fixture
def mock_coordinator(mock_hass):
    """Create a mock coordinator with test data."""
    coordinator = MagicMock(spec=SemsPlusCoordinator)
    coordinator.hass = mock_hass
    coordinator.last_update_success = True
    coordinator.client = MagicMock()
    coordinator.client.stop_inverter = AsyncMock(return_value={"code": "00000"})
    coordinator.client.start_inverter = AsyncMock(return_value={"code": "00000"})
    coordinator.client.restart_inverter = AsyncMock(return_value={"code": "00000"})
    coordinator.async_request_refresh = AsyncMock()

    # Mock coordinator data
    coordinator.data = {
        "stations": {
            "station-123": {
                "name": "Test Station",
                "info": {"id": "plant-123", "stationId": "station-123"},
                "devices": [
                    {
                        "sn": "DEVICE-001",
                        "deviceName": "SolarGoodwe",
                        "status": 1,
                    }
                ],
            }
        }
    }

    return coordinator


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_EMAIL: "test@example.com",
            CONF_PASSWORD: "test_password",
        },
        entry_id="entry-123",
        title="GoodWe SEMS+",
    )


class TestSemsPlusControlButton:
    """Test suite for SemsPlusControlButton entity."""

    def test_button_initialization_stop(self, mock_coordinator):
        """Test button initialization for stop action."""
        button = SemsPlusControlButton(
            coordinator=mock_coordinator,
            station_id="station-123",
            station_name="Test Station",
            device_sn="DEVICE-001",
            device_name="SolarGoodwe",
            plant_id="plant-123",
            action="stop",
            command_delay=30,
        )

        assert button._action == "stop"
        assert button._device_sn == "DEVICE-001"
        assert button._device_name == "SolarGoodwe"
        assert button._plant_id == "plant-123"
        assert button._attr_name == "SolarGoodwe Stop"
        assert button._attr_unique_id == "DEVICE-001_stop"

    def test_button_initialization_start(self, mock_coordinator):
        """Test button initialization for start action."""
        button = SemsPlusControlButton(
            coordinator=mock_coordinator,
            station_id="station-123",
            station_name="Test Station",
            device_sn="DEVICE-001",
            device_name="SolarGoodwe",
            plant_id="plant-123",
            action="start",
            command_delay=30,
        )

        assert button._action == "start"
        assert button._attr_name == "SolarGoodwe Start"
        assert button._attr_unique_id == "DEVICE-001_start"

    def test_button_initialization_restart(self, mock_coordinator):
        """Test button initialization for restart action."""
        button = SemsPlusControlButton(
            coordinator=mock_coordinator,
            station_id="station-123",
            station_name="Test Station",
            device_sn="DEVICE-001",
            device_name="SolarGoodwe",
            plant_id="plant-123",
            action="restart",
            command_delay=30,
        )

        assert button._action == "restart"
        assert button._attr_name == "SolarGoodwe Restart"
        assert button._attr_unique_id == "DEVICE-001_restart"

    def test_device_info(self, mock_coordinator):
        """Test device info property."""
        button = SemsPlusControlButton(
            coordinator=mock_coordinator,
            station_id="station-123",
            station_name="Test Station",
            device_sn="DEVICE-001",
            device_name="SolarGoodwe",
            plant_id="plant-123",
            action="stop",
            command_delay=30,
        )

        device_info = button.device_info
        assert device_info["identifiers"] == {(DOMAIN, "DEVICE-001")}
        assert device_info["name"] == "SolarGoodwe"
        assert device_info["manufacturer"] == "GoodWe"
        assert device_info["model"] == "Inverter"
        assert device_info["via_device"] == (DOMAIN, "station-123")

    @pytest.mark.asyncio
    async def test_button_press_stop(self, mock_coordinator):
        """Test button press for stop action."""
        button = SemsPlusControlButton(
            coordinator=mock_coordinator,
            station_id="station-123",
            station_name="Test Station",
            device_sn="DEVICE-001",
            device_name="SolarGoodwe",
            plant_id="plant-123",
            action="stop",
            command_delay=30,
        )

        # Mock the hass executor
        mock_hass = MagicMock()
        mock_hass.async_add_executor_job = AsyncMock(return_value={"code": "00000"})
        mock_hass.create_task = MagicMock(side_effect=mock_create_task)
        button.hass = mock_hass

        await button.async_press()

        # Verify stop_inverter was called with correct parameters
        mock_hass.async_add_executor_job.assert_any_call(
            mock_coordinator.client.stop_inverter,
            "DEVICE-001",
            "plant-123",
            "SolarGoodwe",
        )

        # Verify create_task was called for delayed refresh
        assert mock_hass.create_task.called

    @pytest.mark.asyncio
    async def test_button_press_start(self, mock_coordinator):
        """Test button press for start action."""
        button = SemsPlusControlButton(
            coordinator=mock_coordinator,
            station_id="station-123",
            station_name="Test Station",
            device_sn="DEVICE-001",
            device_name="SolarGoodwe",
            plant_id="plant-123",
            action="start",
            command_delay=30,
        )

        # Mock the hass executor
        mock_hass = MagicMock()
        mock_hass.async_add_executor_job = AsyncMock(return_value={"code": "00000"})
        mock_hass.create_task = MagicMock(side_effect=mock_create_task)
        button.hass = mock_hass

        await button.async_press()

        # Verify start_inverter was called with correct parameters
        mock_hass.async_add_executor_job.assert_any_call(
            mock_coordinator.client.start_inverter,
            "DEVICE-001",
            "plant-123",
            "SolarGoodwe",
        )

        # Verify create_task was called for delayed refresh
        assert mock_hass.create_task.called

    @pytest.mark.asyncio
    async def test_button_press_restart(self, mock_coordinator):
        """Test button press for restart action."""
        button = SemsPlusControlButton(
            coordinator=mock_coordinator,
            station_id="station-123",
            station_name="Test Station",
            device_sn="DEVICE-001",
            device_name="SolarGoodwe",
            plant_id="plant-123",
            action="restart",
            command_delay=30,
        )

        # Mock the hass executor
        mock_hass = MagicMock()
        mock_hass.async_add_executor_job = AsyncMock(return_value={"code": "00000"})
        mock_hass.create_task = MagicMock(side_effect=mock_create_task)
        button.hass = mock_hass

        await button.async_press()

        # Verify restart_inverter was called with correct parameters
        mock_hass.async_add_executor_job.assert_any_call(
            mock_coordinator.client.restart_inverter,
            "DEVICE-001",
            "plant-123",
            "SolarGoodwe",
        )

        # Verify create_task was called for delayed refresh
        assert mock_hass.create_task.called

    @pytest.mark.asyncio
    async def test_button_press_error_handling(self, mock_coordinator):
        """Test error handling during button press."""
        button = SemsPlusControlButton(
            coordinator=mock_coordinator,
            station_id="station-123",
            station_name="Test Station",
            device_sn="DEVICE-001",
            device_name="SolarGoodwe",
            plant_id="plant-123",
            action="stop",
            command_delay=30,
        )

        # Mock the hass executor to raise an error
        mock_hass = MagicMock()
        mock_hass.async_add_executor_job = AsyncMock(side_effect=Exception("API Error"))
        button.hass = mock_hass

        # Verify exception is raised
        with pytest.raises(Exception, match="API Error"):
            await button.async_press()


class TestAsyncSetupEntry:
    """Test suite for async_setup_entry function."""

    @pytest.mark.asyncio
    async def test_setup_creates_buttons(self, mock_coordinator):
        """Test that setup creates button entities."""
        mock_hass = MagicMock()
        mock_hass.data = {DOMAIN: {"entry-123": mock_coordinator}}

        mock_entry = MagicMock()
        mock_entry.entry_id = "entry-123"
        mock_entry.options = {"command_delay_seconds": 30}

        async_add_entities = MagicMock()  # Not async - HA's add_entities is sync

        await async_setup_entry(mock_hass, mock_entry, async_add_entities)

        # Verify entities were added (should be 3 buttons per device)
        async_add_entities.assert_called_once()
        entities = async_add_entities.call_args[0][0]

        # Should have 3 buttons: stop, start, restart
        assert len(entities) == 3

        # Verify button actions
        actions = {entity._action for entity in entities}
        assert actions == {"stop", "start", "restart"}

    @pytest.mark.asyncio
    async def test_setup_handles_multiple_devices(self):
        """Test setup with multiple devices and stations."""
        mock_coordinator = MagicMock(spec=SemsPlusCoordinator)
        mock_coordinator.last_update_success = True
        mock_coordinator.data = {
            "stations": {
                "station-1": {
                    "name": "Station 1",
                    "info": {"id": "plant-1"},
                    "devices": [
                        {"sn": "DEVICE-001", "deviceName": "Inverter 1"},
                        {"sn": "DEVICE-002", "deviceName": "Inverter 2"},
                    ],
                },
                "station-2": {
                    "name": "Station 2",
                    "info": {"id": "plant-2"},
                    "devices": [
                        {"sn": "DEVICE-003", "deviceName": "Inverter 3"},
                    ],
                },
            }
        }

        mock_hass = MagicMock()
        mock_hass.data = {DOMAIN: {"entry-123": mock_coordinator}}

        mock_entry = MagicMock()
        mock_entry.entry_id = "entry-123"
        mock_entry.options = {"command_delay_seconds": 30}

        async_add_entities = MagicMock()  # Not async

        await async_setup_entry(mock_hass, mock_entry, async_add_entities)

        # Should have 3 buttons per device: 2 + 1 + 3 devices = 9 buttons
        entities = async_add_entities.call_args[0][0]
        assert len(entities) == 9

    @pytest.mark.asyncio
    async def test_setup_skips_devices_without_sn(self):
        """Test that setup skips devices without SN."""
        mock_coordinator = MagicMock(spec=SemsPlusCoordinator)
        mock_coordinator.last_update_success = True
        mock_coordinator.data = {
            "stations": {
                "station-1": {
                    "name": "Station 1",
                    "info": {"id": "plant-1"},
                    "devices": [
                        {"sn": "DEVICE-001", "deviceName": "Inverter 1"},
                        {"deviceName": "Inverter 2"},  # No SN
                    ],
                }
            }
        }

        mock_hass = MagicMock()
        mock_hass.data = {DOMAIN: {"entry-123": mock_coordinator}}

        mock_entry = MagicMock()
        mock_entry.entry_id = "entry-123"
        mock_entry.options = {"command_delay_seconds": 30}

        async_add_entities = MagicMock()  # Not async

        await async_setup_entry(mock_hass, mock_entry, async_add_entities)

        # Should only create buttons for the device with SN
        entities = async_add_entities.call_args[0][0]
        assert len(entities) == 3  # Only 3 buttons for 1 device
        assert all(entity._device_sn == "DEVICE-001" for entity in entities)


class TestIntegrationSetup:
    """Integration tests for setting up the component with Home Assistant."""

    @pytest.mark.asyncio
    async def test_integration_setup_with_mock_entry(self):
        """Test integration setup using MockConfigEntry (HA framework style)."""

        # Create a mock config entry
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_EMAIL: "test@example.com",
                CONF_PASSWORD: "test_password",
            },
            entry_id="entry-123",
            title="GoodWe SEMS+",
        )

        # Verify the config entry has the required attributes
        assert config_entry.domain == DOMAIN
        assert config_entry.data[CONF_EMAIL] == "test@example.com"
        assert config_entry.data[CONF_PASSWORD] == "test_password"
        assert config_entry.entry_id == "entry-123"

    @pytest.mark.asyncio
    async def test_button_entity_unique_ids(self):
        """Test that button entities have unique IDs."""
        mock_coordinator = MagicMock(spec=SemsPlusCoordinator)
        mock_coordinator.hass = MagicMock()

        # Create buttons with the same device but different actions
        button_stop = SemsPlusControlButton(
            coordinator=mock_coordinator,
            station_id="station-123",
            station_name="Test Station",
            device_sn="DEVICE-001",
            device_name="SolarGoodwe",
            plant_id="plant-123",
            action="stop",
            command_delay=30,
        )

        button_start = SemsPlusControlButton(
            coordinator=mock_coordinator,
            station_id="station-123",
            station_name="Test Station",
            device_sn="DEVICE-001",
            device_name="SolarGoodwe",
            plant_id="plant-123",
            action="start",
            command_delay=30,
        )

        button_restart = SemsPlusControlButton(
            coordinator=mock_coordinator,
            station_id="station-123",
            station_name="Test Station",
            device_sn="DEVICE-001",
            device_name="SolarGoodwe",
            plant_id="plant-123",
            action="restart",
            command_delay=30,
        )

        # Verify all unique IDs are different
        unique_ids = {
            button_stop._attr_unique_id,
            button_start._attr_unique_id,
            button_restart._attr_unique_id,
        }
        assert len(unique_ids) == 3
        assert button_stop._attr_unique_id == "DEVICE-001_stop"
        assert button_start._attr_unique_id == "DEVICE-001_start"
        assert button_restart._attr_unique_id == "DEVICE-001_restart"

    @pytest.mark.asyncio
    async def test_coordinator_entity_inheritance(self, mock_coordinator):
        """Test that button properly inherits from CoordinatorEntity."""
        button = SemsPlusControlButton(
            coordinator=mock_coordinator,
            station_id="station-123",
            station_name="Test Station",
            device_sn="DEVICE-001",
            device_name="SolarGoodwe",
            plant_id="plant-123",
            action="stop",
            command_delay=30,
        )

        # Verify coordinator is accessible
        assert button.coordinator == mock_coordinator

        # Verify entity attributes
        assert button.available is True  # CoordinatorEntity default
        assert hasattr(button, "async_press")

    def test_button_attributes(self, mock_coordinator):
        """Test button entity attributes are set correctly."""
        button = SemsPlusControlButton(
            coordinator=mock_coordinator,
            station_id="station-123",
            station_name="Test Station",
            device_sn="DEVICE-001",
            device_name="SolarGoodwe",
            plant_id="plant-123",
            action="stop",
            command_delay=30,
        )

        # Verify entity attributes
        assert button._attr_name == "SolarGoodwe Stop"
        assert button._attr_unique_id == "DEVICE-001_stop"
        assert button._attr_entity_category is not None

        # Verify restart action has device class
        button_restart = SemsPlusControlButton(
            coordinator=mock_coordinator,
            station_id="station-123",
            station_name="Test Station",
            device_sn="DEVICE-001",
            device_name="SolarGoodwe",
            plant_id="plant-123",
            action="restart",
            command_delay=30,
        )
        assert button_restart._attr_device_class is not None
