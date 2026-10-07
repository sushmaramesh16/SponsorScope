"""Job-board parsers, with the HTTP layer stubbed out."""

import pytest

from pipeline import boards


@pytest.fixture
def stub(monkeypatch):
    def install(payload):
        monkeypatch.setattr(boards, "get_json", lambda url, params=None: payload)

    return install


def test_html_to_text_unescapes_greenhouse_double_encoding():
    raw = "&lt;p&gt;Hello &amp;amp; welcome&lt;/p&gt;&lt;ul&gt;&lt;li&gt;Python&lt;/li&gt;&lt;/ul&gt;"
    assert boards.html_to_text(raw) == "Hello & welcome\nPython"


def test_greenhouse(stub):
    stub(
        {
            "jobs": [
                {
                    "id": 123,
                    "title": " Data Scientist ",
                    "location": {"name": "New York, NY"},
                    "offices": [{"name": "NYC", "location": "New York, NY, United States"}],
                    "departments": [{"name": "Data"}],
                    "first_published": "2026-09-01T10:00:00-04:00",
                    "updated_at": "2026-09-05T10:00:00-04:00",
                    "absolute_url": "https://x/123",
                    "content": "&lt;p&gt;We sponsor visas.&lt;/p&gt;",
                    "metadata": [{"name": "Workplace Type", "value": "Remote"}],
                }
            ]
        }
    )
    [r] = boards.greenhouse_jobs("acme", "Acme")
    assert r["job_id"] == "123" and r["title"] == "Data Scientist"
    assert r["posted_at"].startswith("2026-09-01T14:00")
    assert r["remote_hint"] is True
    assert r["description"] == "We sponsor visas."
    assert r["apply_url"] == "https://x/123"


def test_lever(stub):
    stub(
        [
            {
                "id": "abc",
                "text": "Backend Engineer",
                "createdAt": 1767225600000,
                "categories": {
                    "location": "Austin, TX",
                    "allLocations": ["Austin, TX"],
                    "team": "Eng",
                    "commitment": "Full-time",
                },
                "country": "US",
                "workplaceType": "onsite",
                "hostedUrl": "https://jobs.lever.co/acme/abc",
                "descriptionPlain": "Build APIs.",
                "lists": [{"text": "Requirements", "content": "<li>Go</li>"}],
                "additionalPlain": "",
                "salaryRange": {
                    "min": 150000,
                    "max": 180000,
                    "currency": "USD",
                    "interval": "per-year-salary",
                },
            }
        ]
    )
    [r] = boards.lever_jobs("acme", "Acme")
    assert r["posted_at"].startswith("2026-01-01")
    assert (r["pay_min"], r["pay_max"], r["pay_interval"]) == (150000, 180000, "year")
    assert "Requirements" in r["description"] and "Go" in r["description"]


def test_ashby_skips_unlisted_and_reads_compensation(stub):
    comp = {
        "summaryComponents": [
            {"compensationType": "EquityPercentage", "minValue": None},
            {
                "compensationType": "Salary",
                "interval": "1 YEAR",
                "currencyCode": "USD",
                "minValue": 200000,
                "maxValue": 250000,
            },
        ]
    }
    stub(
        {
            "jobs": [
                {
                    "id": "1",
                    "title": "ML Engineer",
                    "isListed": True,
                    "isRemote": True,
                    "location": "Remote (US)",
                    "secondaryLocations": [{"location": "New York, NY"}],
                    "address": {"postalAddress": {"addressCountry": "USA"}},
                    "publishedAt": "2026-09-01T00:00:00Z",
                    "jobUrl": "https://jobs.ashbyhq.com/acme/1",
                    "descriptionPlain": "Hi",
                    "compensation": comp,
                },
                {"id": "2", "title": "Hidden", "isListed": False},
            ]
        }
    )
    [r] = boards.ashby_jobs("acme", "Acme")
    assert r["location_raw"] == "Remote (US); New York, NY"
    assert r["country_hint"] == "USA"
    assert (r["pay_min"], r["pay_max"], r["pay_currency"]) == (200000, 250000, "USD")


def test_404_board_returns_empty(stub):
    stub(None)
    assert boards.greenhouse_jobs("gone", "Gone") == []
    assert boards.lever_jobs("gone", "Gone") == []
    assert boards.ashby_jobs("gone", "Gone") == []
