"""Aggregate raw DOL OFLC LCA disclosure files to small employer-level parquet files.

    python scripts/fetch_lca.py --fy 2025      # one-time / quarterly download (data/raw/lca)
    python -m pipeline.lca                     # writes data/lca/*.parquet (committed)

Only H-1B cases are kept (not H-1B1 / E-3). "Filings" counts LCA cases, which are not
the same as approved petitions or hires.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime

import duckdb
import pandas as pd

from pipeline.employer_match import normalize_name
from pipeline.paths import LCA_EMPLOYER_ROLES, LCA_EMPLOYERS, LCA_META, RAW_LCA
from pipeline.roles import normalize_role

COLS = [
    "CASE_STATUS",
    "VISA_CLASS",
    "JOB_TITLE",
    "SOC_TITLE",
    "FULL_TIME_POSITION",
    "EMPLOYER_NAME",
    "WORKSITE_CITY",
    "WORKSITE_STATE",
    "WAGE_RATE_OF_PAY_FROM",
    "WAGE_UNIT_OF_PAY",
    "DECISION_DATE",
]
UNIT_PER_YEAR = {"Year": 1, "Hour": 2080, "Month": 12, "Week": 52, "Bi-Weekly": 26}


def load_raw() -> tuple[pd.DataFrame, list[str]]:
    files = sorted(RAW_LCA.glob("LCA_Disclosure_Data_FY*_Q*.xlsx"))
    if not files:
        raise SystemExit(f"No LCA files in {RAW_LCA}; run scripts/fetch_lca.py first.")
    frames = []
    for f in files:
        print(f"reading {f.name}")
        frames.append(pd.read_excel(f, engine="calamine", usecols=COLS))
    return pd.concat(frames, ignore_index=True), [f.name for f in files]


def build(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = df[df["VISA_CLASS"] == "H-1B"].copy()
    df["employer_norm"] = df["EMPLOYER_NAME"].astype(str).map(normalize_name)
    df = df[df["employer_norm"] != ""]
    df["wage_annual"] = pd.to_numeric(df["WAGE_RATE_OF_PAY_FROM"], errors="coerce") * df[
        "WAGE_UNIT_OF_PAY"
    ].map(UNIT_PER_YEAR)
    df.loc[(df["wage_annual"] < 20_000) | (df["wage_annual"] > 2_000_000), "wage_annual"] = None
    titles = df["JOB_TITLE"].astype(str)
    uniq = {t: normalize_role(t) for t in titles.unique()}
    df["role"] = titles.map(uniq)
    df["job_title"] = titles.str.strip().map(lambda t: re.sub(r"\s+", " ", t).title())
    df["certified"] = df["CASE_STATUS"].astype(str).str.startswith("Certified")
    df["state"] = df["WORKSITE_STATE"].astype(str).str.upper().str.strip()

    con = duckdb.connect()
    con.register(
        "lca",
        df[
            [
                "employer_norm",
                "EMPLOYER_NAME",
                "CASE_STATUS",
                "certified",
                "wage_annual",
                "role",
                "job_title",
                "state",
                "FULL_TIME_POSITION",
            ]
        ],
    )
    employers = con.sql("""
        with base as (select * from lca),
        names as (
            select employer_norm, EMPLOYER_NAME as employer_name,
                   row_number() over (partition by employer_norm order by count(*) desc, EMPLOYER_NAME) rn
            from base group by 1, 2
        ),
        titles as (
            select employer_norm, job_title, count(*) n,
                   row_number() over (partition by employer_norm order by count(*) desc, job_title) rn
            from base where certified group by 1, 2
        ),
        states as (
            select employer_norm, state, count(*) n,
                   row_number() over (partition by employer_norm order by count(*) desc, state) rn
            from base where certified and state not in ('', 'NAN') group by 1, 2
        )
        select
            b.employer_norm,
            any_value(n.employer_name) as employer_name,
            count(*)::int as lca_filings,
            count(*) filter (where certified)::int as lca_certified,
            count(*) filter (where CASE_STATUS = 'Denied')::int as lca_denied,
            count(*) filter (where role is not null and certified)::int as lca_tech_certified,
            round(median(wage_annual) filter (where certified and FULL_TIME_POSITION = 'Y'))::int
                as lca_median_wage,
            count(distinct state) filter (where certified)::int as lca_n_states,
            (select string_agg(t.job_title || ' (' || t.n || ')', '; ' order by t.rn)
               from titles t where t.employer_norm = b.employer_norm and t.rn <= 5) as lca_top_titles,
            (select string_agg(s.state || ' (' || s.n || ')', '; ' order by s.rn)
               from states s where s.employer_norm = b.employer_norm and s.rn <= 5) as lca_top_states
        from base b
        join names n on n.employer_norm = b.employer_norm and n.rn = 1
        group by b.employer_norm
        order by lca_certified desc
    """).df()
    roles = con.sql("""
        select employer_norm, role,
               count(*)::int as lca_certified,
               round(median(wage_annual))::int as lca_median_wage,
               round(quantile_cont(wage_annual, 0.25))::int as lca_p25_wage,
               round(quantile_cont(wage_annual, 0.75))::int as lca_p75_wage
        from lca
        where certified and role is not null and FULL_TIME_POSITION = 'Y'
        group by 1, 2
        order by 1, 3 desc
    """).df()
    return employers, roles


def main() -> None:
    df, files = load_raw()
    employers, roles = build(df)
    LCA_EMPLOYERS.parent.mkdir(parents=True, exist_ok=True)
    employers.to_parquet(LCA_EMPLOYERS, index=False, compression="zstd")
    roles.to_parquet(LCA_EMPLOYER_ROLES, index=False, compression="zstd")
    dates = pd.to_datetime(df["DECISION_DATE"], errors="coerce")
    meta = {
        "source": "US DOL OFLC LCA Programs (H-1B, H-1B1, E-3) disclosure data",
        "source_page": "https://www.dol.gov/agencies/eta/foreign-labor/performance",
        "files": files,
        "decision_date_min": str(dates.min().date()),
        "decision_date_max": str(dates.max().date()),
        "h1b_cases": int(employers["lca_filings"].sum()),
        "employers": len(employers),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    LCA_META.write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
