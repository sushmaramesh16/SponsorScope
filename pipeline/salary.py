"""Parse posted pay ranges and normalize them to annual USD."""

from __future__ import annotations

import re
from dataclasses import dataclass

HOURS_PER_YEAR = 2080
_PER = {"year": 1, "month": 12, "week": 52, "hour": HOURS_PER_YEAR}
ANNUAL_MIN, ANNUAL_MAX = 20_000, 2_000_000

_NUM = r"(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*([kK])?"
_CUR = r"(?<![A-Za-z])(?:US\$|USD\s*\$?|\$)"  # not CA$, A$
_RANGE = re.compile(
    rf"{_CUR}\s*{_NUM}\s*(?:USD)?(?P<unit1>\s*(?:/\s*h(?:ou)?r|per hour|an hour))?"
    rf"\s*(?:-|–|—|to|and)\s*{_CUR}?\s*{_NUM}\s*(?:USD)?"
    r"(?P<tail>[^\n]{0,40})",
    re.I,
)
_SINGLE = re.compile(
    rf"(?:salary|pay|compensation|base)[^\n$]{{0,40}}{_CUR}\s*{_NUM}\s*(?:USD)?(?P<tail>[^\n]{{0,30}})",
    re.I,
)
_HOURLY = re.compile(r"(/\s*h(ou)?r|per hour|an hour|hourly|/hr)\b", re.I)
_MONTHLY = re.compile(r"(/\s*mo(nth)?|per month|monthly)\b", re.I)


@dataclass(frozen=True)
class Pay:
    min_annual: float | None
    max_annual: float | None
    interval: str | None  # interval as posted: year / hour / month / week


def _num(v: str, k: str | None) -> float:
    x = float(v.replace(",", ""))
    return x * 1000 if k else x


def annualize(amount: float | None, interval: str | None) -> float | None:
    if amount is None:
        return None
    return float(amount) * _PER.get(interval or "year", 1)


def _plausible(lo: float, hi: float) -> bool:
    return ANNUAL_MIN <= lo <= hi <= ANNUAL_MAX and hi <= lo * 4


def parse_pay_text(text: str | None) -> Pay:
    """Find the first plausible USD pay range in free text."""
    if not text:
        return Pay(None, None, None)
    for m in _RANGE.finditer(text):
        lo, hi = _num(m.group(1), m.group(2)), _num(m.group(4), m.group(5))  # 3 = unit1
        tail = m.group("tail") or ""
        # "$120 - $150K" -> both are thousands
        if m.group(5) and not m.group(2) and lo < 1000:
            lo *= 1000
        interval = (
            "hour"
            if m.group("unit1") or _HOURLY.search(tail) or hi < 500
            else ("month" if _MONTHLY.search(tail) else "year")
        )
        alo, ahi = annualize(lo, interval), annualize(hi, interval)
        if alo and ahi and _plausible(min(alo, ahi), max(alo, ahi)):
            return Pay(min(alo, ahi), max(alo, ahi), interval)
    for m in _SINGLE.finditer(text):
        v = _num(m.group(1), m.group(2))
        interval = "hour" if _HOURLY.search(m.group("tail") or "") or v < 500 else "year"
        a = annualize(v, interval)
        if a and _plausible(a, a):
            return Pay(a, a, interval)
    return Pay(None, None, None)


def from_structured(pay_min, pay_max, currency, interval) -> Pay:
    """Normalize ATS-provided compensation fields (Lever salaryRange, Ashby compensation)."""
    if pay_min is None or (currency and str(currency).upper() != "USD"):
        return Pay(None, None, None)
    lo = annualize(float(pay_min), interval)
    hi = annualize(float(pay_max), interval) if pay_max is not None else lo
    if lo is None or hi is None or not _plausible(min(lo, hi), max(lo, hi)):
        return Pay(None, None, None)
    return Pay(min(lo, hi), max(lo, hi), interval or "year")


def best_pay(pay_min, pay_max, currency, interval, description) -> Pay:
    p = from_structured(pay_min, pay_max, currency, interval)
    return p if p.min_annual is not None else parse_pay_text(description)
