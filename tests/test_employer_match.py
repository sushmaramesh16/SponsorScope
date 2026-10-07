import pytest

from pipeline.employer_match import match_companies, normalize_name


@pytest.mark.parametrize(
    "raw,norm",
    [
        ("Stripe, Inc.", "stripe"),
        ("STRIPE INC", "stripe"),
        ("Scale AI, Inc.", "scale"),
        ("Meta Platforms, Inc.", "meta platforms"),
        ("Cockroach Labs, Inc.", "cockroach"),
        ("Google LLC", "google"),
        ("The Walt Disney Company", "walt disney"),
        ("RealTimeBoard, Inc. dba Miro", "realtimeboard"),
        ("Ōura Health Oy", "oura health oy"),
        ("AT&T Services, Inc.", "at and t services"),
        ("Inc.", "inc"),  # never normalized to empty
        ("", ""),
    ],
)
def test_normalize(raw, norm):
    assert normalize_name(raw) == norm


POOL = [
    "stripe",
    "databricks",
    "openai opco",
    "rampart systems design",
    "ramp business",
    "airbnb",
    "maplebear",
    "lucid",
    "data bricks consulting",
]


def by_company(matches):
    return {m.company: m for m in matches}


def test_exact_and_alias():
    m = by_company(
        match_companies(["Stripe", "Instacart", "Airbnb, Inc."], POOL, {"Instacart": "Maplebear Inc."})
    )
    assert (m["Stripe"].employer_norm, m["Stripe"].method) == ("stripe", "exact")
    assert (m["Instacart"].employer_norm, m["Instacart"].method) == ("maplebear", "alias")
    assert m["Airbnb, Inc."].employer_norm == "airbnb"


def test_fuzzy_handles_small_spelling_differences():
    m = by_company(match_companies(["Data Brick"], ["data bricks"]))
    assert m["Data Brick"].method == "fuzzy"
    assert m["Data Brick"].employer_norm == "data bricks"


def test_no_false_positive_on_shared_prefix():
    m = by_company(match_companies(["Ramp", "Lucid Motors"], POOL))
    assert m["Ramp"].employer_norm is None  # not "rampart systems design" or "ramp business"
    assert m["Lucid Motors"].employer_norm is None  # needs an alias, not a guess


def test_block_alias():
    m = by_company(match_companies(["Gamma"], ["gamma"], {"Gamma": "-"}))
    assert (m["Gamma"].employer_norm, m["Gamma"].method) == (None, "blocked")


def test_alias_to_unknown_employer_falls_back():
    m = by_company(match_companies(["Stripe"], POOL, {"Stripe": "Nonexistent Corp"}))
    assert m["Stripe"].employer_norm == "stripe"
