"""Poll the MTS GTFS-Realtime feeds and append a parquet snapshot per run.

Two feeds are captured:

  vehicle_positions — where each bus/trolley is right now (drives the map)
  trip_updates      — the agency's own arrival predictions, which carry a
                      `delay` field per stop. That delay is the label the ML
                      model learns to predict, so it is the more valuable of
                      the two feeds even though it is less fun to look at.

Output is hive-partitioned parquet under data/raw/, e.g.

  data/raw/vehicle_positions/dt=2026-09-01/vp_20260901T204500Z.parquet

which DuckDB and dbt can read directly with read_parquet(..., hive_partitioning=1).

Usage:
    python -m ingestion.poller                  # poll both feeds once
    python -m ingestion.poller --feed positions # just one feed
    python -m ingestion.poller --loop 30        # poll every 30s until Ctrl-C
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from google.transit import gtfs_realtime_pb2

from ingestion.config import Config, load_config

log = logging.getLogger("poller")

REQUEST_TIMEOUT = 30
USER_AGENT = "tritoneta/0.1 (github.com/sharonkodali/tritoneta)"


def fetch_feed(cfg: Config, url: str) -> gtfs_realtime_pb2.FeedMessage:
    """GET a protobuf feed and parse it, with a clear error if it isn't protobuf."""
    url, headers = cfg.authorize(url)
    headers["User-Agent"] = USER_AGENT

    resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()

    feed = gtfs_realtime_pb2.FeedMessage()
    try:
        feed.ParseFromString(resp.content)
    except Exception as exc:  # noqa: BLE001 - we want the body in the message
        preview = resp.content[:200].decode("utf-8", errors="replace")
        raise RuntimeError(
            "Feed did not parse as GTFS-Realtime protobuf. "
            "Usually this means a bad/missing API key or a moved endpoint. "
            f"First 200 bytes of the response: {preview!r}"
        ) from exc
    return feed


def vehicle_positions_to_frame(feed: gtfs_realtime_pb2.FeedMessage) -> pd.DataFrame:
    rows = []
    for entity in feed.entity:
        if not entity.HasField("vehicle"):
            continue
        v = entity.vehicle
        rows.append(
            {
                "entity_id": entity.id,
                "vehicle_id": v.vehicle.id or None,
                "vehicle_label": v.vehicle.label or None,
                "trip_id": v.trip.trip_id or None,
                "route_id": v.trip.route_id or None,
                "direction_id": v.trip.direction_id if v.trip.HasField("direction_id") else None,
                "start_date": v.trip.start_date or None,
                "latitude": v.position.latitude if v.HasField("position") else None,
                "longitude": v.position.longitude if v.HasField("position") else None,
                "bearing": v.position.bearing if v.HasField("position") else None,
                "speed": v.position.speed if v.HasField("position") else None,
                "stop_id": v.stop_id or None,
                "current_stop_sequence": (
                    v.current_stop_sequence if v.HasField("current_stop_sequence") else None
                ),
                "current_status": v.current_status if v.HasField("current_status") else None,
                "occupancy_status": (
                    v.occupancy_status if v.HasField("occupancy_status") else None
                ),
                "vehicle_timestamp": v.timestamp or None,
            }
        )
    return pd.DataFrame(rows)


def trip_updates_to_frame(feed: gtfs_realtime_pb2.FeedMessage) -> pd.DataFrame:
    """Flatten to one row per (trip, stop) prediction — the grain we model on."""
    rows = []
    for entity in feed.entity:
        if not entity.HasField("trip_update"):
            continue
        tu = entity.trip_update
        for stu in tu.stop_time_update:
            arrival = stu.arrival if stu.HasField("arrival") else None
            departure = stu.departure if stu.HasField("departure") else None
            rows.append(
                {
                    "entity_id": entity.id,
                    "trip_id": tu.trip.trip_id or None,
                    "route_id": tu.trip.route_id or None,
                    "direction_id": (
                        tu.trip.direction_id if tu.trip.HasField("direction_id") else None
                    ),
                    "start_date": tu.trip.start_date or None,
                    "schedule_relationship": (
                        tu.trip.schedule_relationship
                        if tu.trip.HasField("schedule_relationship")
                        else None
                    ),
                    "vehicle_id": tu.vehicle.id or None,
                    "stop_id": stu.stop_id or None,
                    "stop_sequence": (
                        stu.stop_sequence if stu.HasField("stop_sequence") else None
                    ),
                    "arrival_time": arrival.time if arrival and arrival.HasField("time") else None,
                    "arrival_delay": (
                        arrival.delay if arrival and arrival.HasField("delay") else None
                    ),
                    "departure_time": (
                        departure.time if departure and departure.HasField("time") else None
                    ),
                    "departure_delay": (
                        departure.delay if departure and departure.HasField("delay") else None
                    ),
                    "trip_update_timestamp": tu.timestamp or None,
                }
            )
    return pd.DataFrame(rows)


def write_snapshot(df: pd.DataFrame, cfg: Config, dataset: str, polled_at: datetime) -> Path | None:
    """Write one partitioned parquet file; return its path (None if the feed was empty)."""
    if df.empty:
        log.warning("%s: feed returned 0 rows, nothing written", dataset)
        return None

    df = df.copy()
    df["polled_at"] = polled_at

    partition = cfg.raw_dir / dataset / f"dt={polled_at:%Y-%m-%d}"
    partition.mkdir(parents=True, exist_ok=True)

    prefix = "vp" if dataset == "vehicle_positions" else "tu"
    out = partition / f"{prefix}_{polled_at:%Y%m%dT%H%M%SZ}.parquet"
    df.to_parquet(out, index=False, compression="snappy")

    log.info("%s: wrote %d rows -> %s", dataset, len(df), out.relative_to(cfg.data_dir.parent))
    return out


FEEDS = {
    "positions": ("vehicle_positions", "vehicle_positions_url", vehicle_positions_to_frame),
    "updates": ("trip_updates", "trip_updates_url", trip_updates_to_frame),
}


def poll_once(cfg: Config, feeds: list[str]) -> int:
    """Poll the named feeds. Returns the number that failed."""
    polled_at = datetime.now(timezone.utc)
    failures = 0

    for feed_key in feeds:
        dataset, url_attr, to_frame = FEEDS[feed_key]
        try:
            feed = fetch_feed(cfg, getattr(cfg, url_attr))
            write_snapshot(to_frame(feed), cfg, dataset, polled_at)
        except Exception as exc:  # noqa: BLE001 - one bad feed shouldn't kill the other
            failures += 1
            log.error("%s: poll failed: %s", dataset, exc)

    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Poll MTS GTFS-Realtime feeds.")
    parser.add_argument(
        "--feed",
        choices=[*FEEDS, "both"],
        default="both",
        help="Which feed to poll (default: both).",
    )
    parser.add_argument(
        "--loop",
        type=int,
        metavar="SECONDS",
        help="Poll repeatedly at this interval instead of once. Ctrl-C to stop.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s | %(message)s"
    )

    cfg = load_config()
    feeds = list(FEEDS) if args.feed == "both" else [args.feed]

    if not args.loop:
        return 1 if poll_once(cfg, feeds) == len(feeds) else 0

    log.info("polling %s every %ss — Ctrl-C to stop", ", ".join(feeds), args.loop)
    try:
        while True:
            poll_once(cfg, feeds)
            time.sleep(args.loop)
    except KeyboardInterrupt:
        log.info("stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
