"""Coordinate handling: extraction from Divar MAP_ROW, validation, order conversions, Haversine."""
import math

# Generous Tehran-province envelope used for sanity / swap detection
TEHRAN_LAT = (35.4, 36.0)
TEHRAN_LON = (51.0, 51.8)


def haversine_m(lat1, lon1, lat2, lon2) -> float:
    r = 6_371_008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


# Explicit order conversions. Internal canonical form: (lat, lon).
def to_google(lat, lon) -> str:
    return f"{lat},{lon}"


def to_geojson(lat, lon) -> list[float]:
    return [lon, lat]


def from_geojson(coords) -> tuple[float, float]:
    lon, lat = coords[:2]
    return lat, lon


def bbox_to_latlon(bbox) -> tuple[float, float, float, float]:
    """[minLon, minLat, maxLon, maxLat] (Divar/GeoJSON bbox) -> (min_lat, min_lon, max_lat, max_lon)."""
    min_lon, min_lat, max_lon, max_lat = bbox
    return min_lat, min_lon, max_lat, max_lon


def validate_point(lat, lon) -> tuple[str, str | None]:
    """Return (status, note). status in VALID, SWAPPED_SUSPECT, OUT_OF_AREA, INVALID."""
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        return "INVALID", "non-numeric"
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        if -90 <= lon <= 90 and -180 <= lat <= 180:
            return "SWAPPED_SUSPECT", "lat out of range but valid when swapped"
        return "INVALID", "out of global range"
    if lat == 0 and lon == 0:
        return "INVALID", "null island"
    in_t = TEHRAN_LAT[0] <= lat <= TEHRAN_LAT[1] and TEHRAN_LON[0] <= lon <= TEHRAN_LON[1]
    if in_t:
        return "VALID", None
    if TEHRAN_LAT[0] <= lon <= TEHRAN_LAT[1] and TEHRAN_LON[0] <= lat <= TEHRAN_LON[1]:
        return "SWAPPED_SUSPECT", "values fit Tehran only when swapped"
    return "OUT_OF_AREA", "outside Tehran envelope"


def extract_map_location(post: dict) -> dict:
    """Pull the listing point out of sections[*].widgets[MAP_ROW].data.location.

    Never swaps or infers: a suspected swap is flagged, not corrected.
    """
    out = {"latitude": None, "longitude": None, "location_type": None,
           "location_source_path": None, "coord_status": "MISSING", "coord_confidence": "none",
           "coord_note": None, "coord_radius_m": None}
    for si, sec in enumerate(post.get("sections") or []):
        for wi, w in enumerate(sec.get("widgets") or []):
            if w.get("widget_type") != "MAP_ROW":
                continue
            loc = (w.get("data") or {}).get("location") or {}
            out["location_type"] = loc.get("type") or ("EXACT_DATA_UNTYPED" if "exact_data" in loc else None)
            base = f"sections[{si}].widgets[{wi}].data.location"
            pt = ((loc.get("exact_data") or {}).get("point")) or {}
            if "latitude" in pt and "longitude" in pt:
                lat, lon = pt["latitude"], pt["longitude"]
                status, note = validate_point(lat, lon)
                out.update(location_source_path=base + ".exact_data.point", coord_status=status, coord_note=note)
                if status == "VALID":
                    out.update(latitude=float(lat), longitude=float(lon), coord_confidence="api_exact_pin")
                return out
            # Other structures (e.g. fuzzy/approximate) - record shape, do not invent a point
            fz = loc.get("fuzzy_data") or loc.get("approximate_data")
            if fz:
                pt = fz.get("point") or {}
                if "latitude" in pt and "longitude" in pt:
                    status, note = validate_point(pt["latitude"], pt["longitude"])
                    out.update(location_source_path=base + (".fuzzy_data.point" if "fuzzy_data" in loc else ".approximate_data.point"),
                               coord_status="APPROXIMATE" if status == "VALID" else status, coord_note=note)
                    out["coord_radius_m"] = fz.get("radius")
                    if status == "VALID":
                        out.update(latitude=float(pt["latitude"]), longitude=float(pt["longitude"]),
                                   coord_confidence="api_approximate", location_type=out["location_type"] or "APPROXIMATE")
                    return out
            out.update(location_source_path=base, coord_status="NO_POINT", coord_note=f"location keys: {sorted(loc)}")
            return out
    return out
