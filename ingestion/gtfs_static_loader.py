"""One-time (well, weekly) load of the GTFS static schedule into DuckDB.

The realtime feeds are all IDs — route_id "510", stop_id "99042". The static
feed is what turns those into "Blue Line" and "UTC Transit Center", and it also
carries the published timetable that realtime delays are measured against.

Re-run this whenever MTS publishes a new schedule (they do so every few months,
and mid-quarter service changes are common around the UCSD calendar).

Usage:
    python -m ingestion.gtfs_static_loader              # download + load
    python -m ingestion.gtfs_static_loader --skip-download   # reuse local zip
"""

from __future__ import annotations

import argparse
import logging
import sys
import zipfile
from pathlib import Path

import duckdb
import requests

from ingestion.config import Config, load_config

log = logging.getLogger("gtfs_static")

REQUEST_TIMEOUT = 120

# GTFS files we load, and whether the spec requires them. Optional files that are
# absent are skipped with a note rather than failing the run.
GTFS_TABLES: dict[str, bool] = {
    "agency": True,
    "routes": True,
    "trips": True,
    "stops": True,
    "stop_times": True,
    "calendar": False,
    "calendar_dates": False,
    "shapes": False,
    "feed_info": False,
}

# Columns that look numeric but must stay text: stop "0123" is not 123, and
# losing the leading zero silently breaks every join against the realtime feed.
FORCE_VARCHAR = [
    "route_id",
    "trip_id",
    "stop_id",
    "shape_id",
    "service_id",
    "agency_id",
    "parent_station",
    "block_id",
    "route_short_name",
    "zone_id",
]


def download_zip(cfg: Config) -> Path:
    cfg.gtfs_static_dir.mkdir(parents=True, exist_ok=True)
    dest = cfg.gtfs_static_dir / "google_transit.zip"

    log.info("downloading %s", cfg.gtfs_static_url)
    url, headers = cfg.authorize(cfg.gtfs_static_url)
    with requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT, stream=True) as resp:
        resp.raise_for_status()
        with dest.open("wb") as fh:
            for chunk in resp.iter_content(chunk_size=1 << 16):
                fh.write(chunk)

    log.info("saved %.1f MB -> %s", dest.stat().st_size / 1e6, dest)
    return dest


def extract_zip(zip_path: Path, cfg: Config) -> Path:
    out_dir = cfg.gtfs_static_dir / "extracted"
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(out_dir)
    log.info("extracted %d files -> %s", len(list(out_dir.glob("*.txt"))), out_dir)
    return out_dir


def load_to_duckdb(txt_dir: Path, cfg: Config) -> None:
    cfg.duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(cfg.duckdb_path))
    try:
        con.execute("CREATE SCHEMA IF NOT EXISTS gtfs")
        types = ", ".join(f"'{c}': 'VARCHAR'" for c in FORCE_VARCHAR)

        for name, required in GTFS_TABLES.items():
            src = txt_dir / f"{name}.txt"
            if not src.exists():
                level = log.error if required else log.info
                level("%s.txt %s", name, "missing (required!)" if required else "not in feed, skipping")
                if required:
                    raise FileNotFoundError(src)
                continue

            con.execute(f"DROP TABLE IF EXISTS gtfs.{name}")
            con.execute(
                f"""
                CREATE TABLE gtfs.{name} AS
                SELECT * FROM read_csv(
                    ?,
                    header = true,
                    all_varchar = false,
                    types = {{{types}}},
                    ignore_errors = false
                )
                """,
                [str(src)],
            )
            (rows,) = con.execute(f"SELECT count(*) FROM gtfs.{name}").fetchone()
            log.info("gtfs.%-14s %8d rows", name, rows)
    finally:
        con.close()

    log.info("loaded into %s", cfg.duckdb_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Load GTFS static feed into DuckDB.")
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Use the already-downloaded zip in data/gtfs_static/.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s | %(message)s"
    )
    cfg = load_config()

    zip_path = cfg.gtfs_static_dir / "google_transit.zip"
    if args.skip_download:
        if not zip_path.exists():
            log.error("--skip-download given but %s does not exist", zip_path)
            return 1
    else:
        zip_path = download_zip(cfg)

    load_to_duckdb(extract_zip(zip_path, cfg), cfg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
