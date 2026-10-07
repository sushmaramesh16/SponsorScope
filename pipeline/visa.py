"""Rule-based detector for visa-sponsorship language in a job description.

Returns one of:
  "no sponsorship"         - the posting says it will not sponsor (or requires US citizenship)
  "sponsorship available"  - the posting says sponsorship is (or may be) available
  "not mentioned"          - nothing decisive either way

Works sentence by sentence. Only sentences that talk about sponsorship / visas / work
authorization / citizenship are considered, application-form questions ("Will you now or
in the future require sponsorship?") are ignored, and a negative statement anywhere wins
over a positive one (conservative: better to under-promise).
"""

from __future__ import annotations

import re

NO = "no sponsorship"
YES = "sponsorship available"
NONE = "not mentioned"
LABELS = (NO, YES, NONE)

# Sentence breaks, but not after abbreviations like "U.S." or "e.g.".
_SENT_SPLIT = re.compile(r"(?<=[.!?])(?<!U\.S\.)(?<!u\.s\.)(?<!e\.g\.)(?<!i\.e\.)(?<!Inc\.)\s+|\n+|•|·|;")
_TOPIC = re.compile(
    r"sponsor|visa|h-?1-?b|immigration|work authori[sz]ation|authori[sz]ed to work|"
    r"citizen|green card|permanent resident|security clearance|opt\b|stem opt|cpt\b",
    re.I,
)
_SPONSOR = r"(?:visa|h-?1-?b|immigration|employment|work(?:\s+visa)?|green\s+card)?\s*sponsor\w*"

_NEG = [
    # "unable to / cannot / will not / do not / are not able to sponsor"
    re.compile(
        r"\b(unable|not able|cannot|can ?not|can't|won't|will not|do not|don't|does not|"
        r"doesn't|are not|is not|aren't|isn't|not in a position|no longer|never)\b"
        r"[\w\s,'/-]{0,40}?\bsponsor",
        re.I,
    ),
    # "no (visa) sponsorship", "sponsorship is not available / not offered / not provided"
    re.compile(r"\bno\s+" + _SPONSOR, re.I),
    re.compile(
        r"\bsponsorship\b[\w\s,()'/-]{0,40}?\b(is|are|will be|would be)?\s*"
        r"(not|un)\s*(available|offered|provided|possible|supported|an option|considered)",
        re.I,
    ),
    re.compile(
        r"\bnot\s+(be\s+)?(eligible|available|offering|providing|offer|provide|considered)"
        r"[\w\s,'/-]{0,30}?\bsponsor",
        re.I,
    ),
    re.compile(r"\bineligible\b[\w\s,'/-]{0,30}?\bsponsor", re.I),
    # "may not be able to employ ... or support future H-1B sponsorship at this time"
    re.compile(
        r"\b(not|unable|cannot|can't|won't)\b.{0,160}?\bsupport\b[\w\s-]{0,20}"
        r"\bsponsorship",
        re.I,
    ),
    # "must be authorized to work ... without (current or future) sponsorship"
    re.compile(r"\bwithout\b[\w\s,()'/-]{0,40}?\bsponsor", re.I),
    re.compile(
        r"\b(require|need)s?\b[\w\s,()'/-]{0,40}?\bsponsor\w*[\w\s,()'/-]{0,40}?\b"
        r"(will not|won't|not|cannot|ineligible)\b[\w\s]{0,20}\b(considered|eligible|accepted)",
        re.I,
    ),
    # citizenship / clearance requirements
    re.compile(
        r"\b(must|required to|need to|requires?|requirement)\b[\w\s,'/-]{0,30}?\b"
        r"(be\s+(a\s+)?)?(u\.?s\.?|united states)\s+(citizen|person)",
        re.I,
    ),
    re.compile(r"\b(u\.?s\.?|united states)\s+citizenship\s+(is\s+)?(required|mandatory|needed)", re.I),
    re.compile(r"\b(only|open only to)\s+(u\.?s\.?|united states)\s+citizens", re.I),
    re.compile(
        r"\b(requires?|required|must (have|hold|obtain|be able to obtain))\b[\w\s,'/-]{0,30}?"
        r"(\b(security|secret|top secret)\s+clearance|\bts/sci\b)",
        re.I,
    ),
]

