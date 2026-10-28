"""Replace estimated walks with real OSRM foot routes, then reclassify and regenerate every output.

Run after main.py:  python src/routing_check.py [--all] [--batch 40]
Default routes only listings that can still matter: prices within budget, real apartment
(not room-share), pin within 2.5 km straight line of a target station.
"""
import argparse
import json
import logging

import pandas as pd

import exporter
import stations
from config import CACHE, MAX_CREDIT_TOMAN, MAX_RENT_TOMAN, OUTPUTS
from distance_calculator import ROUTE_CANDIDATE_RADIUS_M, classify_distance, walking_batch
from main import reclassify

log = logging.getLogger("routing_check")


def needs_route(r: dict) -> bool:
    return (r.get("latitude") is not None and r.get("credit") is not None and r.get("rent") is not None
            and r["credit"] <= MAX_CREDIT_TOMAN and r["rent"] <= MAX_RENT_TOMAN
            and r.get("status") != "WRONG_CATEGORY" and (r.get("nearest_sl_m") or 1e9) <= ROUTE_CANDIDATE_RADIUS_M)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="route every listing with coordinates")
    ap.add_argument("--batch", type=int, default=40)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    d = json.loads((CACHE / "results.json").read_text())
    recs = d["records"]
    st = pd.read_csv(OUTPUTS / "metro_stations.csv")
    nb = pd.read_csv(OUTPUTS / "station_neighborhoods.csv")
    metro = st[st.kind == "metro_station"]
    centres = {r.station_key: (r.lat, r.lon) for r in metro.itertuples()}
    ents = stations.routing_points(st)
    from filters import register_station_aliases
    register_station_aliases(st)
    # group spatially so each OSRM table only carries nearby stations' entrances
    todo = sorted((r for r in recs if (a.all and r.get("latitude") is not None) or needs_route(r)),
                  key=lambda r: (r.get("nearest_sl_station") or "", r["latitude"]))
    log.info("routing %d of %d listings in batches of %d", len(todo), len(recs), a.batch)
    for i in range(0, len(todo), a.batch):
        chunk = todo[i:i + a.batch]
        for r, (w, note) in zip(chunk, walking_batch([(r["latitude"], r["longitude"]) for r in chunk], ents, centres)):
            r["routing_note"] = note
            if w:
                wk = min(w, key=lambda x: w[x][0])
                r.update(nearest_walk_station=wk, nearest_walk_m=round(w[wk][0]), walk_minutes=round(w[wk][1] / 60, 1),
                         walk_class=classify_distance(w[wk][0]),
                         walk_all_json=json.dumps({k: round(v[0]) for k, v in sorted(w.items(), key=lambda x: x[1][0])}))
                # straight-line x factor vs real route, kept for auditing the estimate
                if r.get("est_walk_m"):
                    r["route_vs_estimate"] = round(w[wk][0] / r["est_walk_m"], 2)
        log.info("routed %d/%d", min(i + a.batch, len(todo)), len(todo))
    before = {r["token"]: r["status"] for r in recs}
    reclassify(recs)
    changed = sum(before[r["token"]] != r["status"] for r in recs)
    d["meta"]["routing_check"] = {"routed": len(todo), "status_changes": changed}
    (CACHE / "results.json").write_text(json.dumps(d, ensure_ascii=False, default=str))
    exporter.export(st, nb, d["search_log"], recs, d["meta"])
    print(f"routed {len(todo)} listings; {changed} statuses changed")
    print(pd.Series([r["status"] for r in recs]).value_counts().to_string())


if __name__ == "__main__":
    main()
