# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib"]
# ///

"""
Turn twenty complete years of Hong Kong lightning records into a calendar heatmap.

    uv run plot.py

The raw CSV is published by the Hong Kong Observatory. Each row records the
total number of cloud-to-ground lightning strikes over Hong Kong territory on
one day. Colour is log-transformed so quiet and extreme days remain visible.
"""

import calendar
import csv
import datetime as dt
import math
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize

FILE = "hko-daily-cloud-to-ground-lightning-all-years.csv"
PICTURE = "lightning-calendar.png"
STORM_PICTURE = "lightning-storm-eye.png"

HERE = Path(__file__).parent
DATA = HERE / "data" / FILE
OUT = HERE / "out"


def load_records(path):
    """Return complete observations as (date, count) pairs.

    The file begins with two title lines and a bilingual header. A numeric first
    field identifies a data row; the final field marks data completeness.
    """
    records = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.reader(handle):
            if len(row) < 5 or not row[0].isdigit():
                continue
            year, month, day, value, completeness = row[:5]
            if value == "***" or completeness != "C":
                continue
            date = dt.date(int(year), int(month), int(day))
            records.append((date, int(value)))
    return records


def complete_years(records):
    """Group observations and keep only full January-to-December years."""
    grouped = defaultdict(list)
    for date, count in records:
        grouped[date.year].append((date, count))

    complete = {}
    for year, observations in grouped.items():
        expected = 366 if calendar.isleap(year) else 365
        dates = {date for date, _ in observations}
        if (
            len(dates) == expected
            and dt.date(year, 1, 1) in dates
            and dt.date(year, 12, 31) in dates
        ):
            complete[year] = observations
    return complete


def calendar_position(date):
    """Align the same month and day across years on a 366-day reference year."""
    reference = dt.date(2000, date.month, date.day)
    return (reference - dt.date(2000, 1, 1)).days


def log_colour(count):
    """Compress the 0-to-14,000 range while keeping zero visibly distinct."""
    return math.log10(count + 1)


def calendar_colours():
    """The palette used by the committed first analytical plot."""
    return LinearSegmentedColormap.from_list(
        "calendar-storm",
        ["#050711", "#15102f", "#43247a", "#2366b1", "#25c7f2", "#fff7c2"],
    )


def storm_colours():
    """A restrained storm-to-flash palette shared by both pictures."""
    return LinearSegmentedColormap.from_list(
        "storm",
        ["#080812", "#241242", "#6136a6", "#287fc1", "#48d9eb", "#fff1ae"],
    )


