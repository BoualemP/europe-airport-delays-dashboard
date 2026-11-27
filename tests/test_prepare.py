import pandas as pd

from dashboard import prepare
from dashboard.data import load_dataset, load_prepared


def test_prepared_file_holds_the_same_dataset(data_dir, tmp_path):
    years = [2024, 2025]
    path = tmp_path / "prepared" / "dataset.pkl"
    prepare.main(path, data_dir, refresh=False, years=years)
    saved, direct = load_prepared(path), load_dataset(data_dir, refresh=False, years=years)
    pd.testing.assert_frame_equal(saved.monthly, direct.monthly)
    pd.testing.assert_frame_equal(saved.airports, direct.airports)
    pd.testing.assert_frame_equal(saved.coverage, direct.coverage)
    assert saved.retrieved == direct.retrieved
    assert not path.with_suffix(".tmp").exists()


def test_get_data_reads_the_prepared_file_when_set(data_dir, tmp_path, monkeypatch):
    from dashboard import data
    path = tmp_path / "dataset.pkl"
    prepared = prepare.main(path, data_dir, refresh=False, years=[2024, 2025])
    monkeypatch.setattr(data, "PREPARED_FILE", str(path))
    monkeypatch.setattr(data, "REFRESH", False)
    data.get_data.cache_clear()
    try:
        pd.testing.assert_frame_equal(data.get_data().monthly, prepared.monthly)
    finally:
        data.get_data.cache_clear()
