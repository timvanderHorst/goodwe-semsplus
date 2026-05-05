"""Test client for the GoodWe SEMS+ custom component API."""

import json
import logging
import os
import sys

sys.path.insert(0, ".")
from custom_components.goodwe_semsplus.api import SemsPlusClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def main():
    email = os.getenv("SEMS_EMAIL")
    password = os.getenv("SEMS_PASSWORD")
    if not email or not password:
        log.error("Please set SEMS_EMAIL and SEMS_PASSWORD environment variables")
        return

    log.info("Creating client for %s", email)
    client = SemsPlusClient(email, password)

    # User info
    user = client.get_user()
    log.info("User: %s", json.dumps(user, indent=2, default=str)[:200])

    # Stations
    stations = client.get_stations()
    log.info("Found %d station(s)", len(stations))
    for s in stations:
        station_id = s.get("id") or s.get("stationId", "")
        name = s.get("stationName", station_id)
        log.info("  Station: %s (%s)", name, station_id)

        # Station info
        info = client.get_station_info(station_id)
        log.info("  Info: %s", json.dumps(info, indent=2, default=str)[:300])

        # Power flow
        flow = client.get_station_flow(station_id)
        log.info("  Flow: %s", json.dumps(flow, indent=2, default=str)[:300])

        # Device status
        devices = client.get_device_status(station_id)
        log.info("  Devices: %s", json.dumps(devices, indent=2, default=str)[:500])


if __name__ == "__main__":
    main()
