"""Shared configuration, read once from the environment (and .env if present).

Every path is resolved against the repo root so scripts behave the same whether
they are run from the root, from a subdirectory, or from a GitHub Action.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(REPO_ROOT / ".env")


def _path(env_var: str, default: str) -> Path:
    raw = os.environ.get(env_var, default)
    p = Path(raw)
    return p if p.is_absolute() else REPO_ROOT / p


@dataclass(frozen=True)
class Config:
    api_key: str
    gtfs_static_url: str
    vehicle_positions_url: str
    trip_updates_url: str
    auth_style: str
    auth_param: str
    data_dir: Path
    duckdb_path: Path
    model_path: Path

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def gtfs_static_dir(self) -> Path:
        return self.data_dir / "gtfs_static"

    def authorize(self, url: str) -> tuple[str, dict[str, str]]:
        """Return (url, headers) with the API key applied in the configured style."""
        if not self.api_key:
            return url, {}
        if self.auth_style == "header":
            return url, {"Authorization": self.api_key}
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}{self.auth_param}={self.api_key}", {}


def load_config() -> Config:
    return Config(
        api_key=os.environ.get("MTS_API_KEY", ""),
        gtfs_static_url=os.environ.get(
            "GTFS_STATIC_URL",
            "https://www.sdmts.com/google_transit_files/google_transit.zip",
        ),
        vehicle_positions_url=os.environ.get(
            "GTFS_RT_VEHICLE_POSITIONS_URL",
            "https://realtime.sdmts.com/api/api/gtfs_realtime/vehicle_positions",
        ),
        trip_updates_url=os.environ.get(
            "GTFS_RT_TRIP_UPDATES_URL",
            "https://realtime.sdmts.com/api/api/gtfs_realtime/trip_updates",
        ),
        auth_style=os.environ.get("GTFS_RT_AUTH_STYLE", "query"),
        auth_param=os.environ.get("GTFS_RT_AUTH_PARAM", "key"),
        data_dir=_path("DATA_DIR", "data"),
        duckdb_path=_path("DUCKDB_PATH", "data/warehouse.duckdb"),
        model_path=_path("MODEL_PATH", "ml/artifacts/delay_model.joblib"),
    )
