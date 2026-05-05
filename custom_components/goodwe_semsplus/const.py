"""Constants for the GoodWe SEMS+ integration."""

DOMAIN = "goodwe_semsplus"

CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_COMMAND_DELAY = "command_delay_seconds"

DEFAULT_COMMAND_DELAY = 30  # 30 seconds

SEMS_HOST = "https://semsplus.goodwe.com"
GATEWAY_HOST = "https://eu-gateway.semsportal.com"
LOGIN_URL = f"{SEMS_HOST}/web/sems/sems-user/api/v1/auth/cross-login"

API_BASE = f"{GATEWAY_HOST}/web/sems"
USER_URL = f"{API_BASE}/sems-user/api/v1/user/get-user"
STATIONS_URL = f"{API_BASE}/sems-plant/api/stations/simple-query"
STATION_INFO_URL = f"{API_BASE}/sems-plant/api/portal/stations/basic/info"
STATION_FLOW_URL = f"{API_BASE}/sems-plant/api/stations/flow"
DEVICE_STATUS_URL = f"{API_BASE}/sems-plant/api/stations/device/all-status"
CONTROL_URL = f"{API_BASE}/sems-remote/api/v1/address/remote/setDeviceFunctionParameters"

SCAN_INTERVAL_SECONDS = 30

DEVICE_STATUS_MAP = {
    0: "offline",
    1: "online",
    2: "alarm",
    3: "stopped",
    5: "online",
    -1: "disconnected",
}
