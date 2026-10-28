"""Phase B: station -> nearby neighbourhoods, from Divar's own district list + OSM admin_level 10/11 boundaries."""
import json
import re

import pandas as pd

from config import CACHE, DISTRICT_SEARCH_RADIUS_M, DIVAR_DISTRICTS, OUTPUTS
from geolocation import haversine_m
from net import request_json

SUPPLEMENTARY_RADIUS_M = 1200


def load_divar_districts() -> list[dict]:
    path = CACHE / "divar_districts.json"
    if not path.exists():
        data, _ = request_json("GET", DIVAR_DISTRICTS)
        path.write_text(json.dumps(data, ensure_ascii=False))
    return json.loads(path.read_text())["districts"]


def norm_name(s: str) -> str:
    s = (s or "").replace("ي", "ی").replace("ك", "ک").replace("‌", " ")
    return re.sub(r"\s+", " ", re.sub(r"[()\-_.،]", " ", s)).strip()


def dist_to_bbox_m(lat, lon, bbox) -> float:
    """0 when inside. bbox is Divar order [minLon, minLat, maxLon, maxLat]."""
    min_lon, min_lat, max_lon, max_lat = bbox
    clat, clon = min(max(lat, min_lat), max_lat), min(max(lon, min_lon), max_lon)
    return haversine_m(lat, lon, clat, clon)


def build(stations: pd.DataFrame) -> pd.DataFrame:
    districts = load_divar_districts()
    osm = json.loads((CACHE / "osm" / "overpass_neighbourhoods.json").read_text())["elements"]
    osm_n = [(e["tags"].get("name"), e["tags"].get("name:en"), e["center"]["lat"], e["center"]["lon"]) for e in osm if "center" in e]
    rows = []
    for st in stations.itertuples():
        radius = DISTRICT_SEARCH_RADIUS_M if st.kind == "metro_station" else SUPPLEMENTARY_RADIUS_M
        for d in districts:
            c = d["centroid"]
            cdist = haversine_m(st.lat, st.lon, c["latitude"], c["longitude"])
            bdist = dist_to_bbox_m(st.lat, st.lon, d["bbox"]) if d.get("bbox") else cdist
            if min(cdist, bdist) > radius:
                continue
            nn = norm_name(d["name"])
            aliases = {d["slug"], d.get("second_slug") or ""}
            inside = []
            for name, en, la, lo in osm_n:
                if d.get("bbox") and dist_to_bbox_m(la, lo, d["bbox"]) == 0:
                    inside.append(name)
                    if norm_name(name) != nn and (nn in norm_name(name) or norm_name(name) in nn):
                        aliases.add(name)
                    if en and norm_name(name) == nn:
                        aliases.add(en)
            streets = [t["title"] for t in d.get("tags", []) if t["type"].upper() in ("STREET", "SQUARE", "BOULEVARD", "HIGHWAY", "CROSSROAD", "SUBWAY", "METRO")]
            near = min(cdist, bdist) if bdist == 0 else cdist
            prio = 1 if bdist == 0 or cdist <= 800 else 2 if cdist <= 1300 else 3
            conf = "high" if cdist <= 1200 or bdist == 0 else "medium"
            rows.append({
                "station_key": st.station_key, "station_fa": st.station_fa, "station_en": st.station_en,
                "station_kind": st.kind,
                "neighborhood_fa": d["name"], "divar_slug": d["slug"], "divar_district_id": d["id"],
                "alternative_names": "; ".join(sorted(a for a in aliases if a)),
                "osm_neighbourhoods_inside_bbox": "; ".join(sorted(set(n for n in inside if n))),
                "relevant_streets": "; ".join(streets[:15]),
                "centroid_distance_m": round(cdist), "bbox_distance_m": round(bdist),
                "station_inside_district_bbox": bdist == 0,
                "source": "Divar places API (centroid+bbox+street tags); OSM admin_level 10/11 boundaries",
                "source_url": DIVAR_DISTRICTS,
                "confidence": conf, "search_priority": prio,
            })
    df = pd.DataFrame(rows).sort_values(["station_key", "search_priority", "centroid_distance_m"])
    df.to_csv(OUTPUTS / "station_neighborhoods.csv", index=False, encoding="utf-8-sig")
    return df


if __name__ == "__main__":
    st = pd.read_csv(OUTPUTS / "metro_stations.csv")
    df = build(st)
    print(len(df), "rows;", df.divar_district_id.nunique(), "unique districts")
    print(df.groupby("station_en").neighborhood_fa.apply(lambda s: ", ".join(s)).to_string())
