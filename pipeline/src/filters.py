"""Phase H: strict eligibility + metro-mention text check for far/missing pins."""
import json
import re

from config import DETOUR_FACTOR, MAX_CREDIT_TOMAN, MAX_RENT_TOMAN, MIN_CREDIT_TOMAN, SECONDARY_M
from listing_parser import normalize_digits

# Aliases as they appear in ad text. Matched only right after "مترو"/"ایستگاه" to avoid
# street-name false positives (ولیعصر, بهشتی, طالقانی are also long streets).
STATION_ALIASES = {
    "mahdieh": ["مهدیه"], "moniriyeh": ["منیریه"], "teatr_shahr": ["تئاتر شهر", "تئاترشهر", "تاتر شهر"],
    "vali_asr": ["ولیعصر", "ولی عصر", "ولی‌عصر"], "jahad": ["جهاد"],
    "mirza_shirazi": ["میرزای شیرازی", "میرزا شیرازی", "میرزاشیرازی"], "shahid_beheshti": ["بهشتی"],
    "sohrevardi": ["سهروردی"], "saadi": ["سعدی"], "darvazeh_dowlat": ["دروازه دولت"],
    "taleghani": ["طالقانی"], "haft_tir": ["هفت تیر", "هفتم تیر", "۷ تیر", "7 تیر", "هفتتیر"],
    "mofatteh": ["مفتح"], "helal_ahmar": ["هلال احمر", "هلال‌احمر"], "beryanak": ["بریانک"],
}
def register_station_aliases(stations) -> None:
    """Add text aliases for every station not curated above (all_tehran scope)."""
    for r in stations.itertuples():
        if r.kind != "metro_station" or r.station_key in STATION_ALIASES:
            continue
        base = re.sub(r"\s*\((?:ره|ع|س|عج)\)", "", r.station_fa).strip()
        al = {base, re.sub(r"^(?:شهید|شهدای|میدان|دکتر|آیت الله)\s+", "", base)}
        STATION_ALIASES[r.station_key] = sorted(a for a in al if len(a) >= 3)


_METRO = re.compile(r"(?:مترو|ایستگاه)(?:ی)?\s*(?:ایستگاه\s*)?([^\n.،,؛!]{0,30})")
UNNAMED_MENTION_MAX_SL_M = 3000
_GENERIC = {"نزدیک", "دسترسی", "دقیقه", "پیاده", "فاصله", "و", "تا", "از", "با", "به", "هم", "خط", "در", "است", "هست",
            "عالی", "کنار", "جنب", "نزدیکی", "قدم", "متری", "متر", "دقیقه‌ای", "اتوبوس", "بی", "آر", "BRT", "تی", "خوب"}


def metro_mentions(title: str | None, description: str | None) -> dict:
    """Find 'مترو …' phrases. Returns {any, target_stations, snippets}."""
    text = normalize_digits(f"{title or ''}\n{description or ''}").replace("ي", "ی").replace("ك", "ک")
    snippets, targets, named_other = [], set(), False
    for m in _METRO.finditer(text):
        tail = m.group(1)
        snippets.append(m.group(0).strip())
        hit = False
        for k, al in STATION_ALIASES.items():
            if any(a in tail.replace("‌", " ") or a in tail for a in al):
                targets.add(k)
                hit = True
        first = (tail.split() or [""])[0]
        if not hit and first and not first[0].isdigit() and first not in _GENERIC:
            named_other = True  # e.g. "مترو مدنی" - a named, non-target station
    return {"any": bool(snippets), "target_stations": sorted(targets), "snippets": snippets[:5],
            "named_non_target": named_other and not targets}


_ROOMMATE = re.compile(r"هم\s?‌?خونه|هم\s?‌?خانه|اتاق\s+اشتراکی|متقاضی\s+(?:اتاق|اجاره|رهن)|به\s+دنبال\s+(?:منزل|خانه|خونه|آپارتمان|واحد)|نیازمند\s+(?:منزل|خانه|خونه|آپارتمان|واحد)")


# Title-only: dorms, single rooms, parking spaces filed under apartment-rent
_NON_APARTMENT = re.compile(r"خوابگاه|پانسیون|هاستل|^\s*پارکینگ|اجاره\s+اتاق|اتاق\s+(?:در|مبله|دربست)|^\s*اتاق(?:\s|$)")


def roommate_or_seeker(title, description) -> str | None:
    """Room-share offers/requests, 'wanted' ads, dorms/rooms/parking that Divar files under apartment-rent."""
    t = normalize_digits(title or "")
    m = _ROOMMATE.search(t) or _NON_APARTMENT.search(t) or _ROOMMATE.search(normalize_digits((description or "")[:200]))
    return m.group(0).strip() if m else None


