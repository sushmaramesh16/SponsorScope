"""Export dbt marts to the small files the Streamlit app reads (committed to git).

data/app/jobs.parquet                 open postings (fct_jobs)
data/app/companies.parquet            one row per company (dim_companies)
data/app/company_lca_roles.parquet    H-1B role breakdown for matched employers
data/app/salary_by_role_city.parquet  posted-salary summary
data/app/meta.json                    freshness, counts, match rate
data/history/postings_seen.parquet    first_seen / last_seen (input to tomorrow's run)
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import duckdb

from pipeline.paths import APP_DATA, LCA_META, RAW_POSTINGS, SEEN_HISTORY, WAREHOUSE


def _copy(con: duckdb.DuckDBPyConnection, sql: str, path) -> int:
    con.execute(f"copy ({sql}) to '{path}' (format parquet, compression zstd)")
    return con.execute(f"select count(*) from read_parquet('{path}')").fetchone()[0]


def main() -> None:
    APP_DATA.mkdir(parents=True, exist_ok=True)
    SEEN_HISTORY.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(WAREHOUSE), read_only=True)

    n_jobs = _copy(
        con,
        "select * from fct_jobs order by posted_date desc, company_name, title",
        APP_DATA / "jobs.parquet",
    )
    n_cos = _copy(con, "select * from dim_companies order by company_name", APP_DATA / "companies.parquet")
    _copy(
        con,
        """
        select r.* from stg_lca_employer_roles r
        where r.employer_norm in (select employer_norm from dim_companies where employer_norm is not null)
        order by r.employer_norm, r.lca_certified desc
    """,
        APP_DATA / "company_lca_roles.parquet",
    )
    _copy(
        con,
        "select * from mart_salary_by_role_city order by role, postings_with_salary desc",
        APP_DATA / "salary_by_role_city.parquet",
    )
    n_hist = _copy(
        con, "select job_key, first_seen, last_seen from fct_postings_history order by job_key", SEEN_HISTORY
    )

    snap, n_raw, n_scope = con.execute("""
        select (select max(snapshot_date) from stg_postings),
               (select count(*) from stg_postings),
               (select count(*) from int_postings_enriched)
    """).fetchone()
    matched, total, blocked = con.execute("""
        select count(*) filter (where employer_norm is not null), count(*),
               count(*) filter (where match_method = 'blocked')
        from dim_companies
    """).fetchone()
    jobs_matched = con.execute(
        "select avg(case when employer_norm is not null then 1 else 0 end) from fct_jobs"
    ).fetchone()[0]
    methods = dict(
        con.execute("select match_method, count(*) from dim_companies group by 1 order by 2 desc").fetchall()
    )
    con.close()

    summary_path = RAW_POSTINGS / f"snapshot_date={snap}" / "fetch_summary.json"
    fetch = json.loads(summary_path.read_text()) if summary_path.exists() else {}
    meta = {
        "snapshot_date": str(snap),
        "fetched_at": fetch.get("fetched_at"),
        "boards": fetch.get("boards"),
        "boards_ok": fetch.get("boards_ok"),
        "postings_fetched": n_raw,
        "postings_in_scope": n_scope,
        "open_jobs": n_jobs,
        "companies": n_cos,
        "employer_match": {
            "companies_matched": matched,
            "companies_total": total,
            "company_match_rate": round(matched / total, 4) if total else None,
            "open_jobs_with_matched_employer": round(jobs_matched or 0, 4),
            "blocked_false_matches": blocked,
            "by_method": methods,
        },
        "history_rows": n_hist,
        "lca": json.loads(LCA_META.read_text()) if LCA_META.exists() else None,
        "exported_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    (APP_DATA / "meta.json").write_text(json.dumps(meta, indent=2, default=str))
    print(
        json.dumps(
            {k: meta[k] for k in ("snapshot_date", "postings_fetched", "open_jobs", "employer_match")},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
