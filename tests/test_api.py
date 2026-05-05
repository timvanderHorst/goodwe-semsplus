"""Tests for the GoodWe SEMS+ API client using the mock server."""

import sys
from unittest.mock import patch

sys.path.insert(0, ".")

from custom_components.goodwe_semsplus.api import SemsPlusAuthError, SemsPlusClient
from tests.mock_server import MOCK_SN, MOCK_STATION_ID, MockSemsPlusServer, reset_state


class TestSemsPlusClient:
    """Test suite for SemsPlusClient against mock server."""

    def setup_method(self):
        self.server = MockSemsPlusServer().start()
        base = self.server.base_url
        # Patch URLs to point to mock server
        self._patches = [
            patch("custom_components.goodwe_semsplus.api.SEMS_HOST", base),
            patch(
                "custom_components.goodwe_semsplus.api.LOGIN_URL",
                f"{base}/web/sems/sems-user/api/v1/auth/cross-login",
            ),
            patch(
                "custom_components.goodwe_semsplus.api.USER_URL",
                f"{base}/web/sems/sems-user/api/v1/user/get-user",
            ),
            patch(
                "custom_components.goodwe_semsplus.api.STATIONS_URL",
                f"{base}/web/sems/sems-plant/api/stations/simple-query",
            ),
            patch(
                "custom_components.goodwe_semsplus.api.STATION_INFO_URL",
                f"{base}/web/sems/sems-plant/api/portal/stations/basic/info",
            ),
            patch(
                "custom_components.goodwe_semsplus.api.STATION_FLOW_URL",
                f"{base}/web/sems/sems-plant/api/stations/flow",
            ),
            patch(
                "custom_components.goodwe_semsplus.api.DEVICE_STATUS_URL",
                f"{base}/web/sems/sems-plant/api/stations/device/all-status",
            ),
            patch(
                "custom_components.goodwe_semsplus.api.CONTROL_URL",
                f"{base}/web/sems/sems-remote/api/v1/address/remote/setDeviceFunctionParameters",
            ),
        ]
        for p in self._patches:
            p.start()
        reset_state()

    def teardown_method(self):
        for p in self._patches:
            p.stop()
        self.server.stop()

    def _make_client(self):
        return SemsPlusClient("test@example.com", "testpass")

    def test_login_and_get_user(self):
        client = self._make_client()
        user = client.get_user()
        assert user["info"]["username"] == "testuser"
        assert user["info"]["email"] == "test@example.com"

    def test_get_stations(self):
        client = self._make_client()
        stations = client.get_stations()
        assert len(stations) == 1
        assert stations[0]["id"] == MOCK_STATION_ID
        assert stations[0]["stationName"] == "Test Station"

    def test_get_station_info(self):
        client = self._make_client()
        info = client.get_station_info(MOCK_STATION_ID)
        assert info["stationId"] == MOCK_STATION_ID
        assert info["pac"] == 2500
        assert info["eDay"] == 12.5

    def test_get_station_flow(self):
        client = self._make_client()
        flow = client.get_station_flow(MOCK_STATION_ID)
        assert flow["pAc"] == 2.5
        assert flow["status"] == "1"

    def test_get_device_status(self):
        client = self._make_client()
        devices = client.get_device_status(MOCK_STATION_ID)
        assert devices["total"] == 1
        status_list = devices["deviceDetailList"][0]["statusDetailList"]
        assert status_list[0]["status"] == 5
        assert MOCK_SN in status_list[0]["snList"]

    def test_stop_inverter(self):
        client = self._make_client()
        result = client.stop_inverter(MOCK_SN, MOCK_STATION_ID, "TestInverter")
        assert result["code"] == "00000"
        # Verify state changed
        devices = client.get_device_status(MOCK_STATION_ID)
        status = devices["deviceDetailList"][0]["statusDetailList"][0]["status"]
        assert status == 3

    def test_start_inverter(self):
        client = self._make_client()
        # First stop it
        client.stop_inverter(MOCK_SN, MOCK_STATION_ID, "TestInverter")
        # Then start it
        result = client.start_inverter(MOCK_SN, MOCK_STATION_ID, "TestInverter")
        assert result["code"] == "00000"
        # Verify state changed back
        devices = client.get_device_status(MOCK_STATION_ID)
        status = devices["deviceDetailList"][0]["statusDetailList"][0]["status"]
        assert status == 5

    def test_restart_inverter(self):
        client = self._make_client()
        result = client.restart_inverter(MOCK_SN, MOCK_STATION_ID, "TestInverter")
        assert result["code"] == "00000"

    def test_login_failure(self):
        """Test that empty account triggers auth error."""
        client = SemsPlusClient("", "password")
        try:
            client.get_user()
            assert False, "Should have raised SemsPlusAuthError"
        except SemsPlusAuthError:
            pass
