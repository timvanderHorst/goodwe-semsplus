"""Tests for the GoodWe SEMS+ API client using requests-mock."""

import sys

import pytest
import requests_mock

sys.path.insert(0, ".")

from custom_components.goodwe_semsplus.api import (
    SemsPlusAuthError,
    SemsPlusClient,
)
from custom_components.goodwe_semsplus.const import (
    CONTROL_URL,
    DEVICE_STATUS_URL,
    LOGIN_URL,
    SEMS_HOST,
    STATION_FLOW_URL,
    STATION_INFO_URL,
    STATIONS_URL,
    USER_URL,
)

MOCK_EMAIL = "test@example.com"
MOCK_PASSWORD = "test_password"
MOCK_STATION_ID = "station-123"
MOCK_PLANT_ID = "plant-123"
MOCK_SN = "DEVICE-001"
MOCK_DEVICE_NAME = "SolarGoodwe"


@pytest.fixture
def mock_requests():
    """Fixture to mock HTTP requests."""
    with requests_mock.Mocker() as m:
        yield m


class TestSemsPlusClient:
    """Test suite for SemsPlusClient with mocked requests."""

    def setup_method(self):
        """Setup common test data."""
        self.email = MOCK_EMAIL
        self.password = MOCK_PASSWORD
        self.station_id = MOCK_STATION_ID
        self.plant_id = MOCK_PLANT_ID
        self.sn = MOCK_SN
        self.device_name = MOCK_DEVICE_NAME

    def _mock_login_response(self):
        """Return a mocked login response."""
        return {
            "code": "00000",
            "msg": "success",
            "data": {
                "uid": "user-123",
                "token": "mock-token-xyz",
                "timestamp": 1234567890,
                "client": "semsPlusWeb",
            },
        }

    def _mock_user_response(self):
        """Return a mocked user info response."""
        return {
            "code": "00000",
            "msg": "success",
            "data": {
                "uid": "user-123",
                "email": MOCK_EMAIL,
                "countryCode": "NL",
            },
        }

    def _mock_stations_response(self):
        """Return a mocked stations list response."""
        return {
            "code": "00000",
            "msg": "success",
            "data": {
                "dataList": [
                    {
                        "id": self.station_id,
                        "stationId": self.station_id,
                        "stationName": "Test Station",
                        "countryCode": "NL",
                    }
                ]
            },
        }

    def _mock_station_info_response(self):
        """Return a mocked station info response."""
        return {
            "code": "00000",
            "msg": "success",
            "data": {
                "id": self.station_id,
                "stationId": self.station_id,
                "stationName": "Test Station",
                "pac": 3500,
                "eDay": 12.5,
                "eMonth": 250.0,
                "eTotal": 5000.0,
            },
        }

    def _mock_station_flow_response(self):
        """Return a mocked station flow response."""
        return {
            "code": "00000",
            "msg": "success",
            "data": {
                "pAc": 3500,
                "status": "online",
                "refreshTime": 1234567890,
            },
        }

    def _mock_device_status_response(self):
        """Return a mocked device status response."""
        return {
            "code": "00000",
            "msg": "success",
            "data": {
                "deviceDetailList": [
                    {
                        "statusDetailList": [
                            {
                                "sn": self.sn,
                                "deviceName": self.device_name,
                                "status": 1,
                                "pac": 3500,
                            }
                        ]
                    }
                ]
            },
        }

    def _mock_control_response(self):
        """Return a mocked control response."""
        return {
            "code": "00000",
            "msg": "success",
            "data": {"status": "success"},
        }

    def test_login_and_get_user(self, mock_requests):
        """Test login and get user."""
        # Mock homepage GET for session cookies
        mock_requests.get(SEMS_HOST, text="")
        # Mock login endpoint
        mock_requests.post(
            LOGIN_URL,
            json=self._mock_login_response(),
        )
        # Mock get user endpoint
        mock_requests.get(
            USER_URL,
            json=self._mock_user_response(),
        )

        client = SemsPlusClient(self.email, self.password)
        user = client.get_user()

        assert user["uid"] == "user-123"
        assert user["email"] == MOCK_EMAIL

    def test_get_stations(self, mock_requests):
        """Test getting stations list."""
        mock_requests.get(SEMS_HOST, text="")
        mock_requests.post(LOGIN_URL, json=self._mock_login_response())
        mock_requests.post(STATIONS_URL, json=self._mock_stations_response())

        client = SemsPlusClient(self.email, self.password)
        stations = client.get_stations()

        assert len(stations) == 1
        assert stations[0]["stationId"] == self.station_id

    def test_get_station_info(self, mock_requests):
        """Test getting station info."""
        mock_requests.get(SEMS_HOST, text="")
        mock_requests.post(LOGIN_URL, json=self._mock_login_response())
        mock_requests.post(
            f"{STATION_INFO_URL}?stationId={self.station_id}",
            json=self._mock_station_info_response(),
        )

        client = SemsPlusClient(self.email, self.password)
        info = client.get_station_info(self.station_id)

        assert info["stationId"] == self.station_id
        assert info["pac"] == 3500

    def test_get_station_flow(self, mock_requests):
        """Test getting station flow."""
        mock_requests.get(SEMS_HOST, text="")
        mock_requests.post(LOGIN_URL, json=self._mock_login_response())
        mock_requests.get(
            f"{STATION_FLOW_URL}?stationId={self.station_id}",
            json=self._mock_station_flow_response(),
        )

        client = SemsPlusClient(self.email, self.password)
        flow = client.get_station_flow(self.station_id)

        assert flow["pAc"] == 3500
        assert flow["status"] == "online"

    def test_get_device_status(self, mock_requests):
        """Test getting device status."""
        mock_requests.get(SEMS_HOST, text="")
        mock_requests.post(LOGIN_URL, json=self._mock_login_response())
        mock_requests.get(
            f"{DEVICE_STATUS_URL}?stationId={self.station_id}",
            json=self._mock_device_status_response(),
        )

        client = SemsPlusClient(self.email, self.password)
        status = client.get_device_status(self.station_id)

        # _request returns data.get("data", data), so we get the inner data directly
        assert status["deviceDetailList"][0]["statusDetailList"][0]["sn"] == self.sn

    def test_stop_inverter(self, mock_requests):
        """Test stopping inverter."""
        mock_requests.get(SEMS_HOST, text="")
        mock_requests.post(LOGIN_URL, json=self._mock_login_response())
        mock_requests.post(CONTROL_URL, json=self._mock_control_response())

        client = SemsPlusClient(self.email, self.password)
        result = client.stop_inverter(self.sn, self.plant_id, self.device_name)

        assert result["code"] == "00000"

    def test_start_inverter(self, mock_requests):
        """Test starting inverter."""
        mock_requests.get(SEMS_HOST, text="")
        mock_requests.post(LOGIN_URL, json=self._mock_login_response())
        mock_requests.post(CONTROL_URL, json=self._mock_control_response())

        client = SemsPlusClient(self.email, self.password)
        result = client.start_inverter(self.sn, self.plant_id, self.device_name)

        assert result["code"] == "00000"

    def test_restart_inverter(self, mock_requests):
        """Test restarting inverter."""
        mock_requests.get(SEMS_HOST, text="")
        mock_requests.post(LOGIN_URL, json=self._mock_login_response())
        mock_requests.post(CONTROL_URL, json=self._mock_control_response())

        client = SemsPlusClient(self.email, self.password)
        result = client.restart_inverter(self.sn, self.plant_id, self.device_name)

        assert result["code"] == "00000"

    def test_login_failure(self, mock_requests):
        """Test login failure."""
        mock_requests.get(SEMS_HOST, text="")
        mock_requests.post(
            LOGIN_URL,
            json={"code": "C0601", "msg": "Login failed"},
        )

        client = SemsPlusClient(self.email, self.password)

        with pytest.raises(SemsPlusAuthError, match="Login failed"):
            client.get_user()
