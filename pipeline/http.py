"""Polite HTTP: shared session, timeouts, retries with backoff, per-host rate limit."""

from __future__ import annotations

import threading
import time
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

USER_AGENT = "SponsorScope/0.1 (+https://github.com/sushmaramesh16/SponsorScope; job-board API client)"
TIMEOUT = (10, 45)  # connect, read
MIN_INTERVAL = 0.25  # seconds between requests to the same host (~4 req/s)

_local = threading.local()
_host_lock = threading.Lock()
_host_next: dict[str, float] = {}


def _session() -> requests.Session:
    s = getattr(_local, "session", None)
    if s is None:
        s = requests.Session()
        retry = Retry(
            total=4,
            backoff_factor=1.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
            respect_retry_after_header=True,
        )
        s.mount("https://", HTTPAdapter(max_retries=retry, pool_maxsize=8))
        s.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
        _local.session = s
    return s


def _throttle(url: str) -> None:
    host = urlparse(url).netloc
    with _host_lock:
        now = time.monotonic()
        start = max(now, _host_next.get(host, now))
        _host_next[host] = start + MIN_INTERVAL
    delay = start - time.monotonic()
    if delay > 0:
        time.sleep(delay)


def get_json(url: str, params: dict | None = None):
    """GET a JSON document. Returns None on 404; raises on other failures."""
    _throttle(url)
    r = _session().get(url, params=params, timeout=TIMEOUT)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()
