"""Phase G: straight-line distances (main run) and batched pedestrian routing (routing_check.py)."""
import logging

from config import ACCEPTABLE_M, EXCELLENT_M, FOOT_ROUTER, SECONDARY_M, WALK_SPEED_MPS
from geolocation import haversine_m
from net import request_json

log = logging.getLogger("distance")
ROUTE_CANDIDATE_RADIUS_M = 2500  # only route to stations plausibly walkable


def classify_distance(m: float | None) -> str | None:
    if m is None:
        return None
    if m <= EXCELLENT_M:
        return "Excellent"
    if m <= ACCEPTABLE_M:
        return "Acceptable"
    if m <= SECONDARY_M:
        return "Secondary"
    return "Excluded (>1500 m)"


def straight_line(lat, lon, stations: dict[str, tuple[float, float]]) -> dict[str, float]:
    return {k: haversine_m(lat, lon, *p) for k, p in stations.items()}


def walking_batch(points: list[tuple[float, float]], entrances: dict[str, list[tuple[float, float]]],
                  centres: dict[str, tuple[float, float]]) -> list[tuple[dict, str | None]]:
    """One OSRM foot 'table' call for many listings. Returns per point ({station: (metres, seconds)}, note).

    Destinations = entrances of every station within ROUTE_CANDIDATE_RADIUS_M of any point in the batch.
    """
    keys = {k for lat, lon in points for k, c in centres.items() if haversine_m(lat, lon, *c) <= ROUTE_CANDIDATE_RADIUS_M}
    dest = [(k, p) for k in sorted(keys) for p in entrances[k]]
    if len(points) > 1 and len(points) + len(dest) > 100:  # stay under OSRM table size limits: split
        h = len(points) // 2
        return walking_batch(points[:h], entrances, centres) + walking_batch(points[h:], entrances, centres)
    if not dest:
        return [({}, "no station within routing radius")] * len(points)
    coords = ";".join([f"{lon},{lat}" for lat, lon in points] + [f"{p[1]},{p[0]}" for _, p in dest])  # OSRM: lon,lat
    n = len(points)
    url = f"{FOOT_ROUTER}/table/v1/driving/{coords}"  # 'driving' is the URL slot; routed-foot serves the foot profile
    try:
        j, _ = request_json("GET", url, params={"sources": ";".join(map(str, range(n))),
                                                "destinations": ";".join(map(str, range(n, n + len(dest)))),
                                                "annotations": "distance,duration"},
                            delay=1.0, cache_key="footbatch:" + coords, cache_dir="routing_batch")
    except Exception as e:
        return [({}, f"routing failed: {e}")] * n
    if not j or j.get("code") != "Ok":
        return [({}, f"routing code {j and j.get('code')}")] * n
    dsnap = [x.get("distance") or 0 for x in j["destinations"]]
    out = []
    for i in range(n):
        snap = j["sources"][i].get("distance") or 0
        best: dict[str, tuple[float, float]] = {}
        for (k, _), d, ds in zip(dest, j["distances"][i], dsnap):
            if d is None:
                continue
            # OSRM omits the off-network legs; add them so the figure is conservative
            d = d + snap + ds
            if k not in best or d < best[k][0]:
                best[k] = (d, d / WALK_SPEED_MPS)
        out.append((best, f"origin snapped {snap:.0f} m to path network" if snap > 50 else None))
    return out
