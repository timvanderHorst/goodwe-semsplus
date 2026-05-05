import base64
import hashlib
import json
import logging
import time

import requests

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

SEMS_HOST = "https://semsplus.goodwe.com"
GATEWAY_HOST = "https://eu-gateway.semsportal.com"
LOGIN_URL = f"{SEMS_HOST}/web/sems/sems-user/api/v1/auth/cross-login"
CONTROL_URL = (
    f"{GATEWAY_HOST}/web/sems/sems-remote/api/v1/address/remote/setDeviceFunctionParameters"
)
USER_URL = f"{GATEWAY_HOST}/web/sems/sems-user/api/v1/user/get-user"

CHROME_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/147.0.0.0 Safari/537.36"
)


def make_pwd(plaintext: str) -> str:
    """pwd = base64( MD5-hex(password) )."""
    md5_hex = hashlib.md5(plaintext.encode()).hexdigest()
    return base64.b64encode(md5_hex.encode()).decode()


def encode_signature(token_json: str) -> str:
    """X-Signature = base64( sha256(timestamp@uid@token) + '@' + timestamp )."""
    if not token_json:
        return ""
    try:
        data = json.loads(token_json)
    except (json.JSONDecodeError, TypeError):
        data = {}
    ts = str(int(time.time() * 1000))
    uid = data.get("uid", "")
    token = data.get("token", "")
    hash_input = f"{ts}@{uid}@{token}"
    sig_hash = hashlib.sha256(hash_input.encode()).hexdigest()
    return base64.b64encode(f"{sig_hash}@{ts}".encode()).decode()


EMPTY_TOKEN = json.dumps(
    {
        "uid": "",
        "timestamp": 0,
        "token": "",
        "client": "semsPlusWeb",
        "version": "",
        "language": "en",
    },
    separators=(",", ":"),
)


def _gateway_headers(token_json: str) -> dict:
    return {
        "token": token_json,
        "X-Signature": encode_signature(token_json),
        "Access-Control-Allow-Origin": "*",
        "neutral": "0",
        "currentLang": "en",
    }


def login(email: str, password: str):
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": CHROME_UA,
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Origin": SEMS_HOST,
            "Referer": f"{SEMS_HOST}/",
        }
    )

    log.info("Visiting homepage to retrieve session cookies")
    session.get(SEMS_HOST, timeout=30)

    payload = {
        "account": email,
        "pwd": make_pwd(password),
        "agreement": 1,
        "isChinese": False,
        "isLocal": False,
    }

    log.info("Logging in as %s", email)
    r = session.post(LOGIN_URL, json=payload, headers=_gateway_headers(EMPTY_TOKEN), timeout=15)
    r.raise_for_status()
    resp = r.json()
    log.debug("Login response: %s", resp)

    code = resp.get("code", resp.get("status", -1))
    if code not in (0, 200, "00000", "200"):
        raise RuntimeError(f"Login failed (code {code}): {resp.get('msg', resp)}")

    data = resp.get("data", {})
    data["client"] = "semsPlusWeb"
    token_json = json.dumps(data, separators=(",", ":"))
    session.headers.update({"token": token_json})

    return session, data


def get_user(session):
    token_json = session.headers.get("token", "")
    r = session.get(USER_URL, headers=_gateway_headers(token_json), timeout=15)
    r.raise_for_status()
    return r.json()


def get_stations(session):
    token_json = session.headers.get("token", "")
    r = session.post(
        f"{GATEWAY_HOST}/web/sems/sems-plant/api/stations/simple-query",
        headers=_gateway_headers(token_json),
        json={"pageIndex": 1, "pageSize": 20},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def get_station_info(session, station_id: str):
    token_json = session.headers.get("token", "")
    r = session.post(
        f"{GATEWAY_HOST}/web/sems/sems-plant/api/portal/stations/basic/info?stationId={station_id}",
        headers=_gateway_headers(token_json),
        json={},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def get_station_flow(session, station_id: str):
    """Real-time power flow: pAc (kW), pSystem, status, refreshTime."""
    token_json = session.headers.get("token", "")
    r = session.get(
        f"{GATEWAY_HOST}/web/sems/sems-plant/api/stations/flow?stationId={station_id}",
        headers=_gateway_headers(token_json),
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def get_device_status(session, station_id: str):
    """All devices status (inverters, meters, etc.)."""
    token_json = session.headers.get("token", "")
    r = session.get(
        f"{GATEWAY_HOST}/web/sems/sems-plant/api/stations/device/all-status?stationId={station_id}",
        headers=_gateway_headers(token_json),
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def _control_inverter(
    session, sn: str, plant_id: str, device_name: str, address_value: int, status_setting: str
):
    """Send a remote control command to the inverter."""
    token_json = session.headers.get("token", "")
    r = session.post(
        CONTROL_URL,
        headers=_gateway_headers(token_json),
        json={
            "sn": sn,
            "addressMap": {"80017": address_value},
            "addrFuncMap": {"80017": "1990397626802589697"},
            "controlItemLogs": {"status_setting": status_setting},
            "waitingForDevice": True,
            "plantId": plant_id,
            "deviceName": device_name,
        },
        timeout=120,
    )
    r.raise_for_status()
    return r.json()


def stop_inverter(session, sn: str, plant_id: str, device_name: str):
    return _control_inverter(session, sn, plant_id, device_name, 2, "stop")


def start_inverter(session, sn: str, plant_id: str, device_name: str):
    return _control_inverter(session, sn, plant_id, device_name, 3, "start_up")


def restart_inverter(session, sn: str, plant_id: str, device_name: str):
    return _control_inverter(session, sn, plant_id, device_name, 1, "restart")


if __name__ == "__main__":
    import os

    username = os.getenv("SEMS_EMAIL")
    password = os.getenv("SEMS_PASSWORD")
    if not username or not password:
        log.error("Please set SEMS_EMAIL and SEMS_PASSWORD environment variables")
        exit(1)

    session, data = login(username, password)
    log.info("Login successful, received data: %s", data)

    user_info = get_user(session)
    log.info("User info: %s", user_info)

    stations = get_stations(session)
    log.info("Stations: %s", stations)

    station_id = stations["data"]["dataList"][0]["id"]

    info = get_station_info(session, station_id)
    log.info("Station info: %s", info)

    flow = get_station_flow(session, station_id)
    log.info("Station flow: %s", flow)

    devices = get_device_status(session, station_id)
    log.info("Device status: %s", devices)
