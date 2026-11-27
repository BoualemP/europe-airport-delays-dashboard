"""Build-time step (Dockerfile): download, aggregate and check every EUROCONTROL file, as the app does at
start-up, and save the result to PREPARED_FILE for the app to read.

    PREPARED_FILE=prepared/dataset.pkl python -m dashboard.prepare
"""

import logging
import sys

from dashboard.data import DATA_DIR, PREPARED_FILE, REFRESH, load_dataset, save_prepared

log = logging.getLogger(__name__)


def main(path=PREPARED_FILE, data_dir=DATA_DIR, refresh=REFRESH, years=None):
    if not path:
        sys.exit("Set PREPARED_FILE to the file to write.")
    dataset = load_dataset(data_dir, refresh, years)
    save_prepared(dataset, path)
    log.info("saved %d airport-months, retrieved %s, to %s", len(dataset.monthly), dataset.retrieved, path)
    return dataset


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    main()