_POS = [
    re.compile(
        r"\b(we|company|employer)\s+(do|does|will|can|are able to|is able to|are happy to|"
        r"are open to|offer to|may)\s+(also\s+)?sponsor",
        re.I,
    ),
    re.compile(r"\b(we|they)\s+sponsor\b", re.I),
    re.compile(
        r"\b(visa|h-?1-?b|immigration)\s+sponsorship\b[\w\s,()'/-]{0,30}?"
        r"\b(is|are|will be|may be|can be)?\s*(available|offered|provided|possible|supported)",
        re.I,
    ),
    re.compile(
        r"\bsponsorship\s+(is\s+|may be\s+|will be\s+|can be\s+)?"
        r"(available|offered|provided|possible|supported)",
        re.I,
    ),
    re.compile(
        r"\b(offer|offers|provide|provides|providing|offering|support|supports)\s+"
        r"(visa\s+|h-?1-?b\s+|immigration\s+)?(sponsorship|visa)",
        re.I,
    ),
    re.compile(r"\b(open|willing|happy|able)\s+to\s+sponsor", re.I),
    re.compile(
        r"\bh-?1-?b\s+(transfers?|sponsorship)\s+(are\s+|is\s+)?(welcome|supported|accepted|available)", re.I
    ),
    re.compile(r"\bvisa\s+sponsorship\s*[:\-]\s*(yes|available)", re.I),
    re.compile(r"\bsponsorship\s+(is\s+)?(an option|on the table)", re.I),
    re.compile(
        r"\bvisa sponsorship\s+(where|when|if|as)\s+(applicable|available|needed|eligible|"
        r"required|appropriate)",
        re.I,
    ),
    re.compile(r"\b(relocation|immigration)\b[\w\s]{0,25}\b(and|&)\s+(visa|h-?1-?b)\s+sponsorship", re.I),
]
# Hedges that limit a refusal to *other* roles or candidates ("not for every role",
# "for roles outside of engineering") - not a refusal for this posting.
_HEDGE = re.compile(
    r"\bfor (every|all|each) (role|position|candidate)s?\b|\boutside (of )?(engineering|"
    r"the us|the united states)|\bevery role and every candidate|\bin (all|every) cases?\b",
    re.I,
)
# Not about the candidate's visa: export licenses, "desired"/"preferred" clearances.
_IGNORE = re.compile(r"\bexport licen[sc]e|\bclearance\b[^.]{0,20}\b(desired|preferred|a plus|plus)\b", re.I)
_NEG_INLINE = re.compile(r"\b(visa\s+)?sponsorship\s*[:\-]\s*(no|none|not available|n/a)\b", re.I)


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT_SPLIT.split(text) if s and s.strip()]


def _is_question(s: str) -> bool:
    return s.rstrip().endswith("?") or bool(
        re.match(r"^(will|do|are|would|have|can)\s+you\b", s.strip(), re.I)
    )


def _is_eeo_boilerplate(s: str) -> bool:
    # "...without regard to race, ..., citizenship status, ..." is not a requirement.
    return bool(
        re.search(r"\b(regard(less)? (to|of)|discriminat\w*|protected)\b", s, re.I)
    ) and not re.search(r"sponsor", s, re.I)


def classify_visa_language(text: str | None) -> str:
    if not text:
        return NONE
    neg = pos = False
    for s in _sentences(text):
        if not _TOPIC.search(s) or _is_question(s) or _is_eeo_boilerplate(s) or _IGNORE.search(s):
            continue
        if _NEG_INLINE.search(s) or (any(p.search(s) for p in _NEG) and not _HEDGE.search(s)):
            neg = True
        elif any(p.search(s) for p in _POS):
            pos = True
    if neg:
        return NO
    if pos:
        return YES
    return NONE
