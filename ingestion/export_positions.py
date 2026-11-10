"""
Export vehicle positions from the local poller's SQLite database to
daily Parquet files under data/raw/positions/.

The SQLite file is the poller's working store and stays out of git;
the Parquet files are the shared, versioned raw layer that dbt reads.
Re-running is safe: each day's file is rewritten from scratch.

Usage:
    python ingestion/export_positions.py [--db data/raw_positions.db]
"""

import argparse
import sqlite3
from pathlib import Path

import pandas as pd

OUT_DIR = Path("data/raw/positions")

COLUMNS = ["route_id", "vehicle_id", "lat", "lon", "vehicle_timestamp", "ingested_at"]


def export(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(f"SELECT {', '.join(COLUMNS)} FROM raw_positions", conn)
    conn.close()

    df["ingested_at"] = pd.to_datetime(df["ingested_at"], utc=True)
    df["vehicle_timestamp"] = df["vehicle_timestamp"].astype("int64")
    df["route_id"] = df["route_id"].astype("string")
    df["vehicle_id"] = df["vehicle_id"].astype("string")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for day, part in df.groupby(df["ingested_at"].dt.strftime("%Y-%m-%d")):
        path = OUT_DIR / f"positions_{day}_sqlite.parquet"
        part.to_parquet(path, index=False, compression="zstd")
        print(f"{path}: {len(part):,} rows")

    print(f"Exported {len(df):,} rows across {df['ingested_at'].dt.date.nunique()} days")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/raw_positions.db")
    export(parser.parse_args().db)
