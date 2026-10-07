"""Clients for the three public job-board APIs, normalized to one posting record.

Greenhouse: https://developers.greenhouse.io/job-board.html
Lever:      https://github.com/lever/postings-api
Ashby:      https://developers.ashbyhq.com/docs/public-job-posting-api
"""

from __future__ import annotations

import html
import re
from datetime import UTC, datetime

from pipeline.http import get_json

ATS = ("greenhouse", "lever", "ashby")

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"[ \t\r\f\v]+")
_BLOCK = re.compile(r"</?(p|div|br|li|ul|ol|h[1-6]|tr)\b[^>]*>", re.I)


def html_to_text(s: str | None) -> str:
    if not s:
        return ""
    s = html.unescape(s)  # Greenhouse double-escapes its HTML
    s = _BLOCK.sub("\n", s)
    s = html.unescape(_TAG.sub(" ", s))
    lines = (_WS.sub(" ", ln).strip() for ln in s.splitlines())
    return "\n".join(ln for ln in lines if ln)


def _iso(v) -> str | None:
    if v is None or v == "":
        return None
    if isinstance(v, int | float):  # Lever: epoch milliseconds
        return datetime.fromtimestamp(v / 1000, tz=UTC).isoformat()
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00")).astimezone(UTC).isoformat()
    except ValueError:
        return None


def _record(**kw) -> dict:
    base = dict.fromkeys(
        [
            "ats",
            "board_token",
            "company_name",
            "job_id",
            "title",
            "location_raw",
            "country_hint",
            "remote_hint",
            "department",
            "employment_type",
            "posted_at",
            "updated_at",
            "apply_url",
            "description",
            "pay_min",
            "pay_max",
            "pay_currency",
            "pay_interval",
        ]
    )
    base.update(kw)
    return base


# ── Greenhouse ──────────────────────────────────────────────────────────────


def greenhouse_board(token: str):
    return get_json(f"https://boards-api.greenhouse.io/v1/boards/{token}")


def greenhouse_jobs(token: str, company: str) -> list[dict]:
    data = get_json(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs", {"content": "true"})
    if not data:
        return []
    out = []
    for j in data.get("jobs", []):
        offices = "; ".join(o.get("location") or o.get("name") or "" for o in j.get("offices") or [])
        loc = (j.get("location") or {}).get("name") or ""
        workplace = next(
            (
                str(m.get("value"))
                for m in j.get("metadata") or []
                if "workplace" in (m.get("name") or "").lower() and m.get("value")
            ),
            "",
        )
        out.append(
            _record(
                ats="greenhouse",
                board_token=token,
                company_name=company,
                job_id=str(j["id"]),
                title=(j.get("title") or "").strip(),
                location_raw=loc if loc else offices,
                country_hint=offices,
                remote_hint="remote" in workplace.lower(),
                department="; ".join(d.get("name", "") for d in j.get("departments") or []),
                posted_at=_iso(j.get("first_published")) or _iso(j.get("updated_at")),
                updated_at=_iso(j.get("updated_at")),
                apply_url=j.get("absolute_url"),
                description=html_to_text(j.get("content")),
            )
        )
    return out


# ── Lever ───────────────────────────────────────────────────────────────────

_LEVER_INTERVAL = {"per-year-salary": "year", "per-month-salary": "month", "per-hour-wage": "hour"}


def lever_jobs(token: str, company: str) -> list[dict]:
    data = get_json(f"https://api.lever.co/v0/postings/{token}", {"mode": "json"})
    if not data:
        return []
    out = []
    for j in data:
        cat = j.get("categories") or {}
        lists = "\n".join(
            f"{x.get('text', '')}\n{html_to_text(x.get('content'))}" for x in j.get("lists") or []
        )
        desc = "\n".join(
            p for p in (j.get("descriptionPlain") or "", lists, j.get("additionalPlain") or "") if p
        )
        sal = j.get("salaryRange") or {}
        out.append(
            _record(
                ats="lever",
                board_token=token,
                company_name=company,
                job_id=j["id"],
                title=(j.get("text") or "").strip(),
                location_raw="; ".join(cat.get("allLocations") or []) or cat.get("location") or "",
                country_hint=j.get("country") or "",
                remote_hint=(j.get("workplaceType") or "").lower() == "remote",
                department=cat.get("team") or cat.get("department") or "",
                employment_type=cat.get("commitment"),
                posted_at=_iso(j.get("createdAt")),
                updated_at=_iso(j.get("createdAt")),
                apply_url=j.get("hostedUrl") or j.get("applyUrl"),
                description=desc,
                pay_min=sal.get("min"),
                pay_max=sal.get("max"),
                pay_currency=sal.get("currency"),
                pay_interval=_LEVER_INTERVAL.get(sal.get("interval") or ""),
            )
        )
    return out


# ── Ashby ───────────────────────────────────────────────────────────────────

_ASHBY_INTERVAL = {"1 YEAR": "year", "1 MONTH": "month", "1 HOUR": "hour", "1 WEEK": "week"}


def _ashby_loc(x: dict) -> tuple[str, str]:
    addr = ((x.get("address") or {}).get("postalAddress")) or {}
    return x.get("location") or "", addr.get("addressCountry") or ""


def ashby_jobs(token: str, company: str) -> list[dict]:
    data = get_json(f"https://api.ashbyhq.com/posting-api/job-board/{token}", {"includeCompensation": "true"})
    if not data:
        return []
    out = []
    for j in data.get("jobs", []):
        if j.get("isListed") is False:
            continue
        locs = [_ashby_loc(j)] + [_ashby_loc(x) for x in j.get("secondaryLocations") or []]
        salary = next(
            (
                c
                for c in ((j.get("compensation") or {}).get("summaryComponents") or [])
                if c.get("compensationType") == "Salary" and c.get("minValue")
            ),
            {},
        )
        out.append(
            _record(
                ats="ashby",
                board_token=token,
                company_name=company,
                job_id=j["id"],
                title=(j.get("title") or "").strip(),
                location_raw="; ".join(dict.fromkeys(name for name, _ in locs if name)),
                country_hint="; ".join(dict.fromkeys(c for _, c in locs if c)),
                remote_hint=bool(j.get("isRemote")) or (j.get("workplaceType") or "") == "Remote",
                department=j.get("department") or j.get("team") or "",
                employment_type=j.get("employmentType"),
                posted_at=_iso(j.get("publishedAt")),
                updated_at=_iso(j.get("publishedAt")),
                apply_url=j.get("jobUrl") or j.get("applyUrl"),
                description=j.get("descriptionPlain") or html_to_text(j.get("descriptionHtml")),
                pay_min=salary.get("minValue"),
                pay_max=salary.get("maxValue"),
                pay_currency=salary.get("currencyCode"),
                pay_interval=_ASHBY_INTERVAL.get(salary.get("interval") or ""),
            )
        )
    return out


FETCHERS = {"greenhouse": greenhouse_jobs, "lever": lever_jobs, "ashby": ashby_jobs}


def fetch_board(ats: str, token: str, company: str) -> list[dict]:
    return FETCHERS[ats](token, company)
