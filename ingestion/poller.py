import time
import sqlite3
import logging

import requests
from google.transit import gtfs_realtime_pb2

FEED_URL = "https://api.us.sparelabs.com/v1/fixedRoute/public/21c87bba-e136-41bc-ba9a-191bdb3e08e4/gtfs-rt/vehicle-positions.pb"
DB_PATH = "data/raw_positions.db"
POLL_INTERVAL_SECONDS = 20  # within the 15-30s range from the issue

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("poller")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS raw_positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            route_id TEXT,
            vehicle_id TEXT,
            lat REAL,
            lon REAL,
            vehicle_timestamp INTEGER,
            ingested_at TEXT DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()
    return conn


def poll_once(conn):
    response = requests.get(FEED_URL, timeout=10)
    response.raise_for_status()

    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(response.content)

    rows_written = 0
    for entity in feed.entity:
        if not entity.HasField("vehicle"):
            continue
        vehicle = entity.vehicle
        route_id = vehicle.trip.route_id if vehicle.HasField("trip") else None
        vehicle_id = vehicle.vehicle.id if vehicle.HasField("vehicle") else None
        lat = vehicle.position.latitude if vehicle.HasField("position") else None
        lon = vehicle.position.longitude if vehicle.HasField("position") else None
        vehicle_timestamp = vehicle.timestamp if vehicle.HasField("timestamp") else None

        conn.execute(
            "INSERT INTO raw_positions (route_id, vehicle_id, lat, lon, vehicle_timestamp) VALUES (?, ?, ?, ?, ?)",
            (route_id, vehicle_id, lat, lon, vehicle_timestamp),
        )
        rows_written += 1

    conn.commit()
    logger.info(f"Polled feed: wrote {rows_written} rows")


def main():
    conn = init_db()
    logger.info("Starting GTFS-RT poller")
    while True:
        try:
            poll_once(conn)
        except Exception as e:
            logger.error(f"Poll failed: {e}")
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()