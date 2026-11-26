from dashboard import overview
from dashboard.figures import MAP_SOURCE_NOTE, SOURCE_NOTE


def _texts(component):
    return [child.children for child in component.children]


def test_year_options_and_default(dataset):
    options = overview.year_options(dataset)
    assert [o["value"] for o in options] == [2025, 2024]
    assert options[0]["label"] == "2025 (Jan–Mar)"
    assert overview.default_year(dataset) == 2024


def test_update_for_a_complete_year(dataset):
    intro, kpis, trend, map_title, map_fig, caption = overview.update_overview(dataset, 2024)
    assert intro.endswith("in 2024.")
    assert [_texts(card)[0] for card in kpis] == ["ATFM delay per arrival", "Arrivals with ATFM delay", "Arrivals"]
    assert all(_texts(card)[2] == "No previous year in the data" for card in kpis)
    assert any(a.text == SOURCE_NOTE for a in trend.layout.annotations)
    assert any(a.text == "<b>2024</b>" for a in trend.layout.annotations)  # selected-year label
    assert any(a.text == MAP_SOURCE_NOTE for a in map_fig.layout.annotations)
    assert map_title.endswith("2024")
    busy = dataset.monthly[dataset.monthly["year"] == 2024].groupby("icao")["arrivals"].sum().ge(20_000).sum()
    assert caption == f"{busy} airports with at least 20,000 arrivals in 2024. Bubble size shows arrivals."


def test_update_for_a_partial_year(dataset):
    _, kpis, _, map_title, map_fig, _ = overview.update_overview(dataset, 2025)
    changes = [_texts(card)[2] for card in kpis]
    assert changes[0].endswith("min against Jan–Mar 2024")
    assert changes[1].endswith("pp against Jan–Mar 2024")
    assert changes[2].endswith("% against Jan–Mar 2024")
    assert map_title.endswith("Jan–Mar 2025")
    assert map_fig.layout.coloraxis.colorbar.ticktext[-1].startswith("≥ ")


def test_map_bounds_cover_every_year(dataset):
    _, _, _, _, map_fig, _ = overview.update_overview(dataset, 2025)
    west, south, east, north = map_fig.layout.meta["bounds"]
    for year in dataset.coverage.index:
        shown = overview.metrics.map_airports(dataset.monthly, dataset.airports, year)
        assert shown["lon"].between(west, east).all() and shown["lat"].between(south, north).all()
