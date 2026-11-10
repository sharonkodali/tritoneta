"""
Poll the GTFS-Realtime feed for a fixed window and write the results to a
single Parquet file under data/raw/positions/.

Built for scheduled GitHub Actions runs, which can't keep a long-running
process alive: each run polls for --minutes, then exits. Output uses the
same schema as export_positions.py, so dbt reads both the same way.

Usage:
    python ingestion/collect_positions.py --minutes 25
"""

import argparse
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from poller import POLL_INTERVAL_SECONDS, fetch_positions

OUT_DIR = Path("data/raw/positions")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("collector")


def collect(minutes: float) -> Path | None:
    started = datetime.now(timezone.utc)
    deadline = time.monotonic() + minutes * 60
    rows, polls, failures = [], 0, 0

    while time.monotonic() < deadline:
        polls += 1
        try:
            batch = fetch_positions()
            ingested_at = datetime.now(timezone.utc)
            for row in batch:
                row["ingested_at"] = ingested_at
            rows.extend(batch)
        except Exception as e:  # keep polling through transient feed errors
            failures += 1
            logger.warning(f"Poll {polls} failed: {e}")
        time.sleep(POLL_INTERVAL_SECONDS)

    logger.info(f"{polls} polls, {failures} failed, {len(rows)} rows")
    if not rows:
        logger.info("No vehicles reported (outside service hours?); nothing written")
        return None

    df = pd.DataFrame(rows)
    df["route_id"] = df["route_id"].astype("string")
    df["vehicle_id"] = df["vehicle_id"].astype("string")
    df["vehicle_timestamp"] = df["vehicle_timestamp"].astype("int64")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"positions_{started:%Y-%m-%d_%H%M}_actions.parquet"
    df.to_parquet(path, index=False, compression="zstd")
    logger.info(f"Wrote {path}")
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", type=float, default=25)
    collect(parser.parse_args().minutes)
