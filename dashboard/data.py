"""Download, read, check and aggregate the EUROCONTROL airport arrival ATFM delay files.

The files are not stored in the repository: they are downloaded into DATA_DIR at start-up and
reused from there (local cache), unless REFRESH is set. Each yearly file is read on its own and
aggregated at once to one row per airport and month, which keeps memory small.
"""

import bz2
import codecs
import io
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import pandas as pd
import requests

log = logging.getLogger(__name__)

# Data source and local cache
BASE_URL = "https://www.eurocontrol.int/performance/data/download/csv"
DELAY_FILE = "apt_dly_{year}.csv.bz2"
FIRST_YEAR = 2014  # first year listed on https://ansperformance.eu/csv/
OURAIRPORTS_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"
OURAIRPORTS_FILE = "ourairports_airports.csv"
DATA_DIR = Path(os.environ.get("DATA_DIR", "data"))
REFRESH = os.environ.get("REFRESH", "0") == "1"  # 1: download every file again
MANIFEST_FILE = "manifest.json"  # retrieval date and server metadata per file
TIMEOUT = 120

# Delay codes and their reason groups, as on
# https://ansperformance.eu/reference/dataset/airport-arrival-atfm-delay/ (without the "AD" prefix)
CODE_GROUPS = {
    "A": "Disruptions", "C": "Capacity (ATC)", "D": "Weather", "E": "Disruptions",
    "G": "Capacity", "I": "Disruptions (ATC)", "M": "Capacity", "N": "Disruptions",
    "O": "Disruptions", "P": "Events", "R": "Capacity", "S": "Staffing (ATC)",
    "T": "Disruptions (ATC)", "V": "Capacity", "W": "Weather", "NA": "Disruptions",
}
GROUP_ORDER = ["Capacity", "Weather", "Capacity (ATC)", "Staffing (ATC)", "Disruptions (ATC)",
               "Disruptions", "Events"]
CODE_COLUMNS = {code: f"DLY_APT_ARR_{code}_1" for code in CODE_GROUPS}
DELAY_TOTAL = "DLY_APT_ARR_1"
DELAY_VALUE_COLUMNS = [DELAY_TOTAL, *CODE_COLUMNS.values(), "FLT_ARR_1_DLY", "FLT_ARR_1_DLY_15"]
RAW_COLUMNS = ["FLT_DATE", "APT_ICAO", "APT_NAME", "STATE_NAME", "FLT_ARR_1", *DELAY_VALUE_COLUMNS]

# Names of the aggregated columns
SUM_COLUMNS = {
    "FLT_ARR_1": "arrivals",
    DELAY_TOTAL: "delay_min",
    "FLT_ARR_1_DLY": "arr_with_atfm_delay",
    "FLT_ARR_1_DLY_15": "arr_with_atfm_delay_over_15",
}


@dataclass(frozen=True, eq=False)  # hashed by identity, so per-dataset results can be cached
class Dataset:
    monthly: pd.DataFrame  # one row per year, month and airport
    airports: pd.DataFrame  # name, country, lat, lon per ICAO code
    coverage: pd.DataFrame  # first and last date per year
    retrieved: str  # date the delay files were retrieved (UTC)


# ---------------------------------------------------------------- download

def load_manifest(data_dir):
    path = data_dir / MANIFEST_FILE
    return json.loads(path.read_text()) if path.exists() else {}


def save_manifest(data_dir, manifest):
    (data_dir / MANIFEST_FILE).write_text(json.dumps(manifest, indent=2))


# Download one file into data_dir unless it is cached; return its path, or None when the server
# has no such file and missing_ok is True (the current year before its first publication).
def download_file(url, file_name, data_dir, manifest, refresh=False, missing_ok=False):
    path = data_dir / file_name
    if path.exists() and file_name in manifest and not refresh:
        return path
    response = requests.get(url, timeout=TIMEOUT)
    if response.status_code == 404 and missing_ok:
        log.info("%s not published yet", url)
        return None
    if response.status_code != 200:
        raise RuntimeError(f"{url} returned HTTP {response.status_code}")
    tmp_path = path.with_suffix(path.suffix + ".part")
    tmp_path.write_bytes(response.content)
    tmp_path.replace(path)
    manifest[file_name] = {
        "url": url,
        "retrieved_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
        "server_last_modified": response.headers.get("Last-Modified", ""),
    }
    log.info("downloaded %s", url)
    return path


# ---------------------------------------------------------------- reading

# Decode bytes that are not valid UTF-8 as Latin-1, one byte at a time: the 2025 and 2026 files
# write the country name Türkiye in Latin-1 and everything else in UTF-8.
def _latin1_fallback(error):
    return error.object[error.start:error.end].decode("latin-1"), error.end


codecs.register_error("latin1_fallback", _latin1_fallback)


def read_text(path):
    raw = bz2.open(path).read() if path.suffix == ".bz2" else path.read_bytes()
    return raw.decode("utf-8", errors="latin1_fallback")


# One yearly delay file, needed columns only; missing delay values mean 0.
def read_year(path):
    raw = pd.read_csv(io.StringIO(read_text(path)), usecols=RAW_COLUMNS)
    raw[DELAY_VALUE_COLUMNS] = raw[DELAY_VALUE_COLUMNS].fillna(0).astype("int64")
    raw["FLT_DATE"] = pd.to_datetime(raw["FLT_DATE"].str[:10])
    return raw


# ---------------------------------------------------------------- aggregation and checks

# ATFM delay minutes per reason group, row by row.
def group_minutes(raw):
    return pd.DataFrame({
        group: raw[[CODE_COLUMNS[c] for c, g in CODE_GROUPS.items() if g == group]].sum(axis=1)
        for group in GROUP_ORDER
    })


