"""Tests for GoodWe SEMS+ config and options flow."""

import sys
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

sys.path.insert(0, ".")

from custom_components.goodwe_semsplus.api import SemsPlusAuthError
from custom_components.goodwe_semsplus.config_flow import (
    GoodWeSemsPlusConfigFlow,
    GoodWeSemsPlusOptionsFlow,
)
from custom_components.goodwe_semsplus.const import (
    CONF_COMMAND_DELAY,
    DEFAULT_COMMAND_DELAY,
    DOMAIN,
)


class TestOptionsFlow:
    """Tests for options flow behavior."""

    def test_async_get_options_flow_accepts_config_entry(self):
        """Ensure options flow can be created with a config entry argument."""
        entry = MockConfigEntry(domain=DOMAIN, data={}, options={})

        flow = GoodWeSemsPlusConfigFlow.async_get_options_flow(entry)

        assert isinstance(flow, GoodWeSemsPlusOptionsFlow)
        assert flow.config_entry is entry

    @pytest.mark.asyncio
    async def test_options_flow_shows_form_with_default_delay(self):
        """Ensure options form opens with default command delay when unset."""
        entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
        flow = GoodWeSemsPlusOptionsFlow(entry)

        result = await flow.async_step_init(user_input=None)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "init"

    @pytest.mark.asyncio
    async def test_options_flow_saves_delay(self):
        """Ensure options flow saves command delay to options entry."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={},
            options={CONF_COMMAND_DELAY: DEFAULT_COMMAND_DELAY},
        )
        flow = GoodWeSemsPlusOptionsFlow(entry)

        result = await flow.async_step_init(user_input={CONF_COMMAND_DELAY: 120})

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"] == {CONF_COMMAND_DELAY: 120}

    @pytest.mark.asyncio
    async def test_options_flow_step_user_with_input_creates_entry(self):
        """Ensure async_step_user saves provided options."""
        entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
        flow = GoodWeSemsPlusOptionsFlow(entry)

        result = await flow.async_step_user(user_input={CONF_COMMAND_DELAY: 60})

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"] == {CONF_COMMAND_DELAY: 60}

    @pytest.mark.asyncio
    async def test_options_flow_step_user_without_input_shows_form(self):
        """Ensure async_step_user delegates to init form when no input."""
        entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
        flow = GoodWeSemsPlusOptionsFlow(entry)

        result = await flow.async_step_user(user_input=None)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "init"


class TestConfigFlow:
    """Tests for initial config flow user step."""

    @pytest.mark.asyncio
    async def test_config_flow_shows_form_without_input(self):
        """Ensure user step renders form when no input is given."""
        flow = GoodWeSemsPlusConfigFlow()

        result = await flow.async_step_user(user_input=None)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"

    @pytest.mark.asyncio
    async def test_config_flow_user_success_creates_entry(self):
        """Ensure valid credentials create a config entry."""
        flow = GoodWeSemsPlusConfigFlow()
        flow.hass = MagicMock()
        flow.hass.async_add_executor_job = AsyncMock(return_value={"uid": "user-1"})
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = MagicMock()

        user_input = {
            CONF_EMAIL: "test@example.com",
            CONF_PASSWORD: "secret",
        }

        result = await flow.async_step_user(user_input=user_input)

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "SEMS+ (test@example.com)"
        assert result["data"] == user_input
        flow.hass.async_add_executor_job.assert_awaited_once()
        flow.async_set_unique_id.assert_awaited_once_with("test@example.com")
        flow._abort_if_unique_id_configured.assert_called_once()

    @pytest.mark.asyncio
    async def test_config_flow_user_invalid_auth_returns_error(self):
        """Ensure auth errors return invalid_auth form error."""
        flow = GoodWeSemsPlusConfigFlow()
        flow.hass = MagicMock()
        flow.hass.async_add_executor_job = AsyncMock(
            side_effect=SemsPlusAuthError("bad credentials")
        )

        result = await flow.async_step_user(
            user_input={
                CONF_EMAIL: "test@example.com",
                CONF_PASSWORD: "wrong",
            }
        )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {"base": "invalid_auth"}

    @pytest.mark.asyncio
    async def test_config_flow_user_unknown_error_returns_error(self):
        """Ensure unexpected errors return unknown form error."""
        flow = GoodWeSemsPlusConfigFlow()
        flow.hass = MagicMock()
        flow.hass.async_add_executor_job = AsyncMock(side_effect=Exception("boom"))

        result = await flow.async_step_user(
            user_input={
                CONF_EMAIL: "test@example.com",
                CONF_PASSWORD: "secret",
            }
        )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {"base": "unknown"}
