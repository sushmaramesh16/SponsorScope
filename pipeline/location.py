"""Classify free-text job locations as US / remote and pull out a primary city + state."""

from __future__ import annotations

import re
from dataclasses import dataclass

STATES = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "DC": "District of Columbia",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
}
_NAME_TO_ABBR = {v.lower(): k for k, v in STATES.items()}

# Common US tech hubs written without a state ("San Francisco", "NYC", "Bay Area").
CITY_STATE = {
    "san francisco": "CA",
    "sf": "CA",
    "bay area": "CA",
    "san francisco bay area": "CA",
    "palo alto": "CA",
    "mountain view": "CA",
    "menlo park": "CA",
    "sunnyvale": "CA",
    "san jose": "CA",
    "san mateo": "CA",
    "redwood city": "CA",
    "santa clara": "CA",
    "cupertino": "CA",
    "oakland": "CA",
    "berkeley": "CA",
    "los angeles": "CA",
    "la": "CA",
    "san diego": "CA",
    "irvine": "CA",
    "santa monica": "CA",
    "el segundo": "CA",
    "hawthorne": "CA",
    "foster city": "CA",
    "emeryville": "CA",
    "south san francisco": "CA",
    "new york": "NY",
    "new york city": "NY",
    "nyc": "NY",
    "brooklyn": "NY",
    "manhattan": "NY",
    "seattle": "WA",
    "bellevue": "WA",
    "redmond": "WA",
    "kirkland": "WA",
    "boston": "MA",
    "cambridge": "MA",
    "somerville": "MA",
    "waltham": "MA",
    "austin": "TX",
    "dallas": "TX",
    "houston": "TX",
    "san antonio": "TX",
    "plano": "TX",
    "chicago": "IL",
    "denver": "CO",
    "boulder": "CO",
    "atlanta": "GA",
    "miami": "FL",
    "washington dc": "DC",
    "washington, d.c.": "DC",
    "d.c.": "DC",
    "arlington": "VA",
    "reston": "VA",
    "pittsburgh": "PA",
    "philadelphia": "PA",
    "phoenix": "AZ",
    "salt lake city": "UT",
    "lehi": "UT",
    "portland": "OR",
    "minneapolis": "MN",
    "detroit": "MI",
    "ann arbor": "MI",
    "raleigh": "NC",
    "durham": "NC",
    "charlotte": "NC",
    "nashville": "TN",
    "columbus": "OH",
    "madison": "WI",
    "baltimore": "MD",
    "jersey city": "NJ",
    "hoboken": "NJ",
    "princeton": "NJ",
    "stamford": "CT",
    "new haven": "CT",
    "providence": "RI",
    "las vegas": "NV",
    "honolulu": "HI",
    "costa mesa": "CA",
    "long beach": "CA",
    "sacramento": "CA",
}

US_MARKERS = re.compile(
    r"\b(united states|united states of america|usa|u\.s\.a\.?|u\.s\.?|us|america|"
    r"us[- ]remote|remote[- ]us|north america)\b",
    re.I,
)
NON_US = re.compile(
    r"\b(canada|toronto|vancouver|montreal|ontario|quebec|british columbia|uk|united kingdom|"
    r"england|london|manchester|edinburgh|ireland|dublin|germany|berlin|munich|france|paris|"
    r"netherlands|amsterdam|spain|madrid|barcelona|portugal|lisbon|italy|milan|switzerland|"
    r"zurich|sweden|stockholm|denmark|copenhagen|norway|oslo|finland|helsinki|poland|warsaw|"
    r"krakow|czech|prague|romania|bucharest|ukraine|kyiv|estonia|tallinn|lithuania|serbia|"
    r"belgrade|greece|athens|israel|tel aviv|india|bangalore|bengaluru|hyderabad|pune|mumbai|"
    r"delhi|gurgaon|gurugram|noida|chennai|singapore|japan|tokyo|korea|seoul|china|beijing|"
    r"shanghai|shenzhen|hong kong|taiwan|taipei|australia|sydney|melbourne|new zealand|"
    r"auckland|mexico|mexico city|guadalajara|brazil|sao paulo|são paulo|argentina|buenos aires|"
    r"colombia|bogota|bogotá|chile|santiago|peru|lima|costa rica|uruguay|montevideo|"
    r"philippines|manila|vietnam|indonesia|jakarta|malaysia|thailand|bangkok|uae|dubai|"
    r"abu dhabi|saudi|riyadh|qatar|egypt|cairo|nigeria|lagos|kenya|nairobi|south africa|"
    r"cape town|emea|apac|latam|europe|asia|africa|anz)\b",
    re.I,
)
REMOTE = re.compile(r"\b(remote|anywhere|distributed|work from home|wfh)\b", re.I)
_ABBR = re.compile(r"(?:,|\s|-|\()\s*([A-Z]{2})\b(?!\w)")