def classify(rec: dict) -> tuple[str, str]:
    """Return (status, reason). rec carries prices, coords, distances and mentions."""
    if rec.get("fetch_status") == "UNAVAILABLE":
        return "UNAVAILABLE", "detail endpoint 404/410 (ad removed or expired)"
    if rec.get("fetch_status") == "ACCESS_BLOCKED":
        return "ACCESS_BLOCKED", rec.get("fetch_error") or "blocked"
    if rec.get("fetch_status") == "SKIPPED_CARD_TITLE":
        return "WRONG_CATEGORY", f"room-share / seeker / dorm / room / parking ad (from search-card title, detail not fetched): {rec.get('fetch_error')}"
    if rec.get("fetch_status") == "ERROR":
        return "PARSING_ERROR", rec.get("fetch_error") or "fetch/parse error"
    if rec.get("category") and rec["category"] != "apartment-rent" or rec.get("city") and rec["city"] != "tehran":
        return "WRONG_CATEGORY", f"category={rec.get('category')} city={rec.get('city')}"
    rs = roommate_or_seeker(rec.get("title"), rec.get("description"))
    if rs:
        return "WRONG_CATEGORY", f"room-share / seeker / dorm / room / parking ad, not an apartment for rent ({rs})"
    c, r = rec.get("credit"), rec.get("rent")
    if c is None or r is None:
        raws = f"{rec.get('text_credit_raw') or ''} {rec.get('text_rent_raw') or ''}"
        if "توافقی" in raws:
            return "PARSING_ERROR", f"negotiable price (توافقی) - not a strict match: deposit={rec.get('text_credit_raw')} rent={rec.get('text_rent_raw')}"
        why = rec.get("price_conflict") or f"credit={c} rent={r} (missing)"
        return "PARSING_ERROR", f"price not verifiable: {why}"
    over = []
    if c > MAX_CREDIT_TOMAN:
        over.append(f"deposit {c:,} > {MAX_CREDIT_TOMAN:,}")
    if r > MAX_RENT_TOMAN:
        over.append(f"rent {r:,} > {MAX_RENT_TOMAN:,}")
    if over:
        return ("OVER_DEPOSIT_BUDGET" if c > MAX_CREDIT_TOMAN else "OVER_RENT_BUDGET"), "; ".join(over)
    if c < MIN_CREDIT_TOMAN:
        return "UNDER_MIN_DEPOSIT", f"deposit {c:,} < {MIN_CREDIT_TOMAN:,} (treated as likely scam / placeholder)"

    mt = rec.get("metro_mentions") or {}
    def text_rescue(prefix):
        if mt.get("target_stations"):
            return "NEEDS_LOCATION_VERIFICATION", f"{prefix}; text mentions target metro {','.join(mt['target_stations'])}: {' | '.join(mt['snippets'])}"
        if mt.get("any") and not mt.get("named_non_target") and (rec.get("nearest_sl_m") or 0) <= UNNAMED_MENTION_MAX_SL_M:
            return "NEEDS_LOCATION_VERIFICATION", f"{prefix}; text mentions an unnamed metro: {' | '.join(mt['snippets'])}"
        return None

    if rec.get("latitude") is None:
        res = text_rescue("no usable coordinates")
        return res or ("NEEDS_LOCATION_VERIFICATION", f"no usable coordinates ({rec.get('coord_status')})")
    w = rec.get("nearest_walk_m")
    if w is not None:
        if w <= SECONDARY_M:
            base = f"walk {w:.0f} m to {rec['nearest_walk_station']} ({rec['walk_class']})"
            if rec.get("coord_confidence") != "api_exact_pin":
                # Blurred pin alone is not enough; the ad naming a station the pin is within walking range of corroborates it
                walks = json.loads(rec.get("walk_all_json") or "{}")
                named = [k for k in mt.get("target_stations", []) if walks.get(k, 1e9) <= SECONDARY_M]
                if named:
                    return "MATCH_VERIFIED", (f"{base}; Divar pin is {rec.get('location_type')} (±{rec.get('coord_radius_m')} m) "
                                              f"but ad text names metro {','.join(named)}: {' | '.join(mt['snippets'])}")
                return "MATCH_PROVISIONAL_DISTANCE", f"{base}, but Divar pin is {rec.get('location_type')} (±{rec.get('coord_radius_m')} m)"
            return "MATCH_VERIFIED", base
        res = text_rescue(f"pin is {w:.0f} m walk from nearest target station")
        return res or ("TOO_FAR_FROM_METRO", f"walk {w:.0f} m > {SECONDARY_M} m to {rec['nearest_walk_station']}" +
                       (f"; mentions other metro: {' | '.join(mt['snippets'])}" if mt.get("any") else ""))
    # No routed walk yet: estimated walk = straight line x DETOUR_FACTOR (always provisional)
    sl, est = rec.get("nearest_sl_m"), rec.get("est_walk_m")
    if est is not None and est <= SECONDARY_M:
        return "MATCH_PROVISIONAL_DISTANCE", (f"estimated walk {est:.0f} m (straight_line_distance_m {sl:.0f} x {DETOUR_FACTOR}) to "
                                              f"{rec['nearest_sl_station']}; not routed yet - run routing_check.py")
    res = text_rescue(f"pin is ~{est:.0f} m estimated walk ({sl:.0f} m straight-line) from nearest target station")
    return res or ("TOO_FAR_FROM_METRO", f"estimated walk {est:.0f} m > {SECONDARY_M} m (straight-line {sl:.0f} m)" +
                   (f"; mentions other metro: {' | '.join(mt['snippets'])}" if mt.get("any") else ""))
