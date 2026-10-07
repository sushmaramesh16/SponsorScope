"""Flag postings that are open to new grads / early-career candidates (0–2 years)."""

from __future__ import annotations

import re

_TITLE_YES = re.compile(
    r"\b(new grad\w*|new college grad\w*|university grad\w*|recent grad\w*|graduate (software|data|"
    r"machine learning|ml)|early[- ]career|entry[- ]level|junior|jr\.?|apprentice|associate (software|"
    r"data|machine learning|ml)|(engineer|scientist|analyst|developer)\s+(i|1)\b|level\s*(i|1)\b|"
    r"class of 20\d\d|20\d\d (start|grad\w*))",
    re.I,
)
_TITLE_NO = re.compile(
    r"\b(senior|sr\.?|staff|principal|lead|manager|director|head|architect|distinguished|fellow|"
    r"(engineer|scientist|analyst|developer)\s+(ii|iii|iv|2|3|4|5))\b",
    re.I,
)
_INTERN = re.compile(r"\b(intern|internship|co-?op|summer associate)\b", re.I)

_DESC_YES = re.compile(
    r"\b(new grad\w*|recent (college |university )?grad\w*|entry[- ]level|early[- ]career|"
    r"graduating (in|by) (20\d\d|spring|summer|fall|winter|december|may)|"
    r"no (prior )?(professional |industry )?experience (is )?required)\b",
    re.I,
)
# "0-2 years", "0 to 2 years", "1+ years", "up to 2 years", "at least 3 years", "5+ yrs"
_YEARS = re.compile(
    r"(?:(?P<atleast>at least|minimum of|min\.?|minimum)\s+)?"
    r"(?P<lo>\d{1,2})(?:\.\d)?\s*(?:\+|plus)?\s*(?:(?:-|–|—|to)\s*(?P<hi>\d{1,2})\s*\+?)?\s*"
    r"(?:years?|yrs?)\b(?P<ctx>[^.\n]{0,60})",
    re.I,
)
_UP_TO = re.compile(r"\bup to\s+(\d{1,2})\s*(?:years?|yrs?)", re.I)
_EXPERIENCE_CTX = re.compile(r"experience|industry|professional|working|work", re.I)


def is_internship(title: str | None) -> bool:
    return bool(title and _INTERN.search(title))


def min_years_required(text: str | None) -> int | None:
    """Largest 'minimum years of experience' mentioned (the binding requirement), or None."""
    if not text:
        return None
    mins = []
    for m in _YEARS.finditer(text):
        if not _EXPERIENCE_CTX.search(m.group("ctx") or ""):
            continue
        if re.search(r"up to\s*$", text[max(0, m.start() - 8) : m.start()], re.I):
            continue  # counted by _UP_TO
        lo = int(m.group("lo"))
        if lo > 25:
            continue
        mins.append(lo)
    mins.extend(0 for _ in _UP_TO.finditer(text))
    return max(mins) if mins else None


def is_new_grad(title: str | None, description: str | None = "") -> bool:
    title = title or ""
    if is_internship(title) or _TITLE_NO.search(title):
        return False
    if _TITLE_YES.search(title):
        return True
    yrs = min_years_required(description)
    if yrs is not None:
        return yrs <= 1  # "0-2 years", "1+ years", "up to 2 years"; not "2+ years"
    return bool(description and _DESC_YES.search(description))
