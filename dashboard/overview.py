"""Content of the Overview screen, built from a Dataset (kept apart from the page so it can be tested)."""

from functools import lru_cache

from dash import html

from dashboard import figures, metrics


# Year options, newest first; a partial year is labelled with its months ('2026 (Jan–Oct)').
def year_options(data):
    options = []
    for year in sorted(data.coverage.index, reverse=True):
        label = metrics.period_label(data.coverage, data.monthly, year)
        options.append({"label": label if label == str(year) else f"{year} ({label.removesuffix(f' {year}')})",
                        "value": year})
    return options


# The latest complete year, shown first.
def default_year(data):
    return max(metrics.complete_years(data.coverage))


def _signed(value, decimals):
    return f"{value:+,.{decimals}f}".replace("-", "−")


def _kpi(label, value, change):
    return html.Div(className="kpi", children=[
        html.Div(label, className="kpi-label"),
        html.Div(value, className="kpi-value"),
        html.Div(change, className="kpi-change"),
    ])


# Three KPI cards: ATFM delay per arrival, arrivals with ATFM delay, arrivals; each against the previous year.
def kpi_cards(kpis):
    now, before = kpis["current"], kpis["previous"]
    values = [f"{now['delay_min_per_arrival']:.2f} min", f"{now['arr_with_atfm_delay_pct']:.1f}%",
              f"{now['arrivals']:,.0f}"]
    if before is None:
        changes = ["No previous year in the data"] * 3
    else:
        changes = [f"{text} against {kpis['previous_label']}" for text in (
            f"{_signed(now['delay_min_per_arrival'] - before['delay_min_per_arrival'], 2)} min",
            f"{_signed(now['arr_with_atfm_delay_pct'] - before['arr_with_atfm_delay_pct'], 1)} pp",
            f"{_signed((now['arrivals'] / before['arrivals'] - 1) * 100, 1)}%",
        )]
    labels = ["ATFM delay per arrival", "Arrivals with ATFM delay", "Arrivals"]
    return [_kpi(*card) for card in zip(labels, values, changes)]


# Values that do not depend on the selected year, computed once per dataset.
@lru_cache(maxsize=2)
def _fixed(data):
    return (metrics.europe_by_month(data.monthly), metrics.color_cap(data.monthly, data.airports),
            metrics.map_bounds(data.monthly, data.airports))


# Everything the year selector changes: intro line, KPIs, trend, map title, map and its caption.
def update_overview(data, year):
    by_month, cap, bounds = _fixed(data)
    kpis = metrics.europe_kpis(data.monthly, data.coverage, year)
    busy = metrics.busy_airports(data.monthly, data.airports, year)
    shown = busy.dropna(subset=["lat", "lon"])
    not_shown = len(busy) - len(shown)
    period = kpis["label"]
    return (
        f"Monthly ATFM delay across Europe since {by_month['date'].min():%b %Y}, "
        f"and where it built up in {period}.",
        kpi_cards(kpis),
        figures.trend_figure(by_month, year),
        f"ATFM delay minutes per arrival by airport, {period}",
        figures.map_figure(shown, cap, bounds),
        f"{len(busy)} airports with at least {metrics.MIN_ARRIVALS:,} arrivals in {period}. "
        "Bubble size shows arrivals."
        + (f" {not_shown} of them not shown: no coordinates in OurAirports." if not_shown else ""),
    )
