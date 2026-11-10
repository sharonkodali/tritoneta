"""
Plot schedule adherence by route from the dbt warehouse.

Reads marts.fct_stop_delays and writes docs/img/on_time_by_route.png:
one 100% bar per route split into early / on time / late.

Usage (after `cd dbt && dbt build --profiles-dir .`):
    python analysis/plot_route_reliability.py
"""

from pathlib import Path

import duckdb
import matplotlib.pyplot as plt

DB = Path("data/warehouse.duckdb")
OUT = Path("docs/img/on_time_by_route.png")

# Diverging scale: early (cool) <- on time (neutral) -> late (warm).
COLORS = {"early": "#2a78d6", "on_time": "#c3c2b7", "late": "#e34948"}
LABELS = {"early": "Early (>1 min)", "on_time": "On time", "late": "Late (>5 min)"}
SURFACE, INK, INK_2 = "#fcfcfb", "#0b0b0b", "#52514e"


def load():
    con = duckdb.connect(str(DB), read_only=True)
    df = con.sql(
        """
        with names as (
            select distinct route_id, route_short_name, route_long_name
            from marts.agg_route_stop_performance
        )
        select
            n.route_long_name || ' (' || n.route_short_name || ')' as route,
            count(*) as visits,
            avg((punctuality = 'early')::int) as early,
            avg((punctuality = 'on_time')::int) as on_time,
            avg((punctuality = 'late')::int) as late
        from marts.fct_stop_delays d
        join names n using (route_id)
        group by all
        order by on_time
        """
    ).df()
    span = con.sql("select min(service_date), max(service_date), count(*) from marts.fct_stop_delays").fetchall()[0]
    return df, span


def main():
    df, (start, end, total) = load()

    fig, ax = plt.subplots(figsize=(9, 4.2), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    left = [0.0] * len(df)
    for key in ["early", "on_time", "late"]:
        widths = df[key].tolist()
        ax.barh(
            df["route"], widths, left=left, height=0.62,
            color=COLORS[key], edgecolor=SURFACE, linewidth=2, label=LABELS[key],
        )
        for i, (l, w) in enumerate(zip(left, widths)):
            if w >= 0.07:  # label only segments wide enough to hold text
                text_color = "white" if key != "on_time" else INK
                ax.text(l + w / 2, i, f"{w:.0%}", ha="center", va="center", fontsize=8.5, color=text_color)
        left = [l + w for l, w in zip(left, widths)]

    for i, n in enumerate(df["visits"]):
        ax.text(1.01, i, f"{n:,} visits", va="center", fontsize=8, color=INK_2)

    ax.set_xlim(0, 1)
    ax.set_xticks([])
    ax.tick_params(axis="y", length=0, labelsize=9, colors=INK)
    for side in ["top", "right", "bottom", "left"]:
        ax.spines[side].set_visible(False)

    ax.set_title(
        "UCSD shuttle schedule adherence by route",
        loc="left", fontsize=12, color=INK, pad=28, fontweight="bold",
    )
    ax.text(
        0, 1.06,
        f"{total:,} GPS-derived stop visits matched to the published schedule, {start:%b %d} – {end:%b %d, %Y}",
        transform=ax.transAxes, fontsize=8.5, color=INK_2,
    )
    ax.legend(
        loc="upper center", bbox_to_anchor=(0.5, -0.02), ncol=3, frameon=False,
        fontsize=8.5, labelcolor=INK_2, handlelength=1.2,
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, bbox_inches="tight", facecolor=SURFACE)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
