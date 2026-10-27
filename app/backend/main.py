
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Create the FastAPI application
app = FastAPI(
    title="TritonETA API",
    description="Backend API for UCSD shuttle routes, vehicles, and ETA predictions",
    version="0.1.0",
)

# Allow requests from the local React + Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


# Check whether the API is running
@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "tritoneta-api",
    }


# Return available shuttle routes
@app.get("/api/routes")
def get_routes():
    # TODO: Replace sample data with real UCSD GTFS routes
    return [
        {
            "route_id": "demo-1",
            "route_name": "Demo Shuttle",
        }
    ]


# Return current shuttle locations
@app.get("/api/vehicles")
def get_vehicles():
    # TODO: Connect to the real-time transit feed
    return []


# Return predicted arrival times
@app.get("/api/predictions")
def get_predictions():
    # TODO: Connect the ETA prediction model
    return {
        "status": "not_ready",
        "message": "ETA predictions have not been implemented yet.",
        "predictions": [],
    }
