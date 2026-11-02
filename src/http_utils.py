"""Tiện ích HTTP dùng chung: session có retry + rate limit lịch sự."""
import time
import requests
from requests.adapters import HTTPAdapter, Retry

from . import config

_last_request_ts = {"t": 0.0}


def get_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": config.USER_AGENT, "Accept": "application/json"})
    retries = Retry(total=5, backoff_factor=1.0, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session


def polite_wait():
    elapsed = time.time() - _last_request_ts["t"]
    if elapsed < config.REQUEST_DELAY_SEC:
        time.sleep(config.REQUEST_DELAY_SEC - elapsed)
    _last_request_ts["t"] = time.time()


def get_json(session: requests.Session, url: str, params: dict, timeout: int = 60) -> dict:
    polite_wait()
    resp = session.get(url, params=params, timeout=timeout)
    resp.raise_for_status()
    return resp.json()
