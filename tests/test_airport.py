import pandas as pd
import pytest

from dashboard import airport, metrics
from dashboard.components import ordinal
from dashboard.data import GROUP_ORDER
from dashboard.figures import CAUSE_COLORS, SOURCE_NOTE


def _texts(component):
    return [child.children for child in component.children]


def test_selector_lists_busy_airports_only(dataset):
    listed = [o["value"] for o in airport.airport_options(dataset)]
    busy_any = set()
    for year in dataset.coverage.index:
        busy_any |= set(metrics.busy_airports(dataset.monthly, dataset.airports, year).index)
    assert set(listed) == busy_any
    assert "XSMA" not in listed  # never reaches the arrivals minimum
    first = dataset.airports.loc[listed[0]]
    assert airport.airport_options(dataset)[0]["label"] == f"{first['name']} ({listed[0]}), {first['country']}"


def test_initial_selection_from_url(dataset):
    complete = max(metrics.complete_years(dataset.coverage))
    assert airport.initial_selection(dataset) == ("LPPT", complete)
    assert airport.initial_selection(dataset, "ltac", "2025") == ("LTAC", 2025)
    assert airport.initial_selection(dataset, "ZZZZ", "abc") == ("LPPT", complete)
    assert airport.initial_selection(dataset, "LPPT", "1999") == ("LPPT", complete)


def test_ranking_and_ordinals(dataset):
    ranked = metrics.delay_ranking(dataset.monthly, dataset.airports, 2024)
    values = ranked["delay_min_per_arrival"]
    assert ranked["rank"].tolist() == values.rank(ascending=False, method="min").astype(int).tolist()
    assert [ordinal(n) for n in (1, 2, 3, 4, 11, 12, 13, 21, 22, 101)] == \
        ["1st", "2nd", "3rd", "4th", "11th", "12th", "13th", "21st", "22nd", "101st"]


def test_traffic_peers_are_neighbours_in_arrivals(dataset):
    totals = metrics.airport_year_totals(dataset.monthly, 2024)
    order = totals[totals["arrivals"] > 0].sort_values("arrivals", ascending=False).index.tolist()
    middle = order[1]
    assert metrics.traffic_peers(dataset.monthly, 2024, middle, n_each=1) == [order[0], order[2]]
    assert metrics.traffic_peers(dataset.monthly, 2025, "XSMA") == []  # no arrivals that year


def test_causes_add_up_to_delay_per_arrival(dataset):
    years = metrics.complete_years(dataset.coverage)
    causes = metrics.causes_by_year(dataset.monthly, "LPPT", years)
    totals = metrics.airport_year_totals(dataset.monthly, years[0]).loc["LPPT"]
    assert causes["per_arrival"].loc[years[0]].sum() == pytest.approx(totals["delay_min_per_arrival"])
    assert causes["shares"].loc[years[0]].sum() == pytest.approx(100)
    assert list(causes["per_arrival"].columns) == GROUP_ORDER == list(CAUSE_COLORS)


def test_month_year_matrix_leaves_months_without_data_blank(dataset):
    matrix = metrics.month_year_matrix(dataset.monthly, "LPPT")
    assert matrix.shape == (12, len(dataset.coverage))
    months_2025 = metrics.year_months(dataset.monthly, 2025)
    assert matrix[2025].drop(months_2025).isna().all()
    rows = dataset.monthly[(dataset.monthly["icao"] == "LPPT") & (dataset.monthly["year"] == 2024)
                           & (dataset.monthly["month"] == 1)]
    assert matrix.loc[1, 2024] == pytest.approx(rows["delay_min"].sum() / rows["arrivals"].sum())


def test_update_for_a_ranked_airport(dataset):
    out = airport.update_airport(dataset, "LPPT", 2024)
    kpis, peers_title, _, peers_fig, table_title, _, causes_title, causes_fig, _, heat_title, heat_fig = out
    assert [_texts(card)[0] for card in kpis] == \
        ["ATFM delay per arrival", "Arrivals with ATFM delay", "Arrivals", "Rank"]
    ranked = metrics.delay_ranking(dataset.monthly, dataset.airports, 2024)
    assert _texts(kpis[3])[1] == ordinal(int(ranked.loc["LPPT", "rank"]))
    assert _texts(kpis[3])[2] == f"of {len(ranked)} airports with at least 20,000 arrivals in 2024"
    for fig in (peers_fig, causes_fig, heat_fig):
        assert any(a.text == SOURCE_NOTE for a in fig.layout.annotations)
        assert any(a.text == "<b>2024</b>" for a in fig.layout.annotations)  # selected-year label
    assert [t.name for t in causes_fig.data] == GROUP_ORDER
    assert causes_fig.layout.showlegend is False  # the legend is HTML (components.legend)
    assert peers_title.endswith("and the median of its traffic peers") and table_title == "Traffic peers in 2024"
    # on phones the Arrivals column is hidden, the other columns stay
    header_cells = out[5].children.children[0].children.children
    assert [c.children for c in header_cells if "hide-mobile" in (c.className or "")] == ["Arrivals"]


def test_update_for_a_partial_year_and_an_airport_without_data(dataset):
    # partial year: the yearly charts show complete years only, the heatmap marks the partial year
    out = airport.update_airport(dataset, "LPPT", 2025)
    peers_fig, causes_fig, heat_fig = out[3], out[7], out[10]
    assert not any(a.text == "<b>Jan–Mar 2025</b>" for a in peers_fig.layout.annotations)
    assert not any(a.text == "<b>Jan–Mar 2025</b>" for a in causes_fig.layout.annotations)
    assert any(a.text == "<b>Jan–Mar 2025</b>" for a in heat_fig.layout.annotations)
    assert _texts(out[0][0])[2].endswith("against Jan–Mar 2024")
    # an airport with no arrivals in the year
    kpis, _, caption = airport.update_airport(dataset, "XSMA", 2025)[:3]
    assert _texts(kpis[0])[1] == "–" and _texts(kpis[0])[2] == "No arrivals reported in Jan–Mar 2025"
    assert _texts(kpis[3])[1] == "Not ranked"
    assert "no traffic peers" in caption
    assert isinstance(metrics.month_year_matrix(dataset.monthly, "XSMA"), pd.DataFrame)
