import pandas as pd
"""
TritonETA — GTFS Schedule Exploration

Purpose:
    Explore UCSD shuttle schedule data and combine routes,
    trips, stop times, and stop locations into one dataset.

Input:
    data/raw/gtfs/

Output:
    data/processed_schedule.csv

Note:
    This is scheduled transit data, not live arrival data.
"""
# Load the three GTFS tables we need.
stops = pd.read_csv("data/raw/gtfs/stops.txt")
trips = pd.read_csv("data/raw/gtfs/trips.txt")
stop_times = pd.read_csv("data/raw/gtfs/stop_times.txt")
routes = pd.read_csv("data/raw/gtfs/routes.txt")

# Attach route information to each trip.
trips_with_routes = trips.merge(
    routes[["route_id", "route_short_name", "route_long_name"]],
    on="route_id",
    how="left",
)

# Attach trip information to each scheduled stop visit.
schedule = stop_times.merge(
    trips_with_routes,
    on="trip_id",
    how="left",
)

# Attach each stop's name and coordinates.
schedule = schedule.merge(
    stops[["stop_id", "stop_name", "stop_lat", "stop_lon"]],
    on="stop_id",
    how="left",
)

# Sort stops in the order each shuttle is scheduled to visit them.
schedule = schedule.sort_values(["trip_id", "stop_sequence"])

print("Dataset shape:", schedule.shape)
print("\nColumns:")
print(schedule.columns.tolist())

print("\nSample scheduled arrivals:")
print(
    schedule[
        [
            "route_short_name",
            "trip_id",
            "trip_headsign",
            "stop_sequence",
            "stop_name",
            "arrival_time",
        ]
    ].head(15).to_string(index=False)
)

print("\nMissing stop names:", schedule["stop_name"].isna().sum())
print("Unique trips:", schedule["trip_id"].nunique())
print("Unique stops:", schedule["stop_id"].nunique())

# Save the combined schedule for later exploration.
schedule.to_csv("data/processed_schedule.csv", index=False)
print("\nSaved to data/processed_schedule.csv")
