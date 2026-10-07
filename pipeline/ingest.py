"""Fetch every verified job board and write today's raw snapshot.

    python -m pipeline.ingest     # -> data/raw/postings/snapshot_date=YYYY-MM-DD/postings.parquet

The snapshot holds every posting as returned (all roles, all countries, full text);
filtering and enrichment happen downstream in dbt.
"""

from __future__ import annotations

import csv
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime

import pandas as pd

from pipeline.boards import fetch_board
from pipeline.paths import COMPANIES_CSV, RAW_POSTINGS

WORKERS = 8


def snapshot_dir(day: str):
    return RAW_POSTINGS / f"snapshot_date={day}"


def run(day: str | None = None) -> pd.DataFrame:
    day = day or datetime.now(UTC).date().isoformat()
    with open(COMPANIES_CSV) as f:
        companies = list(csv.DictReader(f))

    rows: list[dict] = []
    status: list[dict] = []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(fetch_board, c["ats"], c["token"], c["company_name"]): c for c in companies}
        for fut in as_completed(futs):
            c = futs[fut]
            try:
                jobs = fut.result()
                rows.extend(jobs)
                status.append({"ats": c["ats"], "token": c["token"], "ok": True, "postings": len(jobs)})
            except Exception as e:
                status.append({"ats": c["ats"], "token": c["token"], "ok": False, "error": str(e)[:200]})

    df = pd.DataFrame(rows)
    fetched_at = datetime.now(UTC).isoformat(timespec="seconds")
    df["fetched_at"] = fetched_at
    for col in ("pay_min", "pay_max"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["remote_hint"] = df["remote_hint"].fillna(False).astype(bool)

    out = snapshot_dir(day)
    out.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out / "postings.parquet", index=False, compression="zstd")
    failed = [s for s in status if not s["ok"]]
    summary = {
        "snapshot_date": day,
        "fetched_at": fetched_at,
        "boards": len(companies),
        "boards_ok": len(companies) - len(failed),
        "boards_failed": [f"{s['ats']}:{s['token']}" for s in failed],
        "postings": len(df),
        "seconds": round(time.time() - t0, 1),
    }
    (out / "fetch_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: v for k, v in summary.items() if k != "boards_failed"}), f"failed={len(failed)}")
    return df


if __name__ == "__main__":
    run()
