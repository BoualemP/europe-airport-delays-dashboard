"""Content of the Overview screen, built from a Dataset (kept apart from the page so it can be tested)."""

from functools import lru_cache

from dashboard import figures, metrics
from dashboard.components import kpi_cards


# Values that do not depend on the selected year, computed once per dataset.
@lru_cache(maxsize=2)
def _fixed(data):
    return (metrics.europe_by_month(data.monthly), metrics.color_cap(data.monthly, data.airports),
            metrics.map_bounds(data.monthly, data.airports))


# Everything the year selector changes: intro line, KPIs, trend, map title, map and its caption.
def update_overview(data, year):
    by_month, cap, bounds = _fixed(data)
    kpis = metrics.period_kpis(data.monthly, data.coverage, year)
    busy = metrics.busy_airports(data.monthly, data.airports, year)
    shown = busy.dropna(subset=["lat", "lon"])
    not_shown = len(busy) - len(shown)
    period = kpis["label"]
    return (
        f"Monthly ATFM delay across Europe since {by_month['date'].min():%b %Y}, "
        f"and where it built up in {period}.",
        kpi_cards(kpis),
        figures.trend_figure(by_month, year, period),
        f"ATFM delay minutes per arrival by airport, {period}",
        figures.map_figure(shown, cap, bounds),
        f"{len(busy)} airports with at least {metrics.MIN_ARRIVALS:,} arrivals in {period}. "
        "Bubble size shows arrivals."
        + (f" {not_shown} of them not shown: no coordinates in OurAirports." if not_shown else ""),
    )
