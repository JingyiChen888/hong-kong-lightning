# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib", "pillow"]
# ///

"""Animate the Hong Kong lightning calendar one complete year at a time.

    uv run animate.py

The GIF keeps the geometry and colour scale fixed while adding one annual ring
per frame. The outer pulse therefore grows from one year's observations into
the combined seasonal pattern for 2006–2025.
"""

import calendar
import datetime as dt
import math

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.colors import Normalize

from plot import (
    DATA,
    OUT,
    calendar_position,
    complete_years,
    load_records,
    log_colour,
    storm_colours,
)

ANIMATION = "lightning-storm-eye.gif"
NUMBER_OF_YEARS = 20
REFERENCE_YEAR = 2000  # A leap year gives every calendar date its own position.


def month_positions():
    """Return month boundaries, centres and short labels on a 366-day circle."""
    boundaries = []
    centres = []
    labels = []
    for month in range(1, 13):
        first = calendar_position(dt.date(REFERENCE_YEAR, month, 1))
        last_day = calendar.monthrange(REFERENCE_YEAR, month)[1]
        last = calendar_position(dt.date(REFERENCE_YEAR, month, last_day))
        boundaries.append(first)
        centres.append((first + last + 1) / 2)
        labels.append(calendar.month_abbr[month].upper())
    return boundaries, centres, labels


def prepare_year(year, observations, colours, norm):
    """Prepare polar bar positions and colours for one year of observations."""
    day_angle = 2 * math.pi / 366
    non_zero = [(date, count) for date, count in observations if count > 0]
    angles = [(calendar_position(date) + 0.5) * day_angle for date, _ in non_zero]
    values = [count for _, count in non_zero]
    rgba = []
    for count in values:
        intensity = norm(log_colour(count))
        red, green, blue, _ = colours(intensity)
        rgba.append((red, green, blue, 0.34 + intensity * 0.66))
    return {
        "year": year,
        "angles": angles,
        "values": values,
        "colours": rgba,
        "observations": observations,
    }


