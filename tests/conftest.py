"""Pytest configuration for GoodWe SEMS+ tests."""

import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import mock_aiohttp_client


@pytest.fixture
def hass_client(hass):
    """Fixture for HTTP client."""
    return mock_aiohttp_client(hass)
