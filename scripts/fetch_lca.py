"""Download US DOL OFLC LCA disclosure files (H-1B, H-1B1, E-3) into data/raw/lca/.

Official source page: https://www.dol.gov/agencies/eta/foreign-labor/performance
File pattern on that page (FY2025):
  https://www.dol.gov/sites/dolgov/files/ETA/oflc/pdfs/LCA_Disclosure_Data_FY2025_Q{1..4}.xlsx

dol.gov sits behind a CDN that rejects plain HTTP clients (403), so this uses a
headless browser session (Playwright) that first opens the public page and then
downloads the files from it. Run it by hand when OFLC publishes a new quarter; the
daily job refresh does not need it.

    pip install playwright && python -m playwright install chromium
    python scripts/fetch_lca.py --fy 2025 --quarters 1 2 3 4
"""

from __future__ import annotations

import argparse
from pathlib import Path

PAGE = "https://www.dol.gov/agencies/eta/foreign-labor/performance"
BASE = "https://www.dol.gov/sites/dolgov/files/ETA/oflc/pdfs"
OUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "lca"


def file_url(fy: int, q: int) -> str:
    return f"{BASE}/LCA_Disclosure_Data_FY{fy}_Q{q}.xlsx"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fy", type=int, default=2025)
    ap.add_argument("--quarters", type=int, nargs="+", default=[1, 2, 3, 4])
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright

    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()
        ctx.new_page().goto(PAGE, timeout=90_000)
        for q in args.quarters:
            dest = OUT / f"LCA_Disclosure_Data_FY{args.fy}_Q{q}.xlsx"
            if dest.exists() and dest.stat().st_size > 1_000_000:
                print(f"skip {dest.name} (exists)")
                continue
            url = file_url(args.fy, q)
            print(f"GET {url}")
            r = ctx.request.get(url, timeout=900_000)
            if r.status != 200:
                raise SystemExit(f"{url} -> HTTP {r.status}")
            dest.write_bytes(r.body())
            print(f"saved {dest.name} ({dest.stat().st_size / 1e6:.1f} MB)")
        browser.close()


if __name__ == "__main__":
    main()
