"""Phase A: verified station coordinates (OSM primary, Wikidata cross-check), entrances, lines."""
import json
import logging
import re
from datetime import date

import pandas as pd

from config import CACHE, FAR_SOUTH_LAT, OUTPUTS, OVERPASS, STATION_SCOPE, STATIONS, SUPPLEMENTARY
from geolocation import haversine_m
from net import request_json

log = logging.getLogger("stations")
BBOX = "35.60,51.25,35.80,51.55"
ENTRANCE_RADIUS_M = 350


def _overpass(name: str, query: str) -> dict:
    path = CACHE / "osm" / f"{name}.json"
    if path.exists():
        return json.loads(path.read_text())
    import requests  # Overpass wants form-encoded `data=`
    from config import UA
    r = requests.post(OVERPASS, data={"data": query}, headers={"User-Agent": UA, "Accept": "application/json"}, timeout=180)
    r.raise_for_status()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(r.text)
    return r.json()


def load_osm():
    raw = _overpass("overpass_raw", f'[out:json][timeout:90];(node["railway"="station"]({BBOX});'
                                    f'node["railway"="subway_entrance"]({BBOX}););out body;')
    extra = _overpass("overpass_beryanak_majidiyeh", f'[out:json][timeout:90];(nwr["name"~"بریانک|مجیدیه|Beryanak|Majid"]({BBOX});'
                                                     f'nwr["name:en"~"Beryanak|Majidiyeh",i]({BBOX}););out center tags;')
    routes = _overpass("overpass_routes", f'[out:json][timeout:120];rel["route"="subway"]({BBOX});out body;node(r);out body;')
    wide = "35.50,51.00,35.90,51.70"  # whole city, for STATION_SCOPE='all_tehran'
    raw2 = _overpass("overpass_stations_v2", f'[out:json][timeout:120];(nwr["railway"="station"]["station"="subway"]({wide});'
                                             f'nwr["railway"="station"]["subway"="yes"]({wide});node["railway"="subway_entrance"]({wide}););out center tags;')
    routes2 = _overpass("overpass_routes_v2", f'[out:json][timeout:180];rel["route"="subway"]({wide});out body;node(r);out body;')
    return raw, extra, routes, raw2, routes2


_PREFIX = re.compile(r"^(?:ایستگاه\s+)?(?:مترو(?:ی)?\s+)?(?:ایستگاه\s+)?")


def clean_name(n: str) -> str:
    n = _PREFIX.sub("", (n or "").strip())
    return re.sub(r"\s*\(عج\)|\s*\((?:تهران)\)", "", n).strip()


def discover_tehran(els_list) -> list[tuple]:
    """Every subway station inside a Divar Tehran district bbox, merged by name within 400 m."""
    from neighborhoods import dist_to_bbox_m, load_divar_districts
    boxes = [d["bbox"] for d in load_divar_districts() if d.get("bbox")]
    pinned = {oid: (k, fa, en) for k, fa, en, oid in STATIONS}
    seen: list[tuple] = []  # (clean name, lat, lon)
    out = []
    # pinned stations first so they keep their curated keys/names
    ordered = sorted(els_list, key=lambda e: f'{e["type"]}/{e["id"]}' not in pinned)
    for e in ordered:
        if e["tags"].get("railway") != "station":
            continue
        lat, lon = _latlon(e)
        if not any(dist_to_bbox_m(lat, lon, b) == 0 for b in boxes):
            continue  # outside Tehran city (Karaj, Parand, Kahrizak ...)
        oid = f'{e["type"]}/{e["id"]}'
        name = clean_name(e["tags"].get("name"))
        if any(n == name and haversine_m(lat, lon, la, lo) < 400 for n, la, lo in seen):
            continue
        seen.append((name, lat, lon))
        k, fa, en = pinned.get(oid, (f"osm_{e['type'][0]}{e['id']}", name, e["tags"].get("name:en") or name))
        out.append((k, fa, en, oid))
    return out


def _latlon(el):
    c = el.get("center", el)
    return c["lat"], c["lon"]


def wikidata_coords(qids: list[str]) -> dict:
    data, _ = request_json("GET", "https://www.wikidata.org/w/api.php",
                           params={"action": "wbgetentities", "ids": "|".join(qids), "props": "claims", "format": "json"},
                           cache_key="wikidata:" + ",".join(sorted(qids)), cache_dir="wikidata")
    out = {}
    for q, ent in (data.get("entities") or {}).items():
        try:
            v = ent["claims"]["P625"][0]["mainsnak"]["datavalue"]["value"]
            out[q] = (v["latitude"], v["longitude"])
        except (KeyError, IndexError):
            out[q] = None
    return out


