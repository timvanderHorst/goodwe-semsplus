"""Mock SEMS+ API server for CI/CD testing."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

MOCK_STATION_ID = "aaaaaaaa-2222-3333-8888-aaaaaaaaaaaa"
MOCK_SN = "9000KACR128R0000"
MOCK_USER_ID = "test-user-id-1234"
MOCK_TOKEN = "mock-token-abc123"

# Mutable state for inverter status (allows tests to verify control commands)
_inverter_status = {"status": 5}


def reset_state():
    """Reset mock state between tests."""
    _inverter_status["status"] = 5


def _success(data):
    return {"code": "00000", "data": data}


class MockSemsPlusHandler(BaseHTTPRequestHandler):
    """Handler that simulates the SEMS+ gateway API."""

    def log_message(self, format, *args):
        """Suppress request logging in tests."""
        pass

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length:
            return json.loads(self.rfile.read(length))
        return {}

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        # Homepage (cookie retrieval)
        if path == "/" or path == "":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body>SEMS+</body></html>")
            return

        # User info
        if path.endswith("/user/get-user"):
            self._send_json(
                _success(
                    {
                        "info": {
                            "id": MOCK_USER_ID,
                            "username": "testuser",
                            "email": "test@example.com",
                            "userType": 1,
                        }
                    }
                )
            )
            return

        # Station flow
        if path.endswith("/stations/flow"):
            station_id = params.get("stationId", [MOCK_STATION_ID])[0]
            self._send_json(
                _success(
                    {
                        "id": station_id,
                        "name": "Test Station",
                        "status": "1",
                        "isGoodweInverter": True,
                        "pSystem": 2.5,
                        "pAc": 2.5,
                        "consumFlag": False,
                        "refreshTime": "2026-05-05T12:00:00.000",
                    }
                )
            )
            return

        # Device status
        if path.endswith("/device/all-status"):
            self._send_json(
                _success(
                    {
                        "total": 1,
                        "deviceDetailList": [
                            {
                                "deviceType": "INVERTER",
                                "total": 1,
                                "statusDetailList": [
                                    {
                                        "status": _inverter_status["status"],
                                        "total": 1,
                                        "snList": [MOCK_SN],
                                        "isHemsMap": {MOCK_SN: False},
                                        "detailMap": {
                                            MOCK_SN: {
                                                "sn": MOCK_SN,
                                                "name": "TestInverter",
                                                "deviceType": "INVERTER",
                                                "status": _inverter_status["status"],
                                            }
                                        },
                                    }
                                ],
                            }
                        ],
                    }
                )
            )
            return

        self._send_json({"code": "404", "msg": "Not found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        body = self._read_body()

        # Login
        if path.endswith("/auth/cross-login"):
            account = body.get("account", "")
            if not account:
                self._send_json({"code": "C0601", "msg": "Invalid credentials"})
                return
            self._send_json(
                _success(
                    {
                        "uid": MOCK_USER_ID,
                        "timestamp": 1714900000000,
                        "token": MOCK_TOKEN,
                        "client": "semsPlusWeb",
                        "version": "",
                        "language": "en",
                    }
                )
            )
            return

        # Stations list
        if path.endswith("/simple-query"):
            self._send_json(
                _success(
                    {
                        "dataList": [
                            {
                                "id": MOCK_STATION_ID,
                                "stationName": "Test Station",
                                "status": "1",
                                "pac": 2500,
                                "eDay": 12.5,
                                "eMonth": 350.0,
                                "eTotal": 45000.0,
                            }
                        ],
                        "total": 1,
                    }
                )
            )
            return

        # Station info
        if path.endswith("/basic/info"):
            self._send_json(
                _success(
                    {
                        "stationId": MOCK_STATION_ID,
                        "name": "Test Station",
                        "status": "1",
                        "pac": 2500,
                        "eDay": 12.5,
                        "eMonth": 350.0,
                        "eTotal": 45000.0,
                        "powerStationType": "1",
                    }
                )
            )
            return

        # Inverter control
        if path.endswith("/setDeviceFunctionParameters"):
            address_map = body.get("addressMap", {})
            command = address_map.get("80017", 0)
            # Apply state change
            if command == 2:
                _inverter_status["status"] = 3  # stopped
            elif command == 3:
                _inverter_status["status"] = 5  # online
            elif command == 1:
                _inverter_status["status"] = 5  # restart -> online
            self._send_json({"code": "00000", "description": "success"})
            return

        self._send_json({"code": "404", "msg": "Not found"}, 404)


class MockSemsPlusServer:
    """Context manager for the mock server."""

    def __init__(self, host="127.0.0.1", port=0):
        self._host = host
        self._port = port
        self._server = None
        self._thread = None

    @property
    def base_url(self) -> str:
        return f"http://{self._host}:{self._server.server_address[1]}"

    def start(self):
        reset_state()
        self._server = HTTPServer((self._host, self._port), MockSemsPlusHandler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self):
        if self._server:
            self._server.shutdown()
            self._thread.join(timeout=5)

    def __enter__(self):
        return self.start()

    def __exit__(self, *args):
        self.stop()


if __name__ == "__main__":
    # Run standalone for manual testing
    server = MockSemsPlusServer(port=8765).start()
    print(f"Mock SEMS+ server running at {server.base_url}")
    print("Press Ctrl+C to stop")
    try:
        server._thread.join()
    except KeyboardInterrupt:
        server.stop()
