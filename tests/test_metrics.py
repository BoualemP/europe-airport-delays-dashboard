import pandas as pd
import pytest

from dashboard import metrics


def test_complete_and_partial_years(dataset):
    assert metrics.complete_years(dataset.coverage) == [2024]
    assert metrics.year_months(dataset.monthly, 2025) == [1, 3]
    assert metrics.period_label(dataset.coverage, dataset.monthly, 2024) == "2024"
    assert metrics.period_label(dataset.coverage, dataset.monthly, 2025) == "Jan–Mar 2025"


def test_kpis_are_ratios_of_sums(dataset):
    kpis = metrics.period_kpis(dataset.monthly, dataset.coverage, 2024)
    rows = dataset.monthly[dataset.monthly["year"] == 2024]
    now = kpis["current"]
    assert now["delay_min_per_arrival"] == pytest.approx(rows["delay_min"].sum() / rows["arrivals"].sum())
    assert now["arr_with_atfm_delay_pct"] == pytest.approx(
        rows["arr_with_atfm_delay"].sum() / rows["arrivals"].sum() * 100)
    assert kpis["previous"] is None  # first year in the data


def test_partial_year_compares_same_months(dataset):
    kpis = metrics.period_kpis(dataset.monthly, dataset.coverage, 2025)
    before = dataset.monthly[(dataset.monthly["year"] == 2024) & dataset.monthly["month"].isin([1, 3])]
    assert kpis["previous"]["arrivals"] == before["arrivals"].sum()
    assert kpis["previous_label"] == "Jan–Mar 2024"


def test_map_keeps_busy_airports_with_coordinates(dataset):
    totals = metrics.airport_year_totals(dataset.monthly, 2024)
    busy = metrics.busy_airports(dataset.monthly, dataset.airports, 2024)
    assert set(busy.index) == set(totals.index[totals["arrivals"] >= metrics.MIN_ARRIVALS])
    shown = metrics.map_airports(dataset.monthly, dataset.airports, 2024)
    assert shown[["lat", "lon"]].notna().all().all()


def test_color_cap_is_a_percentile_of_busy_airport_years(dataset):
    values = [metrics.busy_airports(dataset.monthly, dataset.airports, year)["delay_min_per_arrival"]
              for year in dataset.coverage.index]
    expected = pd.concat(values).quantile(metrics.COLOR_CAP_PERCENTILE / 100)
    assert metrics.color_cap(dataset.monthly, dataset.airports) == pytest.approx(expected)
