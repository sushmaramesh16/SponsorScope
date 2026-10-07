"""Map free-text job titles to a small set of role families (or None if out of scope)."""

from __future__ import annotations

import re

ROLES = (
    "Data Scientist",
    "Data Engineer",
    "ML Engineer",
    "AI Engineer",
    "Data Analyst",
    "Analytics Engineer",
    "Research Scientist",
    "Software Engineer",
    "Backend Engineer",
    "Frontend Engineer",
    "Full-Stack Engineer",
    "Mobile Engineer",
    "Platform / DevOps / SRE",
)

# Titles we never treat as an individual-contributor tech role, even if they mention one.
_EXCLUDE = re.compile(
    r"\b(manager|director|head of|vp|vice president|chief|recruit\w*|sourcer|sales|account"
    r"|solutions? (engineer|architect)|sales engineer|support engineer|customer|consultant"
    r"|technician|counsel|attorney|designer|marketing|product manager|program manager"
    r"|project manager|teacher|tutor|writer|trainer|annotator|contractor - data labeling)\b",
    re.I,
)


def _eng(topic: str) -> re.Pattern:
    """Title mentions `topic` and engineer/developer, in either order."""
    return re.compile(rf"(?=.*\b({topic})(?!\w))(?=.*\b(engineer|developer)\b)", re.I)


_RULES: list[tuple[str, re.Pattern]] = [
    ("Analytics Engineer", re.compile(r"\banalytics engineer", re.I)),
    (
        "Data Engineer",
        re.compile(
            r"\bdata (platform |infrastructure |pipeline |quality |reliability )?engineer"
            r"|\bbig data\b|\betl (developer|engineer)|\bdata warehouse (engineer|developer)",
            re.I,
        ),
    ),
    (
        "Research Scientist",
        re.compile(
            r"\b(research scientist|research engineer|applied scientist|ml researcher"
            r"|ai researcher|member of technical staff.*research|research.*(ml|ai))\b",
            re.I,
        ),
    ),
    (
        "ML Engineer",
        re.compile(
            _eng(
                r"machine learning|ml|mlops|ml ops|deep learning|computer vision|nlp|perception"
                r"|recommendation|ranking|inference"
            ).pattern
            + r"|\bmle\b",
            re.I,
        ),
    ),
    ("AI Engineer", _eng(r"ai|a\.i\.|genai|gen ai|generative ai|llm|applied ai|agents?|agentic")),
    (
        "Data Scientist",
        re.compile(
            r"\bdata scien\w*|\bdecision scien\w*|\bquantitative (researcher|analyst)\b"
            r"|\bstatistician\b|\beconomist\b",
            re.I,
        ),
    ),
    (
        "Data Analyst",
        re.compile(
            r"\b(data|business intelligence|bi|product|business|reporting|insights?|growth)"
            r" analyst\b|\banalyst\b.*\b(data|analytics)\b|\banalytics\b.*\banalyst",
            re.I,
        ),
    ),
    ("Full-Stack Engineer", re.compile(r"\bfull[- ]?stack\b", re.I)),
    ("Mobile Engineer", _eng(r"ios|android|mobile|react native|flutter")),
    ("Frontend Engineer", _eng(r"front[- ]?end|ui|web|react|javascript|typescript")),
    (
        "Backend Engineer",
        _eng(r"back[- ]?end|server[- ]side|api|distributed systems|java|golang|scala|rust|c\+\+"),
    ),
    (
        "Platform / DevOps / SRE",
        re.compile(
            _eng(
                r"devops|dev ops|site reliability|sre|platform|infrastructure|cloud|reliability"
                r"|kubernetes"
            ).pattern
            + r"|\bsre\b",
            re.I,
        ),
    ),
    (
        "Software Engineer",
        re.compile(
            r"\bsoftware (development )?(engineer|developer)|\bswe\b|\bsde\b|\bmember of technical staff"
            r"|\bdeveloper\b|\bprogrammer\b|\b(product|application|security|staff|senior|founding)"
            r" engineer\b|^engineer\b",
            re.I,
        ),
    ),
]

# Hardware-ish engineering titles that the generic rules above would otherwise catch
# ("ASIC RTL Design Engineer, AI Hardware" is not an AI engineer).
_NON_SOFTWARE = re.compile(
    r"\b(mechanical|electrical|hardware|rf|asic|rtl|fpga|analog|manufacturing|process|chemical"
    r"|civil|structural|propulsion|avionics|materials|optical|thermal|firmware|embedded|silicon"
    r"|facilities|field|safety|design verification|(test|quality|validation|network) engineer)\b",
    re.I,
)
_DATA_ROLES = {"Data Scientist", "Data Engineer", "Data Analyst", "Analytics Engineer"}
_IT = re.compile(r"\bIT\b")  # IT / helpdesk titles (case-sensitive: "IT", not "it")


def normalize_role(title: str | None) -> str | None:
    if not title:
        return None
    t = " ".join(title.replace("/", " / ").split())
    if _EXCLUDE.search(t) or _IT.search(t):
        return None
    for role, pat in _RULES:
        if pat.search(t):
            if (
                role not in _DATA_ROLES
                and _NON_SOFTWARE.search(t)
                and not re.search(r"\bsoftware\b", t, re.I)
            ):
                return None
            return role
    return None


ROLE_GROUP = {
    r: "Data & ML"
    if r in {*_DATA_ROLES, "ML Engineer", "AI Engineer", "Research Scientist"}
    else "Software Engineering"
    for r in ROLES
}
