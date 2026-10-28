"""Divar search + post-detail client. Schema confirmed from a live browser session (see currency_filter_verification.md)."""
import json
import logging
from datetime import datetime, timezone

from config import CACHE, DETAIL_DELAY_S, DIVAR_POST, DIVAR_SEARCH, REQUEST_DELAY_S
from listing_parser import parse_post_row
from net import AccessBlocked, request_json

log = logging.getLogger("divar")
SIMILAR_MARKER = "آگهی‌های مشابه"
MAX_PAGES = 40  # safety stop; logged as incomplete if hit


def form_data(max_credit=None, max_rent=None, district_ids=None, bbox=None, category="apartment-rent", min_credit=None) -> dict:
    data = {"category": {"str": {"value": category}}}
    if max_credit is not None or min_credit is not None:
        data["credit"] = {"number_range": {k: str(v) for k, v in (("minimum", min_credit), ("maximum", max_credit)) if v is not None}}
    if max_rent is not None:
        data["rent"] = {"number_range": {"maximum": str(max_rent)}}
    if district_ids:
        data["districts"] = {"repeated_string": {"value": [str(d) for d in district_ids]}}
    if bbox:  # [minLon, minLat, maxLon, maxLat]
        data["bbox"] = {"repeated_float": {"value": [{"value": v} for v in bbox]}}
    return data


def search_all(data: dict, label: str, snapshot=True) -> dict:
    """Paginate one filtered search until exhausted or the 'similar listings' boundary.

    Returns {rows, pages, complete, stop_reason, similar_skipped, echoed_filters, error}.
    """
    rows, pag, pages, similar = [], None, 0, 0
    res = {"label": label, "started": datetime.now(timezone.utc).isoformat(), "error": None}
    echoed = None
    stop = "no_more_pages"
    try:
        while True:
            body = {"city_ids": ["1"], "search_data": {"form_data": {"data": data}}, "disable_recommendation": True}
            if pag:
                body["pagination_data"] = pag
            j, meta = request_json("POST", DIVAR_SEARCH, body=body, delay=REQUEST_DELAY_S)
            if j is None:
                raise RuntimeError(f"status {meta['status']}: {meta.get('error')}")
            pages += 1
            if snapshot:
                p = CACHE / "search_snapshots" / f"{label}_p{pages}.json"
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(json.dumps(j, ensure_ascii=False))
            if echoed is None:
                echoed = (j.get("search_data") or {}).get("form_data", {}).get("data")
            in_similar = False
            for w in j.get("list_widgets") or []:
                wt = w.get("widget_type")
                if wt == "SELECTOR_ROW" and SIMILAR_MARKER in ((w.get("data") or {}).get("title") or ""):
                    in_similar = True
                    continue
                if wt == "POST_ROW":
                    if in_similar:
                        similar += 1
                    else:
                        rows.append(parse_post_row(w))
            if in_similar:
                stop = "similar_results_boundary"
                break
            pg = j.get("pagination") or {}
            if not pg.get("has_next_page"):
                break
            if pages >= MAX_PAGES:
                stop = "max_pages_safety_stop"
                break
            pag = pg.get("data")
    except AccessBlocked as e:
        stop, res["error"] = "access_blocked", str(e)
    except Exception as e:  # logged into search_log, never silently treated as "no listings"
        stop, res["error"] = "error", f"{type(e).__name__}: {e}"
    res.update(rows=rows, pages=pages, stop_reason=stop, similar_skipped=similar, echoed_filters=echoed,
               complete=stop in ("no_more_pages", "similar_results_boundary"),
               finished=datetime.now(timezone.utc).isoformat())
    return res


def fetch_post(token: str) -> tuple[dict | None, dict]:
    """Detail JSON, cached per token. meta.status 404/410 => unavailable."""
    return request_json("GET", DIVAR_POST.format(token=token), delay=DETAIL_DELAY_S,
                        cache_key=f"post:{token}", cache_dir="posts")