def draw_frame(ax, frame_index, years, prepared, colours, norm):
    """Draw all rings up to the year represented by one animation frame."""
    ax.clear()
    ax.set_facecolor("#03040a")
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.grid(False)
    ax.set_axis_off()

    day_angle = 2 * math.pi / 366
    inner_radius = 3.45
    ring_step = 0.47
    ring_height = 0.34
    outer_ring = inner_radius + (len(years) - 1) * ring_step + ring_height
    active_years = prepared[: frame_index + 1]
    current_year = years[frame_index]

    # All ring guides remain fixed, so the growing animation does not jump.
    circle = [index * day_angle for index in range(367)]
    for ring_index in range(len(years)):
        radius = inner_radius + ring_index * ring_step + ring_height / 2
        is_active = ring_index <= frame_index
        ax.plot(
            circle,
            [radius] * len(circle),
            color="#8791aa",
            linewidth=0.35,
            alpha=0.15 if is_active else 0.045,
            zorder=0,
        )

    # Each new frame keeps the earlier annual rings and illuminates one more.
    for ring_index, year_data in enumerate(active_years):
        if not year_data["angles"]:
            continue
        base = inner_radius + ring_index * ring_step
        ax.bar(
            year_data["angles"],
            [ring_height] * len(year_data["angles"]),
            width=day_angle * 0.84,
            bottom=base,
            color=year_data["colours"],
            edgecolor="none",
        )

    # The corona is the accumulated seasonal signal up to the current frame.
    totals_by_day = [0] * 366
    observed_counts = []
    for year_data in active_years:
        for date, count in year_data["observations"]:
            totals_by_day[calendar_position(date)] += count
            observed_counts.append((date, count))

    max_total = max(totals_by_day)
    max_corona = log_colour(max_total)
    corona_angles = []
    corona_bottoms = []
    corona_tops = []
    corona_colours = []
    corona_widths = []
    for day_index, total in enumerate(totals_by_day):
        if total == 0:
            continue
        strength = log_colour(total) / max_corona
        start = outer_ring + 0.18
        corona_angles.append((day_index + 0.5) * day_angle)
        corona_bottoms.append(start)
        corona_tops.append(start + 0.16 + 1.75 * strength**1.55)
        colour_value = norm(log_colour(min(total, 15_000)))
        red, green, blue, _ = colours(colour_value)
        corona_colours.append((red, green, blue, 0.28 + 0.70 * strength))
        corona_widths.append(0.55 + 1.15 * strength)
    ax.vlines(
        corona_angles,
        corona_bottoms,
        corona_tops,
        colors=corona_colours,
        linewidths=corona_widths,
    )

    boundaries, centres, labels = month_positions()
    for boundary in boundaries:
        theta = boundary * day_angle
        ax.plot(
            [theta, theta],
            [inner_radius - 0.18, outer_ring + 2.08],
            color="#d8def0",
            linewidth=0.55,
            alpha=0.13,
            zorder=0,
        )
    label_radius = outer_ring + 2.45
    for label, centre in zip(labels, centres):
        ax.text(
            centre * day_angle,
            label_radius,
            label,
            color="#c8d0e3",
            fontsize=8,
            fontweight="bold",
            ha="center",
            va="center",
        )

    # Label a small set of active rings to show time moving outwards.
    label_theta = math.radians(344)
    for labelled_year in [2006, 2010, 2015, 2020, 2025]:
        if labelled_year > current_year or labelled_year not in years:
            continue
        ring_index = years.index(labelled_year)
        radius = inner_radius + ring_index * ring_step + ring_height / 2
        ax.text(
            label_theta,
            radius,
            str(labelled_year),
            color="#929db6",
            fontsize=6.5,
            ha="center",
            va="center",
            rotation=16,
            rotation_mode="anchor",
        )

    lightning_days = sum(count > 0 for _, count in observed_counts)
    peak_date, peak_count = max(observed_counts, key=lambda item: item[1])
    ax.text(
        0.5,
        0.555,
        str(current_year),
        transform=ax.transAxes,
        color="#f7f4ff",
        fontsize=26,
        fontweight="bold",
        ha="center",
        va="center",
    )
    ax.text(
        0.5,
        0.475,
        f"{frame_index + 1:02d} / {len(years):02d} YEARS\n"
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
    return []


def main():
    records = load_records(DATA)
    yearly = complete_years(records)
    years = sorted(yearly)[-NUMBER_OF_YEARS:]
    if len(years) != NUMBER_OF_YEARS:
        raise ValueError(f"Expected {NUMBER_OF_YEARS} complete calendar years")

    colours = storm_colours()
    norm = Normalize(vmin=0, vmax=log_colour(15_000))
    prepared = [prepare_year(year, yearly[year], colours, norm) for year in years]

    fig, ax = plt.subplots(
        figsize=(9, 9),
        subplot_kw={"projection": "polar"},
        facecolor="#03040a",
    )
    fig.text(
        0.5,
        0.965,
        "WHEN LIGHTNING STRIKES HONG KONG",
        color="#f4f6ff",
        fontsize=15,
        fontweight="bold",
        ha="center",
    )
    fig.text(
        0.5,
        0.94,
        "Each frame adds one year · daily records move clockwise · the pulse accumulates outside",
        color="#78849e",
        fontsize=7.5,
        ha="center",
    )

    scale = plt.cm.ScalarMappable(norm=norm, cmap=colours)
    colour_axis = fig.add_axes([0.31, 0.078, 0.38, 0.012])
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
    fig.subplots_adjust(left=0.025, right=0.975, top=0.91, bottom=0.13)

    # Repeat the final frame so viewers have time to read the completed picture.
    frame_sequence = list(range(len(years))) + [len(years) - 1] * 5
    animation = FuncAnimation(
        fig,
        lambda frame: draw_frame(ax, frame, years, prepared, colours, norm),
        frames=frame_sequence,
        interval=480,
        blit=False,
        repeat=True,
    )
    OUT.mkdir(exist_ok=True)
    target = OUT / ANIMATION
    animation.save(target, writer=PillowWriter(fps=2), dpi=100)
    plt.close(fig)
    print(f"saved out/{ANIMATION}")


if __name__ == "__main__":
    main()
