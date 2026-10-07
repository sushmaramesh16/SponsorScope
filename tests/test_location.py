import pytest

from pipeline.location import classify


@pytest.mark.parametrize(
    "raw,hint,remote,is_us,is_remote,city,state",
    [
        ("San Francisco, CA", "", False, True, False, "San Francisco", "CA"),
        ("Austin, Texas, United States", "", False, True, False, "Austin", "TX"),
        ("New York City", "", False, True, False, "New York City", "NY"),
        ("Remote - US", "", False, True, True, None, None),
        ("Remote (USA)", "", False, True, True, None, None),
        ("Remote", "", False, True, True, None, None),
        ("Remote Canada", "Remote Canada; Remote US", False, False, True, None, None),
        ("London, United Kingdom", "", False, False, False, None, None),
        ("Toronto, ON, CA", "", False, False, False, None, None),
        ("Bengaluru, India", "", False, False, False, None, None),
        ("Seattle, WA; London, UK", "", False, True, False, "Seattle", "WA"),
        ("Washington, D.C.", "", False, True, False, "Washington", "DC"),
        ("Albuquerque, New Mexico", "", False, True, False, "Albuquerque", "NM"),
        ("Hybrid", "US", False, True, False, None, None),
        ("Hybrid", "CA", False, False, False, None, None),
        ("New York, NY", "", True, True, True, "New York", "NY"),
    ],
)
def test_classify(raw, hint, remote, is_us, is_remote, city, state):
    loc = classify(raw, hint, remote)
    assert (loc.is_us, loc.is_remote, loc.city, loc.state) == (is_us, is_remote, city, state)
