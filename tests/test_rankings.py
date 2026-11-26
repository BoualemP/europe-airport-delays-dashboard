from dashboard import metrics, rankings
from dashboard.figures import FOCUS, SOURCE_NOTE


def _cells(row):
    return [cell.children for cell in row.children]


def _table_rows(table):
    return table.children.children[1].children


def test_ranking_by_each_measure_leaves_airports_without_atfm_delay_unranked(dataset):
    for measure in ("delay_min_per_arrival", "arr_with_atfm_delay_pct"):
        ranked = metrics.delay_ranking(dataset.monthly, dataset.airports, 2025, measure)
        busy = metrics.busy_airports(dataset.monthly, dataset.airports, 2025)
        assert set(ranked.index) == set(busy.index)
        with_delay = ranked[ranked["delay_min"] > 0]
        assert ranked.loc[ranked["delay_min"] == 0, "rank"].isna().all()
        assert with_delay["rank"].tolist() == with_delay[measure].rank(ascending=False, method="min").astype(int).tolist()
        assert ranked["rank"].isna().tolist() == sorted(ranked["rank"].isna().tolist())  # unranked last


def test_previous_ranks_use_the_same_months(dataset):
    ranks, label = metrics.previous_ranks(dataset.monthly, dataset.airports, dataset.coverage, 2025)
    assert label == "Jan–Mar 2024"
    months = metrics.year_months(dataset.monthly, 2025)
    totals = metrics.airport_year_totals(dataset.monthly, 2024, months)
    busy = totals[totals["arrivals"] >= metrics.MIN_ARRIVALS]
    assert set(ranks.index) == set(busy.index)
    assert metrics.previous_ranks(dataset.monthly, dataset.airports, dataset.coverage, 2024) is None  # first year


def test_initial_selection_from_url(dataset):
    complete = max(metrics.complete_years(dataset.coverage))
    assert rankings.initial_selection(dataset) == (complete, "all", "minutes")
    assert rankings.initial_selection(dataset, "2025", "Portugal", "share") == (2025, "Portugal", "share")
    assert rankings.initial_selection(dataset, "²", "Narnia", "speed") == (complete, "all", "minutes")
    assert rankings.initial_selection(dataset, ["2024", "2025"], ["Portugal"], ["share"]) == (complete, "all", "minutes")


def test_update_for_all_countries(dataset):
    options, country, title, caption, chart, table_title, notes, table = \
        rankings.update_rankings(dataset, 2024, "all", "minutes")
    ranking = metrics.delay_ranking(dataset.monthly, dataset.airports, 2024)
    assert country == "all" and options[0]["value"] == "all"
    assert [o["value"] for o in options[1:]] == sorted(ranking["country"].unique())
    assert title == "Airports by ATFM delay minutes per arrival in 2024"
    fig = chart.figure
    assert any(a.text == SOURCE_NOTE for a in fig.layout.annotations)
    assert list(fig.data[0].y) == [f"{r}. {n}" for r, n in zip(ranking["rank"], ranking["name"])]
    lppt = list(fig.data[0].y).index(f"{ranking.loc['LPPT', 'rank']}. Lisbon")
    assert fig.data[0].marker.color[lppt] == FOCUS
    assert table_title == f"All {len(ranking)} airports with at least 20,000 arrivals in 2024"
    assert notes == [notes[0]] and "Rank in" not in notes[0]  # no previous year in the data
    rows = _table_rows(table)
    assert len(rows) == len(ranking)
    first = _cells(rows[0])
    assert first[0] == "1st" and first[1].href == f"/airport?icao={ranking.index[0]}&year=2024"


def test_update_for_a_country_keeps_europe_wide_ranks_and_previous_year(dataset):
    _, country, title, _, chart, table_title, notes, table = \
        rankings.update_rankings(dataset, 2025, "Türkiye", "share")
    ranking = metrics.delay_ranking(dataset.monthly, dataset.airports, 2025, "arr_with_atfm_delay_pct")
    assert country == "Türkiye"
    assert table_title.startswith("All 1 airports in Türkiye")
    # LTAC had no ATFM delay in Jan–Mar 2025: listed, not ranked, and no chart
    assert _cells(_table_rows(table)[0])[0] == "–"
    assert "1 of these airports had no ATFM delay in Jan–Mar 2025" in notes[0]
    assert f"Ranks are among all {len(ranking)} airports" in notes[0]
    # the sentence about the previous-year column is hidden on phones, like the column
    assert notes[1].className == "hide-mobile" and notes[1].children.startswith(" Rank in Jan–Mar 2024 is empty")
    assert chart.children == "No airport in Türkiye had ATFM delay in Jan–Mar 2025."
    header = table.children.children[0].children.children
    assert header[-1].children == "Rank in Jan–Mar 2024"
    # in Jan–Mar 2024 LTAC was below the arrivals minimum, so it has no previous rank
    previous = metrics.previous_ranks(dataset.monthly, dataset.airports, dataset.coverage, 2025,
                                      "arr_with_atfm_delay_pct")[0]
    assert "LTAC" not in previous.index and _cells(_table_rows(table)[0])[-1] == "–"


def test_country_missing_in_the_year_falls_back_to_all(dataset):
    _, country, *_ = rankings.update_rankings(dataset, 2024, "Narnia", "minutes")
    assert country == "all"
