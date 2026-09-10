from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

app = FastAPI(title="TritonETA API", version="0.1.0")

# Enable CORS so frontend (running on port 5173 or 3000) can make requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Position(BaseModel):
    latitude: float
    longitude: float
    bearing: Optional[float] = None
    speed: Optional[float] = None


class Vehicle(BaseModel):
    id: str
    label: str


class ShuttlePosition(BaseModel):
    id: str
    vehicle: Vehicle
    route_id: str
    route_name: str
    position: Position
    timestamp: str
    status: str


MOCK_SHUTTLE_POSITIONS: List[ShuttlePosition] = [
    ShuttlePosition(
        id="pos-101",
        vehicle=Vehicle(id="shuttle-1", label="Inside Loop #1"),
        route_id="route-inside-loop",
        route_name="Inside Loop",
        position=Position(latitude=32.8810, longitude=-117.2360, bearing=180.0, speed=12.5),
        timestamp=datetime.utcnow().isoformat() + "Z",
        status="On Time",
    ),
    ShuttlePosition(
        id="pos-102",
        vehicle=Vehicle(id="shuttle-2", label="Outside Loop #1"),
        route_id="route-outside-loop",
        route_name="Outside Loop",
        position=Position(latitude=32.8765, longitude=-117.2320, bearing=90.0, speed=8.0),
        timestamp=datetime.utcnow().isoformat() + "Z",
        status="Delayed 2 mins",
    ),
    ShuttlePosition(
        id="pos-103",
        vehicle=Vehicle(id="shuttle-3", label="Regents Express #1"),
        route_id="route-regents",
        route_name="East Campus / Regents",
        position=Position(latitude=32.8835, longitude=-117.2280, bearing=270.0, speed=15.0),
        timestamp=datetime.utcnow().isoformat() + "Z",
        status="On Time",
    ),
    ShuttlePosition(
        id="pos-104",
        vehicle=Vehicle(id="shuttle-4", label="SIO Shuttle #1"),
        route_id="route-sio",
        route_name="Scripps Institution of Oceanography",
        position=Position(latitude=32.8680, longitude=-117.2500, bearing=45.0, speed=10.0),
        timestamp=datetime.utcnow().isoformat() + "Z",
        status="On Time",
    ),
]


@app.get("/")
def read_root():
    return {"message": "TritonETA Backend API"}


@app.get("/positions", response_model=List[ShuttlePosition])
def get_shuttle_positions():
    """Return mock live shuttle positions across UCSD campus."""
    return MOCK_SHUTTLE_POSITIONS