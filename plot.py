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
from matplotlib.colors import LinearSegmentedColormap

FILE = "hko-daily-cloud-to-ground-lightning-all-years.csv"
PICTURE = "lightning-calendar.png"

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

    colours = LinearSegmentedColormap.from_list(
        "storm",
        ["#050711", "#15102f", "#43247a", "#2366b1", "#25c7f2", "#fff7c2"],
    )
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
    print(f"saved out/{PICTURE}")


if __name__ == "__main__":
    main()
