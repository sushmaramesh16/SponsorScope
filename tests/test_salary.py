import pytest

from pipeline.salary import best_pay, from_structured, parse_pay_text


@pytest.mark.parametrize(
    "text,lo,hi,interval",
    [
        ("The base salary range is $120,000 - $150,000 per year.", 120_000, 150_000, "year"),
        ("Pay range: $120K–$150K", 120_000, 150_000, "year"),
        ("Salary: $145,000 — $175,000 USD", 145_000, 175_000, "year"),
        ("USD 130,000 to 160,000", 130_000, 160_000, "year"),
        ("$120 - $150K base", 120_000, 150_000, "year"),
        ("Hourly rate: $40/hr - $50/hr", 40 * 2080, 50 * 2080, "hour"),
        ("$45 - $55 per hour", 45 * 2080, 55 * 2080, "hour"),
        ("$211.4K - $290.6K", 211_400, 290_600, "year"),
        ("The annual base salary for this role is $185,000.", 185_000, 185_000, "year"),
    ],
)
def test_parse_text(text, lo, hi, interval):
    p = parse_pay_text(text)
    assert (p.min_annual, p.max_annual, p.interval) == (pytest.approx(lo), pytest.approx(hi), interval)


@pytest.mark.parametrize(
    "text",
    [
        "",
        None,
        "We raised $100M in Series C funding.",  # single number, no pay keyword
        "CA$120,000 - CA$150,000",  # not USD
        "$5 - $10 off your next order",  # implausible
        "Our 401(k) match is up to $5,000 - $10,000 per year.",
    ],
)
def test_parse_text_none(text):
    assert parse_pay_text(text).min_annual is None


def test_structured_annual_and_hourly():
    assert from_structured(100000, 140000, "USD", "year").max_annual == 140000
    assert from_structured(50, 60, "USD", "hour").min_annual == 50 * 2080
    assert from_structured(100000, 140000, "EUR", "year").min_annual is None


def test_best_pay_prefers_structured():
    p = best_pay(100000, 120000, "USD", "year", "Salary: $1,000,000 - $1,200,000")
    assert p.min_annual == 100000
    p = best_pay(None, None, None, None, "Salary: $130,000 - $150,000")
    assert p.min_annual == 130000