# One row per year, month and airport: sums of arrivals, ATFM delay minutes (total and by
# reason group), arrivals with ATFM delay, and the number of days reported.
def aggregate_year(raw):
    frame = pd.concat([raw[["APT_ICAO", *SUM_COLUMNS]], group_minutes(raw)], axis=1)
    frame["year"] = raw["FLT_DATE"].dt.year
    frame["month"] = raw["FLT_DATE"].dt.month
    frame["days"] = 1
    out = frame.groupby(["year", "month", "APT_ICAO"], as_index=False).sum()
    return out.rename(columns={"APT_ICAO": "icao", **SUM_COLUMNS})


# Compare an aggregated year with values computed from the raw file; raise if any differs.
def check_year(raw, agg):
    checks = [("rows = days", len(raw), int(agg["days"].sum())),
              ("airports", raw["APT_ICAO"].nunique(), agg["icao"].nunique()),
              ("reason groups = code minutes", int(raw[list(CODE_COLUMNS.values())].sum().sum()),
               int(agg[GROUP_ORDER].sum().sum()))]
    checks += [(name, int(raw[column].sum()), int(agg[name].sum())) for column, name in SUM_COLUMNS.items()]
    failed = [f"{name}: raw {expected}, aggregated {got}" for name, expected, got in checks if expected != got]
    if failed:
        raise ValueError("Aggregation checks failed: " + "; ".join(failed))


# Airport name for display: drop the slash the source uses between city and airport
# ("Amsterdam/ Schiphol" -> "Amsterdam Schiphol").
def display_name(name):
    return " ".join(name.replace("/", " ").split())


# Name and country of each airport on its latest reported date.
def latest_labels(raw):
    latest = raw.sort_values("FLT_DATE").groupby("APT_ICAO").last()
    return latest[["FLT_DATE", "APT_NAME", "STATE_NAME"]]


# ---------------------------------------------------------------- coordinates

# Latitude and longitude of the given ICAO codes from OurAirports. A code is looked up in icao_code,
# then ident, then gps_code (e.g. Jurmala, EVJA), then keywords, where closed airports keep their
# former code (e.g. Berlin Tegel, EDDT). Codes still without coordinates are logged and left out.
def read_coordinates(path, icao_codes):
    ours = pd.read_csv(path, usecols=["ident", "icao_code", "gps_code", "keywords", "latitude_deg", "longitude_deg"],
                       dtype="str")
    ours[["latitude_deg", "longitude_deg"]] = ours[["latitude_deg", "longitude_deg"]].astype("float64")
    keywords = ours.assign(keyword=ours["keywords"].fillna("").str.split(",")).explode("keyword")
    keywords["keyword"] = keywords["keyword"].str.strip().replace("", pd.NA)
    codes = pd.Index(icao_codes)
    coords = pd.DataFrame(index=codes, columns=["latitude_deg", "longitude_deg"], dtype="float64")
    for table, column in [(ours, "icao_code"), (ours, "ident"), (ours, "gps_code"), (keywords, "keyword")]:
        lookup = table.dropna(subset=[column]).drop_duplicates(column).set_index(column)
        coords = coords.fillna(lookup.reindex(codes)[["latitude_deg", "longitude_deg"]])
    missing = coords.index[coords.isna().any(axis=1)].tolist()
    if missing:
        log.warning("no coordinates in OurAirports for %s", ", ".join(missing))
    return coords.dropna().rename(columns={"latitude_deg": "lat", "longitude_deg": "lon"})


# ---------------------------------------------------------------- dataset

# Download (or reuse) every yearly file, aggregate each year, and add airport labels and coordinates.
def load_dataset(data_dir=DATA_DIR, refresh=REFRESH, years=None):
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(data_dir)
    current_year = datetime.now(timezone.utc).year
    years = range(FIRST_YEAR, current_year + 1) if years is None else years

    monthly, labels, coverage, delay_files = [], [], {}, []
    for year in years:
        file_name = DELAY_FILE.format(year=year)
        path = download_file(f"{BASE_URL}/{file_name}", file_name, data_dir, manifest, refresh,
                             missing_ok=year == current_year)
        save_manifest(data_dir, manifest)
        if path is None:
            continue
        raw = read_year(path)
        agg = aggregate_year(raw)
        check_year(raw, agg)
        monthly.append(agg)
        labels.append(latest_labels(raw))
        coverage[year] = {"first": raw["FLT_DATE"].min(), "last": raw["FLT_DATE"].max()}
        delay_files.append(file_name)
        del raw

    monthly = pd.concat(monthly, ignore_index=True)
    latest = pd.concat(labels).sort_values("FLT_DATE").groupby(level=0).last()
    airports = pd.DataFrame({"name": latest["APT_NAME"].map(display_name), "country": latest["STATE_NAME"]})
    airports.index.name = "icao"

    path = download_file(OURAIRPORTS_URL, OURAIRPORTS_FILE, data_dir, manifest, refresh)
    save_manifest(data_dir, manifest)
    airports = airports.join(read_coordinates(path, airports.index))

    retrieved = max(manifest[f]["retrieved_utc"] for f in delay_files)[:10]
    coverage = pd.DataFrame.from_dict(coverage, orient="index").rename_axis("year")
    log.info("%d airport-months, %d airports, %d years", len(monthly), len(airports), len(coverage))
    return Dataset(monthly=monthly, airports=airports, coverage=coverage, retrieved=retrieved)


# The dataset used by the app, loaded once per process.
@lru_cache(maxsize=1)
def get_data():
    return load_dataset()
