"""HTTP with retries, rate limiting, structured logging and on-disk JSON caching."""
import hashlib
import json
import logging
import time

import requests

from config import CACHE, UA

log = logging.getLogger("net")
_session = requests.Session()
_session.headers.update({"User-Agent": UA, "Accept": "application/json"})
_last_call: dict[str, float] = {}


class AccessBlocked(Exception):
    """Non-retryable denial (403/401/429 after retries, captcha page, RBAC)."""


def _throttle(host: str, delay: float):
    wait = _last_call.get(host, 0) + delay - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last_call[host] = time.monotonic()


def request_json(method: str, url: str, *, body=None, params=None, delay=1.0,
                 retries=4, timeout=40, cache_key: str | None = None, cache_dir="http"):
    """Return (json, meta). meta has status, attempts, from_cache. Caches successes when cache_key given."""
    path = None
    if cache_key:
        h = hashlib.sha1(cache_key.encode()).hexdigest()[:16]
        path = CACHE / cache_dir / f"{h}.json"
        if path.exists():
            return json.loads(path.read_text()), {"status": 200, "attempts": 0, "from_cache": True}
    host = url.split("/")[2]
    last = None
    for attempt in range(1, retries + 1):
        _throttle(host, delay)
        try:
            r = _session.request(method, url, json=body, params=params, timeout=timeout)
        except requests.RequestException as e:
            last = f"{type(e).__name__}: {e}"
            log.warning("net error %s %s attempt %d: %s", method, url, attempt, last)
            time.sleep(2 ** attempt)
            continue
        if r.status_code == 200:
            try:
                data = r.json()
            except ValueError:
                raise AccessBlocked(f"non-JSON 200 from {url}: {r.text[:200]!r}")
            if path:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(data, ensure_ascii=False))
            return data, {"status": 200, "attempts": attempt, "from_cache": False}
        last = f"HTTP {r.status_code}: {r.text[:200]!r}"
        if r.status_code in (400, 404, 410):
            return None, {"status": r.status_code, "attempts": attempt, "from_cache": False, "error": last}
        if r.status_code in (401, 403):
            raise AccessBlocked(last)
        log.warning("%s %s attempt %d: %s", method, url, attempt, last)
        time.sleep(min(60, 3 * 2 ** attempt))  # 429/5xx backoff
    if last and ("429" in last):
        raise AccessBlocked(last)
    raise RuntimeError(f"{method} {url} failed after {retries} attempts: {last}")
