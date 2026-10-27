
"""
TritonETA — Schedule Feature Engineering

Summarizes scheduled trip durations and stop-level timing.
These are schedule-derived features, not observed arrival times.
"""

import pandas as pd


def time_to_seconds(value):
    """Convert a GTFS time such as 07:30:00 or 25:15:00 to seconds."""
    hours, minutes, seconds = map(int, value.split(":"))
    return hours * 3600 + minutes * 60 + seconds


def build_features():
    """Build and save trip-level and stop-level schedule features."""

    # Load the joined GTFS dataset
    df = pd.read_csv("data/processed_schedule.csv")

    # Convert scheduled arrival times into seconds after midnight.
    # GTFS times can exceed 24:00:00 for trips after midnight.
    df["arrival_seconds"] = df["arrival_time"].apply(time_to_seconds)

    # Order stops in the sequence each trip visits them
    df = df.sort_values(["trip_id", "stop_sequence"]).copy()

    # Calculate scheduled minutes since the previous stop
    df["minutes_from_previous_stop"] = (
        df.groupby("trip_id")["arrival_seconds"].diff() / 60
    )

    # Summarize each trip
    trip_summary = (
        df.groupby(["trip_id", "route_short_name"], as_index=False)
        .agg(
            first_arrival_seconds=("arrival_seconds", "min"),
            last_arrival_seconds=("arrival_seconds", "max"),
            number_of_stops=("stop_id", "count"),
        )
    )

    trip_summary["scheduled_duration_minutes"] = (
        trip_summary["last_arrival_seconds"]
        - trip_summary["first_arrival_seconds"]
    ) / 60

    # Print summary statistics
    print("=== SCHEDULED TRIP DURATIONS ===")
    print(
        trip_summary["scheduled_duration_minutes"]
        .describe()
        .round(2)
    )

    print("\n=== AVERAGE DURATION BY ROUTE ===")
    print(
        trip_summary.groupby("route_short_name")[
            "scheduled_duration_minutes"
        ]
        .mean()
        .sort_values(ascending=False)
        .round(2)
    )

    print("\n=== EXAMPLE TRIPS ===")
    print(
        trip_summary[
            [
                "route_short_name",
                "trip_id",
                "number_of_stops",
                "scheduled_duration_minutes",
            ]
        ].head(10).to_string(index=False)
    )

    # Save the generated datasets
    trip_summary.to_csv("data/trip_summary.csv", index=False)
    df.to_csv("data/stop_features.csv", index=False)

    print("\nSaved data/trip_summary.csv")
    print("Saved data/stop_features.csv")


if __name__ == "__main__":
    build_features()
