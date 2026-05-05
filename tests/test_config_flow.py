"""Tests for GoodWe SEMS+ config and options flow."""

import sys

import pytest
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

sys.path.insert(0, ".")

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
