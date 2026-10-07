"""Run the whole daily pipeline: ingest -> dbt build -> export.

python -m pipeline.run                 # full run
python -m pipeline.run --skip-ingest   # rebuild from the latest local snapshot
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

import pandas as pd

from pipeline import export, ingest
from pipeline.paths import ROOT, SEEN_HISTORY


def ensure_history() -> None:
    """First run (or fresh clone without history): start from an empty, typed file."""
    if SEEN_HISTORY.exists():
        return
    SEEN_HISTORY.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "job_key": pd.Series(dtype="string"),
            "first_seen": pd.Series(dtype="datetime64[ms]"),
            "last_seen": pd.Series(dtype="datetime64[ms]"),
        }
    ).to_parquet(SEEN_HISTORY, index=False)


def dbt_build() -> None:
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    dbt = os.path.join(os.path.dirname(sys.executable), "dbt")
    cmd = [dbt, "build", "--project-dir", "dbt", "--profiles-dir", "dbt"]
    subprocess.run(cmd, cwd=ROOT, env=env, check=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-ingest", action="store_true")
    args = ap.parse_args()
    if not args.skip_ingest:
        ingest.run()
    ensure_history()
    dbt_build()
    export.main()


if __name__ == "__main__":
    main()
