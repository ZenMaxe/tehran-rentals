"""End-to-end pipeline. Resumable: search pages and post details are checkpointed under cache/.

Usage: python src/main.py [--only DISTRICT_ID ...] [--reverify-currency] [--skip-search]
"""
import argparse
import json
import logging
from datetime import datetime, timezone

import pandas as pd

import currency_verification
import neighborhoods
import stations
from config import CACHE, DETOUR_FACTOR, MAX_CREDIT_TOMAN, MAX_RENT_TOMAN, MIN_CREDIT_TOMAN, OUTPUTS, WALK_SPEED_MPS
from deduplication import find_reposts
from distance_calculator import classify_distance, straight_line
from divar_client import fetch_post, form_data, search_all
from filters import classify, metro_mentions, register_station_aliases, roommate_or_seeker
from listing_parser import parse_post_detail
from net import AccessBlocked

log = logging.getLogger("main")
CK = CACHE / "checkpoint"


def run_searches(nb: pd.DataFrame, only=None) -> tuple[list[dict], dict[str, dict]]:
    CK.mkdir(parents=True, exist_ok=True)
    dists = nb.groupby(["divar_district_id", "neighborhood_fa", "divar_slug"]).agg(
        stations=("station_en", lambda s: ", ".join(sorted(set(s)))),
        min_dist=("centroid_distance_m", "min"), prio=("search_priority", "min")).reset_index().sort_values(["prio", "min_dist"])
    log_rows, found = [], {}
    for d in dists.itertuples():
        did = int(d.divar_district_id)
        if only and did not in only:
            continue
        ck = CK / f"search_{did}.json"
        if ck.exists():
            s = json.loads(ck.read_text())
        else:
            s = search_all(form_data(MAX_CREDIT_TOMAN, MAX_RENT_TOMAN, [did], min_credit=MIN_CREDIT_TOMAN), f"d{did}")
            s["method"] = "districts filter"
            if s["error"] and "district is not valid" in s["error"]:
                # Legacy ("قدیمی") districts serve page 1 then reject pagination; redo the area by its bbox, keep page-1 rows
                bbox = next(x["bbox"] for x in neighborhoods.load_divar_districts() if x["id"] == did)
                first = s["rows"]
                s = search_all(form_data(MAX_CREDIT_TOMAN, MAX_RENT_TOMAN, bbox=bbox, min_credit=MIN_CREDIT_TOMAN), f"d{did}_bbox")
                seen = {r["token"] for r in s["rows"]}
                s["rows"] += [r for r in first if r["token"] not in seen]
                s["method"] = f"bbox fallback {bbox} (legacy district id rejected on page 2; {len(first)} page-1 rows merged)"
            if s["complete"]:  # only checkpoint complete runs so failures get retried on rerun
                ck.write_text(json.dumps(s, ensure_ascii=False))
        log.info("district %s %s: %d rows, %d pages, %s", did, d.neighborhood_fa, len(s["rows"]), s["pages"], s["stop_reason"])
        for r in s["rows"]:
            f = found.setdefault(r["token"], dict(r, found_in_districts=[]))
            f["found_in_districts"].append(d.neighborhood_fa)
        log_rows.append({"divar_district_id": did, "neighborhood_fa": d.neighborhood_fa, "divar_slug": d.divar_slug,
                         "associated_stations": d.stations, "search_priority": d.prio,
                         "filters": f"{MIN_CREDIT_TOMAN}<=credit<={MAX_CREDIT_TOMAN}; rent<={MAX_RENT_TOMAN}", "method": s.get("method"),
                         "request_status": "ok" if not s["error"] else "error", "pages_fetched": s["pages"],
                         "pagination_complete": s["complete"], "stop_reason": s["stop_reason"],
                         "similar_results_skipped": s["similar_skipped"], "candidates": len(s["rows"]),
                         "error": s["error"], "started_utc": s["started"], "finished_utc": s["finished"]})
    return log_rows, found


class _Skip(Exception):
    pass


