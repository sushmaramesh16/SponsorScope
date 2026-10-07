"""Verify candidate board tokens against Greenhouse, Ashby and Lever; keep live boards.

    python -m pipeline.verify_companies          # writes seeds/companies.csv

A token is tried on each ATS in turn; the first one that answers with at least one
posting wins. Boards that 404 everywhere or have zero postings are dropped.
"""

from __future__ import annotations

import csv
from concurrent.futures import ThreadPoolExecutor, as_completed

from pipeline import boards
from pipeline.http import get_json
from pipeline.paths import CANDIDATES_CSV, COMPANIES_CSV

ORDER = ("greenhouse", "ashby", "lever")


def _count(ats: str, token: str) -> tuple[int, str | None]:
    """Number of postings on the board (0 if dead) and the board's own display name."""
    if ats == "greenhouse":
        board = boards.greenhouse_board(token)
        if not board:
            return 0, None
        jobs = get_json(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs") or {}
        return len(jobs.get("jobs", [])), board.get("name")
    if ats == "ashby":
        data = get_json(f"https://api.ashbyhq.com/posting-api/job-board/{token}") or {}
        return len(data.get("jobs", [])), None
    data = get_json(f"https://api.lever.co/v0/postings/{token}", {"mode": "json", "limit": 200})
    return len(data or []), None


def verify(token: str, name: str) -> dict | None:
    for ats in ORDER:
        try:
            n, board_name = _count(ats, token)
        except Exception:
            continue
        if n > 0:
            return {
                "ats": ats,
                "token": token,
                "company_name": name,
                "board_name": board_name or "",
                "open_postings_at_verify": n,
            }
    return None


def main() -> None:
    with open(CANDIDATES_CSV) as f:
        cands = list(csv.DictReader(f))
    live = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(verify, c["token"], c["company_name"]): c for c in cands}
        for fut in as_completed(futs):
            if (row := fut.result()) is not None:
                live.append(row)
    # one board per company name (duplicate tokens like toast/toasttab)
    live.sort(key=lambda r: (-r["open_postings_at_verify"], r["token"]))
    seen, keep = set(), []
    for r in live:
        if r["company_name"].lower() in seen:
            continue
        seen.add(r["company_name"].lower())
        keep.append(r)
    keep.sort(key=lambda r: r["company_name"].lower())
    with open(COMPANIES_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(keep[0].keys()))
        w.writeheader()
        w.writerows(keep)
    by_ats = {a: sum(r["ats"] == a for r in keep) for a in ORDER}
    print(f"{len(cands)} candidates -> {len(keep)} live boards {by_ats}")


if __name__ == "__main__":
    main()
