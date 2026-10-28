"""Repost detection. Token is the primary key; content matches are flagged, only near-identical ones marked DUPLICATE."""
from difflib import SequenceMatcher

from geolocation import haversine_m


def _sim(a, b) -> float:
    return SequenceMatcher(None, a or "", b or "").ratio()


def repost_score(a: dict, b: dict) -> tuple[bool, bool, str]:
    """Return (likely_repost, strong_duplicate, evidence)."""
    same_price = a.get("credit") == b.get("credit") and a.get("rent") == b.get("rent")
    same_shape = a.get("area_m2") and a.get("area_m2") == b.get("area_m2") and a.get("rooms") == b.get("rooms")
    if not (same_price and same_shape):
        return False, False, ""
    near = None
    if a.get("latitude") is not None and b.get("latitude") is not None:
        near = haversine_m(a["latitude"], a["longitude"], b["latitude"], b["longitude"])
    tsim, dsim = _sim(a.get("title"), b.get("title")), _sim(a.get("description"), b.get("description"))
    photos = bool(set(a.get("photos") or []) & set(b.get("photos") or []))
    ev = f"same price/area/rooms; dist={near:.0f}m" if near is not None else "same price/area/rooms; no coords"
    ev += f"; title_sim={tsim:.2f}; desc_sim={dsim:.2f}; shared_photo_url={photos}"
    close = near is not None and near <= 150
    likely = close and (tsim >= 0.6 or dsim >= 0.6 or photos)
    strong = (near is not None and near <= 30 and dsim >= 0.9) or photos
    return likely, likely and strong, ev


def find_reposts(recs: list[dict]) -> None:
    """Annotate in place: possible_repost_of / duplicate_of (keeps the most recently bumped/first-seen one)."""
    for i, a in enumerate(recs):
        for b in recs[:i]:
            likely, strong, ev = repost_score(a, b)
            if likely:
                a.setdefault("possible_repost_of", b["token"])
                a["repost_evidence"] = ev
                if strong and not b.get("duplicate_of"):
                    a["duplicate_of"] = b["token"]
                    break