def build() -> pd.DataFrame:
    raw, extra, routes, raw2, routes2 = load_osm()
    if STATION_SCOPE == "all_tehran":
        raw, routes = raw2, routes2
    els = {f'{e["type"]}/{e["id"]}': e for e in raw["elements"] + extra["elements"]}
    all_stations = [e for e in raw["elements"] if e["tags"].get("railway") == "station"]
    entrances = [e for e in raw["elements"] if e["tags"].get("railway") == "subway_entrance"]
    station_list = discover_tehran(raw["elements"]) if STATION_SCOPE == "all_tehran" else STATIONS
    # line lookup: stop_position nodes that are members of subway route relations
    rnodes = {e["id"]: e for e in routes["elements"] if e["type"] == "node"}
    stops = []  # (lat, lon, ref)
    for rel in (e for e in routes["elements"] if e["type"] == "relation"):
        for m in rel["members"]:
            n = rnodes.get(m["ref"]) if m["type"] == "node" else None
            if n and m.get("role", "").startswith("stop"):
                stops.append((n["lat"], n["lon"], rel["tags"].get("ref")))

    targets = [(k, fa, en, oid, "metro_station") for k, fa, en, oid in station_list] + \
              [(k, fa, en, oid, "supplementary_area") for k, fa, en, oid in SUPPLEMENTARY]
    qids = [els[oid]["tags"]["wikidata"] for *_, oid, _ in targets if els[oid]["tags"].get("wikidata")]
    wd = {}
    for i in range(0, len(qids), 50):  # wbgetentities limit
        wd.update(wikidata_coords(qids[i:i + 50]))
    rows = []
    for key, fa, en, oid, kind in targets:
        el = els[oid]
        lat, lon = _latlon(el)
        # entrances: nearest OSM station must be this one (avoid stealing a neighbour's exits)
        ents = []
        for e in entrances:
            d = haversine_m(lat, lon, e["lat"], e["lon"])
            if d > ENTRANCE_RADIUS_M:
                continue
            nearest = min(all_stations + ([el] if el not in all_stations else []),
                          key=lambda s: haversine_m(*_latlon(s), e["lat"], e["lon"]))
            if nearest is el:
                ents.append({"osm_id": e["id"], "lat": e["lat"], "lon": e["lon"], "name": e["tags"].get("name"), "dist_m": round(d)})
        lines = sorted({ref for slat, slon, ref in stops if ref and haversine_m(lat, lon, slat, slon) < 400}, key=lambda x: int(x) if x.isdigit() else 99)
        qid = el["tags"].get("wikidata")
        wpt = wd.get(qid) if qid else None
        disc = round(haversine_m(lat, lon, *wpt)) if wpt else None
        conf = "n/a (neighbourhood centre)" if kind != "metro_station" else (
            "high" if disc is not None and disc <= 250 else "medium" if disc is not None and disc <= 600 else "medium (single source)" if disc is None else "low - sources disagree")
        rows.append({
            "station_key": key, "station_fa": fa, "station_en": en, "kind": kind,
            "lines": ",".join(lines) if kind == "metro_station" else "",
            "lat": round(lat, 7), "lon": round(lon, 7),
            "osm_element": oid, "osm_name": el["tags"].get("name"),
            "source_url": f"https://www.openstreetmap.org/{oid}",
            "entrance_count": len(ents),
            "entrances_json": json.dumps(ents, ensure_ascii=False),
            "wikidata": qid, "wikidata_lat": wpt[0] if wpt else None, "wikidata_lon": wpt[1] if wpt else None,
            "osm_vs_wikidata_m": disc, "confidence": conf,
            "date_verified": date.today().isoformat(),
            "far_south": kind == "metro_station" and lat < FAR_SOUTH_LAT,
        })
    df = pd.DataFrame(rows)
    OUTPUTS.mkdir(exist_ok=True)
    df.to_csv(OUTPUTS / "metro_stations.csv", index=False, encoding="utf-8-sig")
    return df


def routing_points(df: pd.DataFrame) -> dict[str, list[tuple[float, float]]]:
    """Per metro station: entrance points, or the station centre if OSM maps no entrance."""
    out = {}
    for r in df[df.kind == "metro_station"].itertuples():
        ents = json.loads(r.entrances_json)
        out[r.station_key] = [(e["lat"], e["lon"]) for e in ents] or [(r.lat, r.lon)]
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(build().drop(columns=["entrances_json"]).to_string())
