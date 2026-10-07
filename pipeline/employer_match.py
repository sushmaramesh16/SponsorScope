"""Match job-board company names to LCA employer names.

1. Manual aliases (seeds/employer_aliases.csv) for brands whose legal name differs
   (e.g. "Cursor" -> "Anysphere").
2. Exact match on a normalized name (lowercase, no punctuation, legal suffixes dropped).
3. Fuzzy match (RapidFuzz ratio on normalized names) above a strict threshold, with a
   guard that the first word agrees, so "Ramp" never matches "Rampart Systems".
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass

from rapidfuzz import fuzz, process

FUZZY_THRESHOLD = 92

_SUFFIXES = {
    "inc",
    "incorporated",
    "llc",
    "l l c",
    "corp",
    "corporation",
    "co",
    "company",
    "ltd",
    "limited",
    "lp",
    "llp",
    "plc",
    "pbc",
    "pc",
    "na",
    "n a",
    "sa",
    "ag",
    "gmbh",
    "bv",
    "holdings",
    "holding",
    "group",
    "the",
    "usa",
    "us",
    "technologies",
    "technology",
    "tech",
    "labs",
    "lab",
    "software",
    "systems",
    "ai",
    "hq",
    "global",
    "international",
    "intl",
}
_PAREN = re.compile(r"\(.*?\)")
_NON_ALNUM = re.compile(r"[^a-z0-9 ]+")
_DBA = re.compile(r"\b(d/?b/?a|doing business as)\b.*$", re.I)


def normalize_name(name: str | None) -> str:
    """'Stripe, Inc.' -> 'stripe'; 'Scale AI, Inc.' -> 'scale'; 'Meta Platforms, Inc.' -> 'meta platforms'."""
    if not name:
        return ""
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    s = _DBA.sub("", s)
    s = _PAREN.sub(" ", s).lower().replace("&", " and ")
    s = s.replace(".", "").replace("'", "")
    s = _NON_ALNUM.sub(" ", s)
    words = s.split()
    # strip suffix words from the end, but never strip the name down to nothing
    while len(words) > 1 and words[-1] in _SUFFIXES:
        words.pop()
    while len(words) > 1 and words[0] == "the":
        words.pop(0)
    return " ".join(words)


@dataclass(frozen=True)
class Match:
    company: str
    employer_norm: str | None
    method: str  # alias | exact | fuzzy | blocked | none
    score: float


def match_companies(
    companies: Iterable[str],
    employer_norms: Iterable[str],
    aliases: dict[str, str] | None = None,
    threshold: int = FUZZY_THRESHOLD,
) -> list[Match]:
    """Match each company (display name) to one normalized LCA employer name."""
    pool = sorted(set(e for e in employer_norms if e))
    pool_set = set(pool)
    by_first: dict[str, list[str]] = {}
    for e in pool:
        by_first.setdefault(e.split()[0], []).append(e)
    # an alias of "-" blocks a known false match ("Gamma" the app vs Gamma Technologies LLC)
    aliases = {k.lower(): (v if v == "-" else normalize_name(v)) for k, v in (aliases or {}).items()}

    out = []
    for c in companies:
        alias = aliases.get(c.lower())
        if alias == "-":
            out.append(Match(c, None, "blocked", 0.0))
            continue
        if alias and alias in pool_set:
            out.append(Match(c, alias, "alias", 100.0))
            continue
        n = normalize_name(c)
        if n in pool_set:
            out.append(Match(c, n, "exact", 100.0))
            continue
        cands = by_first.get(n.split()[0], []) if n else []
        best = process.extractOne(n, cands, scorer=fuzz.ratio, score_cutoff=threshold) if cands else None
        if best:
            out.append(Match(c, best[0], "fuzzy", float(best[1])))
        else:
            out.append(Match(c, None, "none", 0.0))
    return out