def draw_storm_eye(years, yearly, raw_counts, peak_date, peak_count):
    """Draw the same daily records as concentric years and a seasonal corona."""
    colours = storm_colours()
    norm = Normalize(vmin=0, vmax=log_colour(15_000))
    day_angle = 2 * math.pi / 366
    inner_radius = 3.45
    ring_step = 0.47
    ring_height = 0.34

    fig, ax = plt.subplots(
        figsize=(11, 11),
        subplot_kw={"projection": "polar"},
        facecolor="#03040a",
    )
    ax.set_facecolor("#03040a")
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.grid(False)
    ax.set_axis_off()

    totals_by_day = [0] * 366
    for ring_index, year in enumerate(years):
        base = inner_radius + ring_index * ring_step
        for date, count in yearly[year]:
            day_index = calendar_position(date)
            totals_by_day[day_index] += count
            if count == 0:
                continue
            theta = (day_index + 0.5) * day_angle
            intensity = norm(log_colour(count))
            ax.bar(
                theta,
                ring_height,
                width=day_angle * 0.84,
                bottom=base,
                color=colours(intensity),
                edgecolor="none",
                alpha=0.34 + intensity * 0.66,
            )

        # A faint circle keeps a quiet year legible without pretending zero is missing.
        circle = [index * day_angle for index in range(367)]
        ax.plot(
            circle,
            [base + ring_height / 2] * len(circle),
            color="#7e88a3",
            linewidth=0.35,
            alpha=0.13,
            zorder=0,
        )

    outer_ring = inner_radius + (len(years) - 1) * ring_step + ring_height
    max_total = max(totals_by_day)
    max_corona = log_colour(max_total)
    for day_index, total in enumerate(totals_by_day):
        if total == 0:
            continue
        theta = (day_index + 0.5) * day_angle
        strength = log_colour(total) / max_corona
        length = 0.16 + 1.75 * strength**1.55
        colour = colours(norm(log_colour(min(total, 15_000))))
        line = ax.plot(
            [theta, theta],
            [outer_ring + 0.18, outer_ring + 0.18 + length],
            color=colour,
            linewidth=0.55 + 1.15 * strength,
            alpha=0.28 + 0.70 * strength,
            solid_capstyle="round",
        )[0]
        line.set_solid_capstyle("round")

    # Month boundaries and labels make the circular calendar readable.
    month_starts = [calendar_position(dt.date(2000, month, 1)) for month in range(1, 13)]
    month_names = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    month_centres = []
    for month in range(1, 13):
        first = calendar_position(dt.date(2000, month, 1))
        last = calendar_position(dt.date(2000, month, calendar.monthrange(2000, month)[1]))
        month_centres.append((first + last + 1) / 2)

    label_radius = outer_ring + 2.45
    for boundary in month_starts:
        theta = boundary * day_angle
        ax.plot(
            [theta, theta],
            [inner_radius - 0.18, outer_ring + 2.08],
            color="#d8def0",
            linewidth=0.55,
            alpha=0.13,
            zorder=0,
        )
    for name, centre in zip(month_names, month_centres):
        ax.text(
            centre * day_angle,
            label_radius,
            name,
            color="#c8d0e3",
            fontsize=8,
            fontweight="bold",
            ha="center",
            va="center",
        )

    # A few year labels show the radial direction without crowding all twenty rings.
    label_theta = math.radians(344)
    for year in [2006, 2010, 2015, 2020, 2025]:
        ring_index = years.index(year)
        radius = inner_radius + ring_index * ring_step + ring_height / 2
        ax.text(
            label_theta,
            radius,
            str(year),
            color="#929db6",
            fontsize=6.5,
            ha="center",
            va="center",
            rotation=16,
            rotation_mode="anchor",
        )

    lightning_days = sum(count > 0 for _, count in raw_counts)
    ax.text(
        0.5,
        0.545,
        "STORM\nEYE",
        transform=ax.transAxes,
        color="#f7f4ff",
        fontsize=23,
        fontweight="bold",
        ha="center",
        va="center",
        linespacing=0.88,
    )
    ax.text(
        0.5,
        0.455,
        f"HONG KONG  ·  {years[0]}–{years[-1]}\n"
        f"{lightning_days:,} LIGHTNING DAYS\n"
        f"PEAK  {peak_count:,}  ·  {peak_date:%d %b %Y}",
        transform=ax.transAxes,
        color="#8f9bb4",
        fontsize=7.5,
        ha="center",
        va="center",
        linespacing=1.7,
    )

    ax.set_ylim(0, outer_ring + 2.9)
    fig.text(
        0.5,
        0.965,
        "WHEN LIGHTNING STRIKES HONG KONG",
        color="#f4f6ff",
        fontsize=17,
        fontweight="bold",
        ha="center",
    )
    fig.text(
        0.5,
        0.94,
        "Each ring is one year · each mark is one day · the outer pulse combines all twenty years",
        color="#78849e",
        fontsize=8,
        ha="center",
    )

    scale = plt.cm.ScalarMappable(norm=norm, cmap=colours)
    colour_axis = fig.add_axes([0.31, 0.055, 0.38, 0.012])
    colourbar = fig.colorbar(scale, cax=colour_axis, orientation="horizontal")
    tick_counts = [0, 1, 10, 100, 1_000, 10_000]
    colourbar.set_ticks([log_colour(value) for value in tick_counts])
    colourbar.set_ticklabels([f"{value:,}" for value in tick_counts])
    colourbar.ax.tick_params(colors="#9aa6be", labelsize=7, length=0, pad=4)
    colourbar.outline.set_visible(False)
    colourbar.set_label(
        "daily cloud-to-ground lightning count · logarithmic colour",
        color="#7e89a1",
        fontsize=7,
        labelpad=7,
    )
    fig.text(
        0.5,
        0.018,
        "Source: Hong Kong Observatory · zero is a recorded quiet day, not missing data",
        color="#5e6980",
        fontsize=6.5,
        ha="center",
    )
    fig.subplots_adjust(left=0.025, right=0.975, top=0.91, bottom=0.10)

    target = OUT / STORM_PICTURE
    fig.savefig(target, dpi=220, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"saved out/{STORM_PICTURE}")


