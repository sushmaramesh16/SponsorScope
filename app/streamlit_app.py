"""SponsorScope: live US data/ML and software jobs, flagged by employer H-1B history."""

from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

DATA = Path(__file__).resolve().parents[1] / "data" / "app"

VISA_LABEL = {
    "sponsorship available": "✅ Says it sponsors",
    "no sponsorship": "🚫 Says no sponsorship",
    "not mentioned": "— Not mentioned",
}

st.set_page_config(page_title="SponsorScope", page_icon="🔭", layout="wide")


@st.cache_data(ttl=3600)
def load():
    jobs = pd.read_parquet(DATA / "jobs.parquet")
    companies = pd.read_parquet(DATA / "companies.parquet")
    lca_roles = pd.read_parquet(DATA / "company_lca_roles.parquet")
    meta = json.loads((DATA / "meta.json").read_text())
    jobs["posted_date"] = pd.to_datetime(jobs["posted_date"]).dt.date
    jobs["lca_certified"] = jobs["lca_certified"].fillna(0).astype(int)
    jobs["salary_mid"] = (jobs["salary_min"] + jobs["salary_max"]) / 2
    jobs["where"] = jobs.apply(_where, axis=1)
    return jobs, companies, lca_roles, meta


def _where(r) -> str:
    place = f"{r['city']}, {r['state']}" if r["city"] else (r["state"] or "")
    if r["is_remote"]:
        return f"Remote · {place}" if place else "Remote (US)"
    return place or str(r["location_raw"] or "US")


def money(x) -> str:
    return "—" if pd.isna(x) else f"${x / 1000:,.0f}K"


def salary_text(lo, hi) -> str:
    if pd.isna(lo):
        return ""
    return money(lo) if lo == hi else f"{money(lo)}–{money(hi)}"


def sponsor_badge(n: int) -> str:
    return f"🟢 {n:,} H-1B" if n >= 50 else f"🟡 {n:,} H-1B" if n > 0 else "⚪ none found"


jobs, companies, lca_roles, meta = load()
lca = meta.get("lca") or {}
snapshot = meta.get("snapshot_date", "?")

# ── header ──────────────────────────────────────────────────────────────────
st.title("🔭 SponsorScope")
st.markdown(
    "Live US **data, ML and software** job postings, each flagged by whether the employer has "
    "**H-1B sponsorship history**, for international grads looking for sponsor-friendly roles."
)
st.caption(
    f"Jobs refreshed **{snapshot}** from {meta.get('boards_ok', '?')} company job boards "
    f"(Greenhouse, Lever, Ashby) · H-1B history: US DOL LCA disclosures, decisions "
    f"{lca.get('decision_date_min', '?')} → {lca.get('decision_date_max', '?')} (FY2025)."
)
with st.expander("⚠️ Read this first: what the H-1B flag does and doesn't mean", expanded=False):
    st.markdown(
        "- **H-1B history does not guarantee sponsorship** for any particular role or candidate. "
        "It shows the employer filed Labor Condition Applications (LCAs) in FY2025.\n"
        "- An **LCA filing is not a hire** or an approved petition; one person can have several LCAs.\n"
        "- The visa-language flag is a **rule-based reading** of the posting text and can be wrong; "
        "always read the posting and ask the recruiter.\n"
        "- **Not legal or immigration advice.** Talk to an immigration attorney or your DSO."
    )

# ── sidebar filters ─────────────────────────────────────────────────────────
sb = st.sidebar
sb.header("Filters")
query = sb.text_input("Search title or company", placeholder="e.g. recommendation, Stripe")
groups = sb.multiselect("Role family", ["Data & ML", "Software Engineering"])
role_opts = sorted(jobs.loc[jobs["role_group"].isin(groups) if groups else slice(None), "role"].unique())
roles = sb.multiselect("Role", role_opts)

loc_mode = sb.radio("Location", ["Anywhere in US", "Remote only", "On-site / hybrid only"])
states = sb.multiselect("States", sorted(s for s in jobs["state"].dropna().unique()))

new_grad = sb.toggle("New-grad / early-career only", value=False)
interns = sb.toggle("Include internships", value=False)

