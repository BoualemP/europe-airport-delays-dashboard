"""Content of the Airport explorer screen, built from a Dataset (kept apart from the page so it can be tested)."""

from functools import lru_cache

import pandas as pd
from dash import html

from dashboard import figures, metrics
from dashboard.components import kpi_card, kpi_cards, ordinal, table
from dashboard.data import GROUP_ORDER

DEFAULT_AIRPORT = "LPPT"  # Lisbon, the first of the three focus airports


# Airports offered in the selector: at least MIN_ARRIVALS arrivals in at least one year.
@lru_cache(maxsize=2)
def _explorer_airports(data):
    return metrics.explorer_airports(data.monthly, data.airports)


def airport_options(data):
    return [{"label": f"{row['name']} ({icao}), {row['country']}", "value": icao}
            for icao, row in _explorer_airports(data).iterrows()]


# Airport and year from the URL (e.g. /airport?icao=LPPT&year=2025), or the defaults when missing or unknown.
def initial_selection(data, icao=None, year=None):
    airports = _explorer_airports(data).index
    icao = (icao or "").upper()
    if icao not in airports:
        icao = DEFAULT_AIRPORT if DEFAULT_AIRPORT in airports else airports[0]
    years = data.coverage.index
    year = int(year) if str(year).isdigit() and int(year) in years else max(metrics.complete_years(data.coverage))
    return icao, year


def _name(data, icao):
    return data.airports.loc[icao, "name"]


# Four KPI cards: the three of the Overview for this airport, and its rank among busy airports.
def airport_kpis(data, icao, year):
    kpis = metrics.period_kpis(data.monthly, data.coverage, year, icao)
    period = kpis["label"]
    if kpis["current"]["arrivals"] == 0:
        no_data = f"No arrivals reported in {period}"
        cards = [kpi_card(label, "–", no_data)
                 for label in ["ATFM delay per arrival", "Arrivals with ATFM delay", "Arrivals"]]
    else:
        cards = kpi_cards(kpis)
    ranking = metrics.delay_ranking(data.monthly, data.airports, year)
    if icao in ranking.index:
        rank = kpi_card("Rank", ordinal(int(ranking.loc[icao, "rank"])),
                        f"of {len(ranking)} airports with at least {metrics.MIN_ARRIVALS:,} arrivals in {period}")
    else:
        rank = kpi_card("Rank", "Not ranked", f"Below {metrics.MIN_ARRIVALS:,} arrivals in {period}")
    return [*cards, rank], period


def _fmt(value, pattern, empty="–"):
    return empty if pd.isna(value) else pattern.format(value)


# Peer table: the airport (highlighted), its peers, and the median of the peers.
def _peer_table(data, icao, peers, year):
    rows, median = metrics.peer_table(data.monthly, data.airports, icao, peers, year)
    body = [[f"{r['name']} ({i})", _fmt(r["arrivals"], "{:,.0f}"), _fmt(r["delay_min_per_arrival"], "{:.3f}"),
             _fmt(r["arr_with_atfm_delay_pct"], "{:.1f}%"), "–" if pd.isna(r["rank"]) else ordinal(int(r["rank"]))]
            for i, r in rows.iterrows()]
    footer = [[f"Median of the {len(peers)} peers", _fmt(median["arrivals"], "{:,.0f}"),
               _fmt(median["delay_min_per_arrival"], "{:.3f}"), _fmt(median["arr_with_atfm_delay_pct"], "{:.1f}%"), ""]]
    header = ["Airport", "Arrivals", "ATFM delay min per arrival", "Arrivals with ATFM delay", "Rank"]
    return table(header, body, highlight=(0,), footer=footer)


# Causes table ("Show the numbers"): minutes per arrival by reason group and year, and the total.
def _causes_table(causes):
    per_arrival, totals = causes["per_arrival"], causes["totals"]
    body = [[str(year), *[_fmt(per_arrival.loc[year, g], "{:.3f}") for g in GROUP_ORDER],
             _fmt(totals.loc[year, "delay_min"] / totals.loc[year, "arrivals"] if totals.loc[year, "arrivals"]
                  else float("nan"), "{:.3f}")]
            for year in per_arrival.index]
    return html.Details(className="numbers", children=[
        html.Summary("Show the numbers"),
        html.P("ATFM delay minutes per arrival by reason group.", className="caption"),
        table(["Year", *GROUP_ORDER, "Total"], body),
    ])


# Everything the two selectors change.
def update_airport(data, icao, year):
    name = _name(data, icao)
    kpis, period = airport_kpis(data, icao, year)
    years = metrics.complete_years(data.coverage)

    peers = metrics.traffic_peers(data.monthly, year, icao)
    by_year = metrics.airport_vs_peers_by_year(data.monthly, icao, peers, years)
    if peers:
        peers_caption = (f"The peers are the {len(peers)} airports closest to {name} in arrivals in {period} "
                         "(up to 5 above and 5 below), kept the same in every year. Complete years only.")
        peers_table = _peer_table(data, icao, peers, year)
    else:
        peers_caption = f"{name} has no arrivals reported in {period}, so it has no traffic peers that year."
        peers_table = html.P("No traffic peers.", className="caption")

    causes = metrics.causes_by_year(data.monthly, icao, years)
    matrix = metrics.month_year_matrix(data.monthly, icao)
    return (
        kpis,
        f"ATFM delay minutes per arrival: {name} and the median of its traffic peers",
        peers_caption,
        figures.peers_figure(by_year, name, year, period),
        f"Traffic peers in {period}",
        peers_table,
        f"Causes of ATFM delay at {name}, by year",
        figures.causes_figure(causes, year, period),
        _causes_table(causes),
        f"ATFM delay minutes per arrival at {name}, by month",
        figures.heatmap_figure(matrix, year, period),
    )