def main():
    records = load_records(DATA)
    yearly = complete_years(records)
    years = sorted(yearly)[-20:]
    if not years:
        raise ValueError("No complete calendar year was found in the lightning file")

    matrix = [[0.0] * 366 for _ in years]
    raw_counts = []
    for row_index, year in enumerate(years):
        for date, count in yearly[year]:
            matrix[row_index][calendar_position(date)] = log_colour(count)
            raw_counts.append((date, count))

    zero_days = sum(count == 0 for _, count in raw_counts)
    peak_date, peak_count = max(raw_counts, key=lambda item: item[1])
    print(
        f"{DATA.name}: {len(records)} complete observations; "
        f"plotting {years[0]}-{years[-1]}"
    )
    print(
        f"{zero_days:,} of {len(raw_counts):,} days had no recorded lightning; "
        f"the peak was {peak_count:,} strikes on {peak_date:%d %B %Y}"
    )

    colours = calendar_colours()
    fig, ax = plt.subplots(figsize=(14, 8), facecolor="#03050b")
    ax.set_facecolor("#03050b")
    image = ax.imshow(
        matrix,
        aspect="auto",
        interpolation="nearest",
        cmap=colours,
        vmin=0,
        vmax=math.log10(15_000 + 1),
    )

    month_starts = [calendar_position(dt.date(2000, month, 1)) for month in range(1, 13)]
    month_centres = []
    for month in range(1, 13):
        first = calendar_position(dt.date(2000, month, 1))
        last_day = calendar.monthrange(2000, month)[1]
        last = calendar_position(dt.date(2000, month, last_day))
        month_centres.append((first + last) / 2)

    for boundary in month_starts[1:]:
        ax.axvline(boundary - 0.5, color="white", alpha=0.13, linewidth=0.7)

    ax.set_xticks(month_centres)
    ax.set_xticklabels(
        ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"],
        color="#cfd8ea",
        fontsize=9,
    )
    ax.xaxis.tick_top()
    ax.tick_params(axis="x", length=0, pad=10)
    ax.set_yticks(range(len(years)))
    ax.set_yticklabels(years, color="#aebbd1", fontsize=8)
    ax.tick_params(axis="y", length=0, pad=8)

    for spine in ax.spines.values():
        spine.set_visible(False)

    ax.set_title(
        "WHEN LIGHTNING STRIKES HONG KONG",
        loc="left",
        color="#f5f7ff",
        fontsize=22,
        fontweight="bold",
        pad=48,
    )
    ax.text(
        0,
        -1.55,
        "Daily cloud-to-ground lightning count · 20 complete years · brighter means more",
        color="#8e9bb3",
        fontsize=10,
        va="bottom",
    )

    colourbar = fig.colorbar(image, ax=ax, orientation="horizontal", pad=0.09, fraction=0.035)
    tick_counts = [0, 1, 10, 100, 1_000, 10_000]
    colourbar.set_ticks([log_colour(value) for value in tick_counts])
    colourbar.set_ticklabels([f"{value:,}" for value in tick_counts])
    colourbar.ax.tick_params(colors="#aebbd1", labelsize=8, length=0)
    colourbar.outline.set_visible(False)
    colourbar.set_label(
        "lightning strikes in one day (logarithmic colour scale)",
        color="#aebbd1",
        fontsize=9,
        labelpad=8,
    )

    fig.text(
        0.09,
        0.025,
        "Source: Hong Kong Observatory · Zero is a recorded quiet day, not missing data",
        color="#748198",
        fontsize=8,
    )
    fig.subplots_adjust(left=0.09, right=0.98, top=0.82, bottom=0.16)

    OUT.mkdir(exist_ok=True)
    target = OUT / PICTURE
    fig.savefig(target, dpi=180, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"saved out/{PICTURE}")

    draw_storm_eye(years, yearly, raw_counts, peak_date, peak_count)


if __name__ == "__main__":
    main()
