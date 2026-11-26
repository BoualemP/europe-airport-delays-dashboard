"""Metrics computed from the aggregated data. Every metric is a ratio of sums (peer medians aside)."""

import calendar

import numpy as np
import pandas as pd

from dashboard.data import GROUP_ORDER

MIN_ARRIVALS = 20_000  # arrivals in the period shown, for the map and the rankings (analysis, 5.3)
PEERS_EACH_SIDE = 5  # traffic peers: 5 airports just above and 5 just below in arrivals (analysis, 5.5)
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


# Sums and ratios of one year, limited to some months, for all airports or for one airport.
def period_totals(monthly, year, months, icao=None):
    rows = monthly[(monthly["year"] == year) & monthly["month"].isin(months)]
    if icao is not None:
        rows = rows[rows["icao"] == icao]
    return add_ratios(rows[SUMS].sum().to_frame().T).iloc[0]


# The previous year on the same months as 'year' (every month for a complete year): its months and its
# label ('2024', or 'Jan–Oct 2025'), or None when the data does not have those months.
def previous_period(monthly, coverage, year):
    months = year_months(monthly, year)
    if not set(months) <= set(year_months(monthly, year - 1)):
        return None
    return months, str(year - 1) if is_complete(coverage, year) else f"{months_label(months)} {year - 1}"


# KPIs of a year and of the previous year on the same months, Europe-wide or for one airport.
# The months come from the whole dataset, so an airport is compared on the same months as Europe.
# 'previous' is None when the data has no previous year, or when the airport had no arrivals in it;
# 'previous_note' then says which of the two it is.
def period_kpis(monthly, coverage, year, icao=None):
    months = year_months(monthly, year)
    before, label, note = None, None, "No previous year in the data"
    if (previous := previous_period(monthly, coverage, year)) is not None:
        label = previous[1]
        before, note = period_totals(monthly, year - 1, months, icao), None
        if before["arrivals"] == 0:
            before, note = None, f"No arrivals reported in {label}"
    return {
        "current": period_totals(monthly, year, months, icao),
        "previous": before,
        "label": period_label(coverage, monthly, year),
        "previous_label": label,
        "previous_note": note,
    }


# Europe-wide sums and ratios for every month, with the month's first day as date.
def europe_by_month(monthly):
    out = monthly.groupby(["year", "month"], as_index=False)[SUMS].sum()
    out["date"] = pd.to_datetime({"year": out["year"], "month": out["month"], "day": 1})
    return add_ratios(out)


# Sums and ratios per airport for one year (all months with data, or only 'months').
def airport_year_totals(monthly, year, months=None):
    rows = monthly[monthly["year"] == year]
    if months is not None:
        rows = rows[rows["month"].isin(months)]
    return add_ratios(rows.groupby("icao")[SUMS].sum())


# Airports with at least MIN_ARRIVALS arrivals in one year (or in some of its months), with their labels
# and coordinates.
def busy_airports(monthly, airports, year, months=None):
    totals = airport_year_totals(monthly, year, months)
    return totals[totals["arrivals"] >= MIN_ARRIVALS].join(airports).sort_values("arrivals", ascending=False)


# Airports on the map for one year: busy airports with known coordinates.
def map_airports(monthly, airports, year):
    return busy_airports(monthly, airports, year).dropna(subset=["lat", "lon"])


# Bounds [west, south, east, north] of every airport the map can show in any year, so the map
# frames the same area whatever the year.
def map_bounds(monthly, airports):
    shown = pd.concat([map_airports(monthly, airports, year) for year in sorted(monthly["year"].unique())])
    return [float(shown["lon"].min()), float(shown["lat"].min()), float(shown["lon"].max()), float(shown["lat"].max())]


# ---------------------------------------------------------------- airport explorer

# Airports with at least MIN_ARRIVALS arrivals in at least one year, sorted by name.
def explorer_airports(monthly, airports):
    busy = set()
    for year in sorted(monthly["year"].unique()):
        totals = airport_year_totals(monthly, year)
        busy |= set(totals.index[totals["arrivals"] >= MIN_ARRIVALS])
    return airports.loc[sorted(busy)].sort_values("name")


# Busy airports of one year (or of some of its months) ranked by one measure: ATFM delay minutes per
# arrival or the share of arrivals with ATFM delay (1 = highest; ties share a rank). Airports with no ATFM
# delay at all are counted but not ranked (rank missing), as in the analysis (5.3): they would all tie last.
def delay_ranking(monthly, airports, year, measure="delay_min_per_arrival", months=None):
    ranked = busy_airports(monthly, airports, year, months).copy()
    values = ranked[measure].where(ranked["delay_min"] > 0)
    ranked["rank"] = values.rank(ascending=False, method="min").astype("Int64")
    return ranked.sort_values(["rank", "arrivals"], ascending=[True, False], na_position="last")


