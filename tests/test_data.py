import pytest

from dashboard.data import DELAY_FILE, GROUP_ORDER, aggregate_year, check_year, display_name, read_text, read_year
from tests.conftest import ROWS


def test_mixed_encoding_is_read(data_dir):
    text = read_text(data_dir / DELAY_FILE.format(year=2025))
    assert "Türkiye" in text  # Latin-1 byte
    assert "Esenboğa" in text  # valid UTF-8 on the same row


def test_missing_delay_values_mean_zero(data_dir):
    raw = read_year(data_dir / DELAY_FILE.format(year=2024))
    assert not raw.isna().any().any()
    assert raw["DLY_APT_ARR_1"].dtype == "int64"


def test_aggregate_matches_raw_sums(data_dir):
    raw = read_year(data_dir / DELAY_FILE.format(year=2024))
    agg = aggregate_year(raw)
    check_year(raw, agg)  # raises if any sum differs
    assert agg["arrivals"].sum() == raw["FLT_ARR_1"].sum()
    assert (agg[GROUP_ORDER].sum(axis=1) == agg["delay_min"]).all()
    assert len(agg) == raw.groupby([raw["FLT_DATE"].dt.month, "APT_ICAO"]).ngroups


def test_check_year_fails_on_a_wrong_sum(data_dir):
    raw = read_year(data_dir / DELAY_FILE.format(year=2024))
    agg = aggregate_year(raw)
    agg.loc[0, "arrivals"] += 1
    with pytest.raises(ValueError, match="arrivals"):
        check_year(raw, agg)


def test_dataset_labels_and_coordinates(dataset):
    airports = dataset.airports
    assert airports.loc["LTAC", "country"] == "Türkiye"  # latest country name
    assert airports.loc["LTAC", "name"] == "Ankara Esenboğa"  # display name without the slash
    assert airports.loc[["LPPT", "LTAC"], "lat"].notna().all()  # icao_code and ident matches
    assert airports.loc["XSMA", ["lat", "lon"]].isna().all()  # no entry: no coordinates
    assert list(dataset.coverage.index) == sorted(ROWS)
    assert dataset.retrieved == "2026-11-20"


def test_display_name():
    assert display_name("Amsterdam/ Schiphol") == "Amsterdam Schiphol"
    assert display_name("Lleida/Alguaire") == "Lleida Alguaire"