def enrich(tok: str, card: dict, st_centres, supp_districts) -> dict:
    rec = {"token": tok, "url": f"https://divar.ir/v/{tok}", "fetch_status": "OK", "fetch_error": None}
    skip = roommate_or_seeker(card.get("title"), None)
    try:
        if skip:  # obvious from the card title alone; saves a rate-limited detail request
            raise _Skip(skip)
        post, meta = fetch_post(tok)
        if post is None:
            rec["fetch_status"] = "UNAVAILABLE"
        else:
            rec.update(parse_post_detail(post))
            rec["token"] = rec["token"] or tok
            rec["url"] = rec["url"] or f"https://divar.ir/v/{tok}"
    except _Skip as e:
        rec.update(fetch_status="SKIPPED_CARD_TITLE", fetch_error=str(e))
    except AccessBlocked as e:
        rec.update(fetch_status="ACCESS_BLOCKED", fetch_error=str(e))
    except Exception as e:
        rec.update(fetch_status="ERROR", fetch_error=f"{type(e).__name__}: {e}")
    rec.update({f"card_{k}": card.get(f"card_{k}") for k in ("credit", "rent", "credit_text", "rent_text")})
    rec["found_in_districts"] = "; ".join(card["found_in_districts"])
    rec["search_district_fa"] = card.get("district_fa")
    rec["supplementary_area"] = any(x in supp_districts for x in card["found_in_districts"])
    rec["title"] = rec.get("title") or card.get("title")
    if rec.get("card_credit") is not None and rec.get("credit") is not None and rec["card_credit"] != rec["credit"]:
        rec["price_conflict"] = ((rec.get("price_conflict") or "") + f"; card credit {rec['card_credit']} != detail {rec['credit']}").strip("; ")
    if rec.get("latitude") is not None:
        sl = straight_line(rec["latitude"], rec["longitude"], st_centres)
        k = min(sl, key=sl.get)
        rec.update(nearest_sl_station=k, nearest_sl_m=round(sl[k]), sl_class_provisional=classify_distance(sl[k]))
        rec["sl_all_json"] = json.dumps({a: round(b) for a, b in sorted(sl.items(), key=lambda x: x[1])})
        est = sl[k] * DETOUR_FACTOR  # real routes come later from routing_check.py
        rec.update(est_walk_m=round(est), est_walk_minutes=round(est / WALK_SPEED_MPS / 60, 1),
                   est_walk_class=classify_distance(est), routing_note="not routed (estimate only)")
    rec["metro_mentions"] = metro_mentions(rec.get("title"), rec.get("description"))
    return rec


def reclassify(recs):
    for r in recs:
        if r.get("duplicate_of"):
            r["status"], r["reason"] = "DUPLICATE", f"near-identical to {r['duplicate_of']}: {r.get('repost_evidence')}"
        else:
            r["status"], r["reason"] = classify(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int, nargs="*")
    ap.add_argument("--reverify-currency", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                        handlers=[logging.StreamHandler(), logging.FileHandler(CACHE / "run.log", encoding="utf-8")])
    started = datetime.now(timezone.utc)
    OUTPUTS.mkdir(exist_ok=True)
    st = stations.build()
    register_station_aliases(st)
    nb = neighborhoods.build(st)
    if a.reverify_currency or not (OUTPUTS / "currency_filter_verification.md").exists():
        currency_verification.run()
    log_rows, found = run_searches(nb, set(a.only) if a.only else None)
    log.info("unique candidate tokens: %d", len(found))
    metro = st[st.kind == "metro_station"]
    centres = {r.station_key: (r.lat, r.lon) for r in metro.itertuples()}
    supp = set(nb[nb.station_kind == "supplementary_area"].neighborhood_fa) - set(nb[nb.station_kind == "metro_station"].neighborhood_fa)
    recs = []
    for i, (tok, card) in enumerate(found.items(), 1):
        recs.append(enrich(tok, card, centres, supp))
        if i % 50 == 0:
            log.info("details %d/%d", i, len(found))
    find_reposts(recs)
    reclassify(recs)
    # per-district match counts back into the search log
    for row in log_rows:
        row["matches"] = sum(1 for r in recs if r["status"] in ("MATCH_VERIFIED", "MATCH_PROVISIONAL_DISTANCE")
                             and row["neighborhood_fa"] in r["found_in_districts"].split("; "))
    meta = {"started_utc": started.isoformat(), "finished_utc": datetime.now(timezone.utc).isoformat(),
            "budget": {"max_credit_toman": MAX_CREDIT_TOMAN, "max_rent_toman": MAX_RENT_TOMAN}, "only": a.only}
    (CACHE / "results.json").write_text(json.dumps({"meta": meta, "search_log": log_rows, "records": recs}, ensure_ascii=False, default=str))
    import exporter
    exporter.export(st, nb, log_rows, recs, meta)


if __name__ == "__main__":
    main()
