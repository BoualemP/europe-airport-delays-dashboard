"""Synthetic EUROCONTROL-like files, so the tests run offline and do not depend on the real data."""

import bz2
import json

import pytest

from dashboard.data import CODE_COLUMNS, DELAY_FILE, MANIFEST_FILE, OURAIRPORTS_FILE, load_dataset

HEADER = ["YEAR", "MONTH_NUM", "MONTH_MON", "FLT_DATE", "APT_ICAO", "APT_NAME", "STATE_NAME", "FLT_ARR_1",
          "DLY_APT_ARR_1", *CODE_COLUMNS.values(), "FLT_ARR_1_DLY", "FLT_ARR_1_DLY_15", "ATFM_VERSION"]


# One CSV line; delay=None leaves every delay value empty, as in the 2014-2022 files.
def row(date, icao, name, state, arrivals, delay=None, code="W", with_delay=0, over_15=0):
    year, month = int(date[:4]), int(date[5:7])
    if delay is None:
        values = [""] * (len(CODE_COLUMNS) + 3)
    else:
        values = [delay] + [delay if c == code else 0 for c in CODE_COLUMNS] + [with_delay, over_15]
    return ",".join(map(str, [year, month, "XXX", f"{date}T00:00:00Z", icao, name, state, arrivals,
                              *values, "v2"]))


# Write a bz2 file; 'Türkiye' is written in Latin-1 and everything else in UTF-8, as in the 2025 file.
def write_delay_file(path, lines):
    text = "\n".join([",".join(HEADER), *lines]) + "\n"
    path.write_bytes(bz2.compress(text.encode("utf-8").replace("Türkiye".encode("utf-8"), b"T\xfcrkiye")))


ROWS = {
    # 2024: complete year (1 Jan to 31 Dec); LTAC still under its earlier country name
    2024: [
        row("2024-01-01", "LPPT", "Lisbon", "Portugal", 12_000, 600, "W", 40, 10),
        row("2024-01-01", "LTAC", "Ankara/ Esenboğa", "Turkiye", 9_000),
        row("2024-01-01", "XSMA", "Small", "Portugal", 100),
        row("2024-03-10", "LPPT", "Lisbon", "Portugal", 2_000, 50, "W", 4, 1),
        row("2024-03-10", "LTAC", "Ankara/ Esenboğa", "Turkiye", 1_500),
        row("2024-07-15", "LPPT", "Lisbon", "Portugal", 12_000, 1_800, "G", 120, 60),
        row("2024-07-15", "LTAC", "Ankara/ Esenboğa", "Turkiye", 9_000, 90, "C", 9, 1),
        row("2024-12-31", "LPPT", "Lisbon", "Portugal", 6_000),
        row("2024-12-31", "LTAC", "Ankara/ Esenboğa", "Turkiye", 3_000),
    ],
    # 2025: partial year (January to March)
    2025: [
        row("2025-01-01", "LPPT", "Lisbon", "Portugal", 15_000, 300, "W", 30, 5),
        row("2025-01-01", "LTAC", "Ankara/ Esenboğa", "Türkiye", 12_000, 0, "W", 0, 0),
        row("2025-03-31", "LPPT", "Lisbon", "Portugal", 10_000, 200, "S", 20, 2),
        row("2025-03-31", "LTAC", "Ankara/ Esenboğa", "Türkiye", 10_000, 0, "W", 0, 0),
    ],
}

# OurAirports: LPPT matched on icao_code, LTAC only on ident; XSMA has no entry
OURAIRPORTS = (
    '"id","ident","type","name","latitude_deg","longitude_deg","elevation_ft","continent","iso_country",'
    '"iso_region","municipality","scheduled_service","icao_code","iata_code","gps_code","local_code",'
    '"home_link","wikipedia_link","keywords"\n'
    '1,"LPPT","large_airport","Lisbon",38.78,-9.13,374,"EU","PT","PT-11","Lisbon","yes","LPPT","LIS","LPPT",,,,\n'
    '2,"LTAC","large_airport","Ankara",40.12,32.99,3125,"AS","TR","TR-06","Ankara","yes",,"ESB","LTAC",,,,\n'
)


@pytest.fixture(scope="session")
def data_dir(tmp_path_factory):
    folder = tmp_path_factory.mktemp("data")
    manifest = {}
    for year, lines in ROWS.items():
        write_delay_file(folder / DELAY_FILE.format(year=year), lines)
        manifest[DELAY_FILE.format(year=year)] = {"retrieved_utc": "2026-11-20 10:00"}
    (folder / OURAIRPORTS_FILE).write_text(OURAIRPORTS)
    manifest[OURAIRPORTS_FILE] = {"retrieved_utc": "2026-11-20 10:00"}
    (folder / MANIFEST_FILE).write_text(json.dumps(manifest))
    return folder


@pytest.fixture(scope="session")
def dataset(data_dir):
    return load_dataset(data_dir, refresh=False, years=sorted(ROWS))
