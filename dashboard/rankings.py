"""Rankings: airports with at least MIN_ARRIVALS arrivals ranked by ATFM delay, by year and country."""

import pandas as pd
from dash import dcc, html

from dashboard import figures, metrics
from dashboard.components import default_year, ordinal, table

TOP_N = 15  # bars in the chart (analysis, 5.3)
ALL_COUNTRIES = "all"
# URL value -> (column, name in the selector, name in titles, value format)
MEASURES = {
    "minutes": ("delay_min_per_arrival", "ATFM delay minutes per arrival", "ATFM delay minutes per arrival",
                "{:.3f}"),
    "share": ("arr_with_atfm_delay_pct", "Share of arrivals with ATFM delay", "share of arrivals with ATFM delay",
              "{:.1f}%"),
}


def measure_options():
    return [{"label": label, "value": key} for key, (_, label, _, _) in MEASURES.items()]


# 'All countries', then the countries with at least one airport in the year's ranking.
def country_options(data, year):
    countries = sorted(metrics.busy_airports(data.monthly, data.airports, year)["country"].unique())
    return [{"label": "All countries", "value": ALL_COUNTRIES}, *[{"label": c, "value": c} for c in countries]]


# Year, country and measure from the URL (e.g. /rankings?year=2025&country=Portugal&by=share), or the
# defaults when missing or unknown. A repeated query key arrives as a list and counts as unknown.
def initial_selection(data, year=None, country=None, by=None):
    valid_year = isinstance(year, str) and year.isascii() and year.isdigit()
    year = int(year) if valid_year and int(year) in data.coverage.index else default_year(data)
    countries = [o["value"] for o in country_options(data, year)]
    country = country if isinstance(country, str) and country in countries else ALL_COUNTRIES
    by = by if isinstance(by, str) and by in MEASURES else "minutes"
    return year, country, by


def _fmt(value, pattern):
    return "–" if pd.isna(value) else pattern.format(value)


def _rank(value):
    return "–" if pd.isna(value) else ordinal(int(value))


# Table of every airport in the ranking (of one country, or all), ranked airports first. Each name links
# to the Airport explorer. The ranks are always the Europe-wide ones.
def _ranking_table(shown, year, previous):
    header = ["Rank", "Airport", "Country", "Arrivals", "ATFM delay min per arrival", "Arrivals with ATFM delay"]
    if previous is not None:
        header.append(f"Rank in {previous[1]}")
    body = []
    for icao, r in shown.iterrows():
        row = [_rank(r["rank"]), dcc.Link(f"{r['name']} ({icao})", href=f"/airport?icao={icao}&year={year}"),
               r["country"], f"{r['arrivals']:,.0f}", f"{r['delay_min_per_arrival']:.3f}",
               f"{r['arr_with_atfm_delay_pct']:.1f}%"]
        if previous is not None:
            row.append(_rank(previous[0].get(icao)))
        body.append(row)
    highlight = [i for i, icao in enumerate(shown.index) if icao in metrics.FOCUS_AIRPORTS]
    # Country, Arrivals and the previous rank are hidden on phones, so the rank, the name and the two
    # measures fit on screen
    return table(header, body, highlight=highlight, numeric=(0, 3, 4, 5, 6), hide_on_phones=(2, 3, 6))


# Everything the three selectors change. A country without airports in the new year falls back to all.
def update_rankings(data, year, country, by):
    options = country_options(data, year)
    if country not in [o["value"] for o in options]:
        country = ALL_COUNTRIES
    measure, _, measure_title, value_format = MEASURES[by]
    period = metrics.period_label(data.coverage, data.monthly, year)
    ranking = metrics.delay_ranking(data.monthly, data.airports, year, measure)
    shown = ranking if country == ALL_COUNTRIES else ranking[ranking["country"] == country]
    ranked = shown.dropna(subset=["rank"])
    where = "" if country == ALL_COUNTRIES else f" in {country}"
    minimum = f"at least {metrics.MIN_ARRIVALS:,} arrivals"

    # chart: the top airports, then Lisbon, Porto and Faro when they are ranked but outside the top
    top = ranked.head(TOP_N)
    extra = ranked[ranked.index.isin(metrics.FOCUS_AIRPORTS) & ~ranked.index.isin(top.index)]
    if len(ranked) > TOP_N:
        chart_title = f"The {TOP_N} airports{where} with the highest {measure_title} in {period}"
    else:
        chart_title = f"Airports{where} by {measure_title} in {period}"
    caption = [f"Airports with {minimum} in {period}. Lisbon, Porto and Faro are in orange"
               + (", after the top airports when they are not among them. " if len(extra) else ". "),
               "The Europe-wide value is on the ", dcc.Link("Overview", href="/"), "."]
    chart = (dcc.Graph(figure=figures.rankings_figure(top, extra, measure, value_format),
                       config={"displayModeBar": False}) if len(ranked)
             else html.P(f"No airport{where} had ATFM delay in {period}.", className="caption"))

    # table: every airport in the ranking, those without ATFM delay at the end
    previous = metrics.previous_ranks(data.monthly, data.airports, data.coverage, year, measure)
    table_title = f"All {len(shown)} airports{where} with {minimum} in {period}"
    notes = ["Each airport links to the Airport explorer."]
    if country != ALL_COUNTRIES:
        notes.append(f"Ranks are among all {len(ranking)} airports in the ranking.")
    if unranked := len(shown) - len(ranked):
        notes.append(f"{unranked} of these airports had no ATFM delay in {period}, so they are not ranked.")
    notes = [" ".join(notes)]
    if previous is not None:
        # hidden on phones, like the column it explains
        notes.append(html.Span(f" Rank in {previous[1]} is empty when the airport had fewer than "
                               f"{metrics.MIN_ARRIVALS:,} arrivals or no ATFM delay then.", className="hide-mobile"))
    return (options, country, chart_title, caption, chart, table_title, notes,
            _ranking_table(shown, year, previous))
