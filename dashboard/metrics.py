"""Metrics computed from the aggregated data. Every metric is a ratio of sums."""

import calendar

import pandas as pd

MIN_ARRIVALS = 20_000  # arrivals in the period shown, for the map and the rankings (analysis, 5.3)
COLOR_CAP_PERCENTILE = 95  # map colour scale ends at this percentile of all airport-years shown
FOCUS_AIRPORTS = ["LPPT", "LPPR", "LPFR"]  # Lisbon, Porto, Faro
ATFM_CALCULATION_CHANGE = pd.Timestamp("2016-04-04")  # first date of ATFM_VERSION v2 (analysis, 3.7)
LOW_TRAFFIC_YEARS = [2020, 2021]  # traffic drop (analysis, 5.1)

SUMS = ["arrivals", "delay_min", "arr_with_atfm_delay", "arr_with_atfm_delay_over_15"]


# Add ATFM delay minutes per arrival and the share of arrivals with ATFM delay (%).
def add_ratios(df):
    df = df.copy()
    df["delay_min_per_arrival"] = df["delay_min"] / df["arrivals"]
    df["arr_with_atfm_delay_pct"] = df["arr_with_atfm_delay"] / df["arrivals"] * 100
    return df


# Years whose data covers 1 January to 31 December.
def complete_years(coverage):
    first, last = coverage["first"], coverage["last"]
    full = (first.dt.month == 1) & (first.dt.day == 1) & (last.dt.month == 12) & (last.dt.day == 31)
    return coverage.index[full].tolist()


def is_complete(coverage, year):
    return year in complete_years(coverage)


# Months with data in a year.
def year_months(monthly, year):
    return sorted(monthly.loc[monthly["year"] == year, "month"].unique().tolist())


# 'Jan-Oct' for a run of months, 'Mar' for one month.
def months_label(months):
    first, last = calendar.month_abbr[months[0]], calendar.month_abbr[months[-1]]
    return first if first == last else f"{first}–{last}"


# How a year is named in the app: '2025', or 'Jan–Oct 2026' for a partial year.
def period_label(coverage, monthly, year):
    if is_complete(coverage, year):
        return str(year)
    return f"{months_label(year_months(monthly, year))} {year}"


# Europe-wide sums and ratios of one year, limited to some months.
def europe_totals(monthly, year, months):
    rows = monthly[(monthly["year"] == year) & monthly["month"].isin(months)]
    return add_ratios(rows[SUMS].sum().to_frame().T).iloc[0]


# Europe-wide KPIs of a year and of the previous year on the same months (None if no previous year).
def europe_kpis(monthly, coverage, year):
    months = year_months(monthly, year)
    previous = year - 1
    has_previous = set(months) <= set(year_months(monthly, previous))
    return {
        "current": europe_totals(monthly, year, months),
        "previous": europe_totals(monthly, previous, months) if has_previous else None,
        "label": period_label(coverage, monthly, year),
        "previous_label": (str(previous) if is_complete(coverage, year)
                           else f"{months_label(months)} {previous}") if has_previous else None,
    }


# Europe-wide sums and ratios for every month, with the month's first day as date.
def europe_by_month(monthly):
    out = monthly.groupby(["year", "month"], as_index=False)[SUMS].sum()
    out["date"] = pd.to_datetime({"year": out["year"], "month": out["month"], "day": 1})
    return add_ratios(out)


# Sums and ratios per airport for one year (all months with data).
def airport_year_totals(monthly, year):
    rows = monthly[monthly["year"] == year]
    return add_ratios(rows.groupby("icao")[SUMS].sum())


# Airports with at least MIN_ARRIVALS arrivals in one year, with their labels and coordinates.
def busy_airports(monthly, airports, year):
    totals = airport_year_totals(monthly, year)
    return totals[totals["arrivals"] >= MIN_ARRIVALS].join(airports).sort_values("arrivals", ascending=False)


# Airports on the map for one year: busy airports with known coordinates.
def map_airports(monthly, airports, year):
    return busy_airports(monthly, airports, year).dropna(subset=["lat", "lon"])


# Bounds [west, south, east, north] of every airport the map can show in any year, so the map
# frames the same area whatever the year.
def map_bounds(monthly, airports):
    shown = pd.concat([map_airports(monthly, airports, year) for year in sorted(monthly["year"].unique())])
    return [float(shown["lon"].min()), float(shown["lat"].min()), float(shown["lon"].max()), float(shown["lat"].max())]


# Upper end of the map colour scale: a percentile of ATFM delay per arrival over every
# airport-year with at least MIN_ARRIVALS arrivals, so the colours mean the same in every year.
def color_cap(monthly, airports):
    values = pd.concat([busy_airports(monthly, airports, year)["delay_min_per_arrival"]
                        for year in sorted(monthly["year"].unique())])
    return float(values.quantile(COLOR_CAP_PERCENTILE / 100))