# Ranks in the previous year on the same months (the 'Rank in 2024' column) and that period's label, or
# None when the data does not have those months. Airports below the minimum or without ATFM delay that
# year are missing or have no rank.
def previous_ranks(monthly, airports, coverage, year, measure="delay_min_per_arrival"):
    previous = previous_period(monthly, coverage, year)
    if previous is None:
        return None
    months, label = previous
    return delay_ranking(monthly, airports, year - 1, measure, months)["rank"], label


# Traffic peers of an airport: the n airports just above and the n just below it when all airports
# of one year are ordered by arrivals. Empty when the airport has no arrivals that year.
def traffic_peers(monthly, year, icao, n_each=PEERS_EACH_SIDE):
    totals = airport_year_totals(monthly, year)
    order = totals[totals["arrivals"] > 0].sort_values("arrivals", ascending=False).index.tolist()
    if icao not in order:
        return []
    position = order.index(icao)
    return order[max(0, position - n_each):position] + order[position + 1:position + 1 + n_each]


# One airport and its peers in one year: arrivals, ratios and rank (missing below MIN_ARRIVALS),
# plus the median of the peers.
def peer_table(monthly, airports, icao, peers, year):
    rows = [icao, *peers]
    totals = airport_year_totals(monthly, year).reindex(rows)
    ranks = delay_ranking(monthly, airports, year)["rank"].reindex(rows).astype("Int64")
    out = pd.DataFrame({
        "name": airports["name"].reindex(rows), "country": airports["country"].reindex(rows),
        "arrivals": totals["arrivals"], "delay_min_per_arrival": totals["delay_min_per_arrival"],
        "arr_with_atfm_delay_pct": totals["arr_with_atfm_delay_pct"], "rank": ranks,
    })
    median = out.loc[peers, ["arrivals", "delay_min_per_arrival", "arr_with_atfm_delay_pct"]].median()
    return out, median


# ATFM delay per arrival by year for one airport and the median of its fixed peers.
def airport_vs_peers_by_year(monthly, icao, peers, years):
    rows = []
    for year in years:
        values = airport_year_totals(monthly, year)["delay_min_per_arrival"]
        peer_values = values.reindex(peers).dropna()
        rows.append({"year": year, "airport": values.get(icao, np.nan),
                     "peer_median": peer_values.median() if len(peer_values) else np.nan,
                     "peers_with_data": len(peer_values)})
    return pd.DataFrame(rows).set_index("year")


# ATFM delay minutes of one airport by year and reason group: minutes, minutes per arrival (the groups
# add up to the year's ATFM delay per arrival) and share of the year's minutes (%).
def causes_by_year(monthly, icao, years):
    rows = monthly[(monthly["icao"] == icao) & monthly["year"].isin(years)]
    sums = rows.groupby("year")[[*GROUP_ORDER, "arrivals", "delay_min"]].sum().reindex(years, fill_value=0)
    minutes = sums[GROUP_ORDER]
    per_arrival = minutes.div(sums["arrivals"].replace(0, np.nan), axis=0)
    shares = minutes.div(sums["delay_min"].replace(0, np.nan), axis=0) * 100
    return {"minutes": minutes, "per_arrival": per_arrival, "shares": shares, "totals": sums[["arrivals", "delay_min"]]}


# ATFM delay minutes per arrival of one airport for each month (rows) and year (columns);
# months without arrivals are missing.
def month_year_matrix(monthly, icao):
    rows = monthly[monthly["icao"] == icao]
    sums = rows.groupby(["month", "year"])[["delay_min", "arrivals"]].sum()
    matrix = (sums["delay_min"] / sums["arrivals"].replace(0, np.nan)).unstack("year")
    years = sorted(monthly["year"].unique())
    return matrix.reindex(index=range(1, 13), columns=years)


# Upper end of the map colour scale: a percentile of ATFM delay per arrival over every
# airport-year with at least MIN_ARRIVALS arrivals, so the colours mean the same in every year.
def color_cap(monthly, airports):
    values = pd.concat([busy_airports(monthly, airports, year)["delay_min_per_arrival"]
                        for year in sorted(monthly["year"].unique())])
    return float(values.quantile(COLOR_CAP_PERCENTILE / 100))