sb.subheader("Sponsorship")
sponsor_only = sb.toggle(
    "Sponsor-friendly only",
    value=False,
    help="Employer has certified H-1B LCAs (at least the minimum below) and the posting does "
    "not say it won't sponsor.",
)
min_filings = sb.slider("Min. FY2025 certified H-1B LCAs", 1, 200, 1, disabled=not sponsor_only)
visa_sel = sb.multiselect("Visa language in posting", list(VISA_LABEL), format_func=lambda v: VISA_LABEL[v])

sb.subheader("Pay & recency")
min_salary = sb.slider("Minimum posted salary ($K/yr)", 0, 400, 0, step=10)
keep_unpaid = sb.checkbox("Keep postings without a posted salary", value=True, disabled=min_salary == 0)
DAYS = {
    "Any time": None,
    "Last 24 hours": 1,
    "Last 3 days": 3,
    "Last 7 days": 7,
    "Last 14 days": 14,
    "Last 30 days": 30,
    "Last 90 days": 90,
}
days = DAYS[sb.selectbox("Posted within", list(DAYS), key="posted_within")]

f = jobs
if query:
    pat = re.escape(query.strip())
    f = f[
        f["title"].str.contains(pat, case=False, na=False)
        | f["company_name"].str.contains(pat, case=False, na=False)
    ]
if groups:
    f = f[f["role_group"].isin(groups)]
if roles:
    f = f[f["role"].isin(roles)]
if loc_mode == "Remote only":
    f = f[f["is_remote"]]
elif loc_mode == "On-site / hybrid only":
    f = f[~f["is_remote"]]
if states:
    f = f[f["state"].isin(states)]
if new_grad:
    f = f[f["is_new_grad"]]
if not interns:
    f = f[~f["is_internship"]]
if sponsor_only:
    f = f[(f["lca_certified"] >= min_filings) & (f["visa_status"] != "no sponsorship")]
if visa_sel:
    f = f[f["visa_status"].isin(visa_sel)]
if min_salary:
    ok = f["salary_max"] >= min_salary * 1000
    f = f[ok | (f["salary_max"].isna() & keep_unpaid)]
if days:
    f = f[f["posted_date"] >= date.fromisoformat(snapshot) - timedelta(days=days)]

tab_jobs, tab_cos, tab_pay, tab_about = st.tabs(["Jobs", "Companies", "Salary insights", "About"])

# ── jobs ────────────────────────────────────────────────────────────────────
with tab_jobs:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Matching jobs", f"{len(f):,}")
    c2.metric("Companies", f"{f['company_name'].nunique():,}")
    c3.metric("At H-1B employers", f"{(f['lca_certified'] > 0).mean():.0%}" if len(f) else "—")
    c4.metric("With posted salary", f"{f['salary_min'].notna().mean():.0%}" if len(f) else "—")

    view = pd.DataFrame(
        {
            "Company": f["company_name"],
            "Title": f["title"],
            "Role": f["role"],
            "Location": f["where"],
            "Posted": f["posted_date"],
            "Salary": [salary_text(a, b) for a, b in zip(f["salary_min"], f["salary_max"], strict=True)],
            "H-1B (FY25)": f["lca_certified"].map(sponsor_badge),
            "Visa language": f["visa_status"].map(VISA_LABEL),
            "New grad": f["is_new_grad"],
            "Employer LCA median (role)": f["lca_role_median_wage"].map(money),
            "Apply": f["apply_url"],
        }
    ).sort_values(["Posted", "Company"], ascending=[False, True])
    st.dataframe(
        view,
        hide_index=True,
        width="stretch",
        height=620,
        column_config={
            "Apply": st.column_config.LinkColumn("Apply", display_text="Open ↗"),
            "Posted": st.column_config.DateColumn("Posted", format="MMM D, YYYY"),
            "New grad": st.column_config.CheckboxColumn("New grad"),
            "Employer LCA median (role)": st.column_config.TextColumn(
                "Employer LCA median (role)",
                help="Median annual wage on this employer's FY2025 certified H-1B LCAs for this role "
                "family: context for what they pay sponsored hires, not this job's salary.",
            ),
            "H-1B (FY25)": st.column_config.TextColumn(
                "H-1B (FY25)", help="Certified H-1B LCAs filed by this employer in FY2025."
            ),
        },
    )
    st.caption(
        "🟢 50+ certified H-1B LCAs · 🟡 1–49 · ⚪ none found (no filings, or the employer's legal "
        "name could not be matched). Salary is the posted range, annualized."
    )

