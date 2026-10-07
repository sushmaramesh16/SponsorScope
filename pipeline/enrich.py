"""Row-level enrichment of postings (called from the dbt Python model int_postings_enriched)."""

from __future__ import annotations

import pandas as pd

from pipeline.location import classify
from pipeline.newgrad import is_internship, is_new_grad, min_years_required
from pipeline.roles import ROLE_GROUP, normalize_role
from pipeline.salary import best_pay
from pipeline.visa import classify_visa_language


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    """Add role, location, visa, new-grad and pay columns; keep US/remote tech roles only."""
    df = df.copy()
    df["role"] = df["title"].map(normalize_role)
    df = df[df["role"].notna()].copy()

    locs = [
        classify(r, c, bool(h))
        for r, c, h in zip(df["location_raw"], df["country_hint"], df["remote_hint"], strict=True)
    ]
    df["is_us"] = [x.is_us for x in locs]
    df["is_remote"] = [x.is_remote for x in locs]
    df["city"] = [x.city for x in locs]
    df["state"] = [x.state for x in locs]
    df = df[df["is_us"]].copy()

    desc = df["description"].fillna("")
    df["role_group"] = df["role"].map(ROLE_GROUP)
    df["visa_status"] = desc.map(classify_visa_language)
    df["is_internship"] = df["title"].map(is_internship)
    df["is_new_grad"] = [is_new_grad(t, d) for t, d in zip(df["title"], desc, strict=True)]
    df["min_years_experience"] = desc.map(min_years_required).astype("Int64")

    pays = [
        best_pay(a, b, c, i, d)
        for a, b, c, i, d in zip(
            df["pay_min"], df["pay_max"], df["pay_currency"], df["pay_interval"], desc, strict=True
        )
    ]
    df["salary_min"] = [p.min_annual for p in pays]
    df["salary_max"] = [p.max_annual for p in pays]
    df["salary_interval"] = [p.interval for p in pays]
    for c in ("salary_min", "salary_max"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.drop(columns=["description", "pay_min", "pay_max", "pay_currency", "pay_interval", "is_us"])