@dataclass(frozen=True)
class Location:
    is_us: bool
    is_remote: bool
    city: str | None
    state: str | None


def _part_state(part: str) -> tuple[str | None, str | None]:
    """(city, state) for one location fragment like 'San Francisco, CA' or 'Austin, Texas'."""
    p = part.strip(" .")
    low = p.lower()
    if NON_US.search(low.replace("new mexico", "")):
        return None, None  # "Toronto, ON, CA", "Cambridge, UK"
    for m in _ABBR.finditer(p):
        if m.group(1) in STATES:
            city = p[: m.start()].strip(" ,-(")
            return (city or None), m.group(1)
    for name, abbr in _NAME_TO_ABBR.items():
        if re.search(rf"\b{re.escape(name)}\b", low):
            if name in {"washington", "georgia"} and not re.search(r",\s*" + name, low):
                continue  # "Washington" alone is ambiguous (DC / state); Georgia (country)
            city = re.split(r",", p)[0].strip()
            return (None if city.lower() == name else city), abbr
    if re.search(r"\bwashington,?\s*d\.?\s?c\b", low):
        return "Washington", "DC"
    first = re.split(r"[,(]", low)[0].strip()
    for city, abbr in CITY_STATE.items():
        if first == city or re.fullmatch(rf"(greater )?{re.escape(city)}( metro| area)?", first):
            return p.split(",")[0].split("(")[0].strip(), abbr
    return None, None


def classify(location_raw: str | None, country_hint: str | None = "", remote_hint: bool = False) -> Location:
    text = location_raw or ""
    hint = country_hint or ""
    parts = [p for p in re.split(r";|\||/|\bor\b|\n", text) if p.strip()] or [""]
    is_remote = bool(remote_hint) or bool(REMOTE.search(text))

    us_city, us_state = None, None
    any_us = False
    any_non_us = False
    for part in parts:
        city, state = _part_state(part)
        if state:
            any_us = True
            if us_state is None:
                us_city, us_state = city, state
        elif US_MARKERS.search(part):
            any_us = True
        elif NON_US.search(part.lower().replace("new mexico", "")):
            any_non_us = True

    hint_us = bool(re.search(r"\b(US|USA|United States|United States of America)\b", hint))
    hint_non_us = (
        bool(hint) and not hint_us and bool(re.fullmatch(r"[A-Z]{2}", hint.strip()) or NON_US.search(hint))
    )
    if not any_us and not any_non_us and hint_us:
        any_us = True  # the hint only decides when the location text itself is silent

    if any_us:
        is_us = True
    elif any_non_us or hint_non_us:
        is_us = False
    else:
        # "Remote" with no country: these are US-headquartered boards, so keep it as remote.
        is_us = is_remote
    if us_city and REMOTE.fullmatch(us_city.strip()):
        us_city = None
    return Location(is_us=is_us, is_remote=is_remote, city=us_city, state=us_state)