# ── companies ───────────────────────────────────────────────────────────────
with tab_cos:
    cos = companies.sort_values(["lca_certified", "open_postings"], ascending=False)
    names = cos.loc[cos["open_postings"] > 0, "company_name"].tolist()  # biggest sponsors first
    pick = st.selectbox("Company", names, index=0 if names else None)
    if pick:
        c = cos.set_index("company_name").loc[pick]
        a, b, d, e = st.columns(4)
        a.metric("Certified H-1B LCAs (FY2025)", f"{int(c['lca_certified']):,}")
        b.metric("Median LCA wage", money(c["lca_median_wage"]))
        d.metric("Worksite states", "—" if pd.isna(c["lca_n_states"]) else int(c["lca_n_states"]))
        e.metric("Open postings here", int(c["open_postings"]))
        if c["employer_norm"] is None or pd.isna(c["employer_norm"]):
            st.info(
                "No FY2025 H-1B LCA filings matched this company. It may file under a different "
                "legal name, or may not sponsor."
            )
        else:
            st.caption(
                f"Matched to LCA employer **{c['lca_employer_name']}** ({c['match_method']} match). "
                f"Top worksite states: {c['lca_top_states'] or '—'}"
            )
            left, right = st.columns(2)
            with left:
                st.markdown("**Top sponsored job titles (certified LCAs)**")
                rows = [
                    (m.group(1), int(m.group(2)))
                    for m in re.finditer(r"([^;]+?) \((\d+)\)", c["lca_top_titles"] or "")
                ]
                if rows:
                    t = pd.DataFrame(rows, columns=["Job title", "LCAs"])
                    st.altair_chart(
                        alt.Chart(t)
                        .mark_bar()
                        .encode(x="LCAs:Q", y=alt.Y("Job title:N", sort="-x", title=None))
                        .properties(height=220),
                        width="stretch",
                    )
            with right:
                st.markdown("**By role family (full-time, certified)**")
                r = lca_roles[lca_roles["employer_norm"] == c["employer_norm"]]
                st.dataframe(
                    pd.DataFrame(
                        {
                            "Role": r["role"],
                            "LCAs": r["lca_certified"],
                            "Median wage": r["lca_median_wage"].map(money),
                            "25th–75th pct": [
                                f"{money(p)}–{money(q)}"
                                for p, q in zip(r["lca_p25_wage"], r["lca_p75_wage"], strict=True)
                            ],
                        }
                    ),
                    hide_index=True,
                    width="stretch",
                )
        st.markdown("**Currently open postings**")
        o = jobs[jobs["company_name"] == pick]
        st.dataframe(
            pd.DataFrame(
                {
                    "Title": o["title"],
                    "Location": o["where"],
                    "Posted": o["posted_date"],
                    "Salary": [
                        salary_text(x, y) for x, y in zip(o["salary_min"], o["salary_max"], strict=True)
                    ],
                    "Visa language": o["visa_status"].map(VISA_LABEL),
                    "Apply": o["apply_url"],
                }
            ).sort_values("Posted", ascending=False),
            hide_index=True,
            width="stretch",
            column_config={"Apply": st.column_config.LinkColumn("Apply", display_text="Open ↗")},
        )

    st.divider()
    st.markdown("**All tracked companies**")
    st.dataframe(
        cos[
            ["company_name", "open_postings", "lca_certified", "lca_median_wage", "match_method", "ats"]
        ].rename(
            columns={
                "company_name": "Company",
                "open_postings": "Open tech postings",
                "lca_certified": "Certified H-1B LCAs",
                "lca_median_wage": "Median LCA wage",
                "match_method": "LCA match",
                "ats": "Job board",
            }
        ),
        hide_index=True,
        width="stretch",
        column_config={"Median LCA wage": st.column_config.NumberColumn(format="$%d")},
    )

# ── salary insights ─────────────────────────────────────────────────────────
with tab_pay:
    st.caption("Uses the jobs matching your filters. Posted ranges are annualized; midpoints shown.")
    paid = f[f["salary_mid"].notna() & ~f["is_internship"]]
    if paid.empty:
        st.info("No postings with a salary match these filters.")
    else:
        by_role = (
            paid.groupby("role")
            .agg(
                postings=("salary_mid", "size"),
                posted_median=("salary_mid", "median"),
                lca_median=("lca_role_median_wage", "median"),
            )
            .reset_index()
        )
        long = by_role.melt(
            id_vars=["role", "postings"], value_vars=["posted_median", "lca_median"], var_name="measure"
        )
        long["measure"] = long["measure"].map(
            {"posted_median": "Posted salary (median)", "lca_median": "Same employers' H-1B LCA wage"}
        )
        st.markdown("**By role**")
        st.altair_chart(
            alt.Chart(long.dropna())
            .mark_bar()
            .encode(
                y=alt.Y("role:N", sort="-x", title=None),
                x=alt.X("value:Q", title="Annual USD", axis=alt.Axis(format="$,.0f")),
                yOffset="measure:N",
                color=alt.Color("measure:N", title=None, legend=alt.Legend(orient="bottom")),
                tooltip=["role", "measure", alt.Tooltip("value:Q", format="$,.0f"), "postings"],
            )
            .properties(height=max(220, 46 * len(by_role))),
            width="stretch",
        )
        st.markdown("**By city** (top 15 by number of postings with a salary)")
        paid = paid.assign(
            metro=paid.apply(
                lambda r: (
                    f"{r['city']}, {r['state']}"
                    if r["city"]
                    else ("Remote (US)" if r["is_remote"] else "Other US")
                ),
                axis=1,
            )
        )
        by_city = (
            paid.groupby("metro")
            .agg(postings=("salary_mid", "size"), median=("salary_mid", "median"))
            .reset_index()
            .nlargest(15, "postings")
        )
        st.altair_chart(
            alt.Chart(by_city)
            .mark_bar()
            .encode(
                y=alt.Y("metro:N", sort="-x", title=None),
                x=alt.X("median:Q", title="Median posted salary", axis=alt.Axis(format="$,.0f")),
                tooltip=["metro", alt.Tooltip("median:Q", format="$,.0f"), "postings"],
            )
            .properties(height=420),
            width="stretch",
        )

# ── about ───────────────────────────────────────────────────────────────────
with tab_about:
    em = meta.get("employer_match", {})
    st.markdown(
        f"""
**Data freshness:** jobs snapshot **{snapshot}** (refreshed daily by GitHub Actions) ·
{meta.get("postings_fetched", 0):,} postings fetched, {meta.get("open_jobs", 0):,} in scope
(US or remote, data/ML/software roles).

**Sources**
- Job postings: public job-board APIs of Greenhouse, Lever and Ashby for {meta.get("boards", "?")}
  verified companies. No LinkedIn/Indeed scraping.
- H-1B history: [US DOL OFLC LCA disclosure data]({lca.get("source_page", "")}), FY2025
  ({lca.get("h1b_cases", 0):,} H-1B LCAs, {lca.get("employers", 0):,} employers).

**How companies are matched to LCA employers:** normalized legal names (suffixes like Inc./LLC
dropped), manual aliases for brands with different legal names (Instacart → Maplebear Inc.),
and a strict fuzzy match. **{em.get("companies_matched", 0)} of {em.get("companies_total", 0)}
companies matched ({em.get("company_match_rate", 0):.0%})**, covering
{em.get("open_jobs_with_matched_employer", 0):.0%} of open postings.

**Limitations**
- Only companies that use these three job boards are covered, so big employers on Workday,
  their own careers sites, etc. are missing.
- LCA filings ≠ hires; FY2025 data lags today's hiring; a company with no match may still sponsor.
- Visa-language, new-grad, role and salary fields are parsed with rules and can be wrong.

**Not legal advice.** H-1B history does not guarantee sponsorship.
"""
    )
