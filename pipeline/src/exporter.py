"""CSV / XLSX exports. HTML dashboard and markdown reports live in report.py."""
import json

import pandas as pd

from config import MAX_CREDIT_TOMAN, MAX_RENT_TOMAN, OUTPUTS

MATCH = ("MATCH_VERIFIED", "MATCH_PROVISIONAL_DISTANCE")
COLS = ["status", "reason", "token", "url", "title", "neighborhood_fa", "street_hint", "found_in_districts",
        "supplementary_area", "credit", "rent", "convertible", "area_m2", "rooms", "year_built", "floor", "elevator",
        "parking", "storage", "photo_count", "business_type", "published", "last_bump",
        "latitude", "longitude", "location_type", "coord_status", "coord_confidence", "coord_radius_m", "location_source_path",
        "nearest_walk_station", "nearest_walk_m", "walk_minutes", "walk_class",
        "est_walk_m", "est_walk_minutes", "est_walk_class", "route_vs_estimate",
        "nearest_sl_station", "nearest_sl_m", "sl_class_provisional", "routing_note",
        "metro_mention_targets", "metro_mention_snippets",
        "we_credit", "we_rent", "text_credit_raw", "text_rent_raw", "card_credit_text", "card_rent_text",
        "convertible_alternative", "price_conflict", "possible_repost_of", "repost_evidence", "duplicate_of",
        "fetch_status", "fetch_error", "unavailable_after", "walk_all_json", "sl_all_json", "description"]


def to_frame(recs) -> pd.DataFrame:
    rows = []
    for r in recs:
        r = dict(r)
        mm = r.pop("metro_mentions", {}) or {}
        r["metro_mention_targets"] = ",".join(mm.get("target_stations", []))
        r["metro_mention_snippets"] = " | ".join(mm.get("snippets", []))
        r.pop("photos", None)
        rows.append(r)
    df = pd.DataFrame(rows)
    for c in COLS:
        if c not in df:
            df[c] = None
    return df[COLS]


def rank(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["_dist"] = d.nearest_walk_m.fillna(d.est_walk_m)
    d["_budget"] = d.credit / MAX_CREDIT_TOMAN + d.rent / MAX_RENT_TOMAN
    d["_conf"] = (d.status != "MATCH_VERIFIED").astype(int)
    d = d.sort_values(["_conf", "_dist", "_budget"]).drop(columns=["_dist", "_budget", "_conf"])
    d.insert(0, "rank", range(1, len(d) + 1))
    return d


def export(st, nb, log_rows, recs, meta):
    df = to_frame(recs)
    df.drop(columns=["description"]).to_csv(OUTPUTS / "all_listings.csv", index=False, encoding="utf-8-sig")
    rej = df[~df.status.isin(MATCH + ("NEEDS_LOCATION_VERIFICATION",))]
    rej.drop(columns=["description"]).to_csv(OUTPUTS / "rejected_listings.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(log_rows).to_csv(OUTPUTS / "search_log.csv", index=False, encoding="utf-8-sig")

    m = df[df.status.isin(MATCH)]
    with pd.ExcelWriter(OUTPUTS / "matching_apartments.xlsx", engine="openpyxl") as xw:
        rank(m[~m.supplementary_area.fillna(False).astype(bool)]).to_excel(xw, sheet_name="matches", index=False)
        for k in st[st.kind == "metro_station"].itertuples():
            sub = m[(m.nearest_walk_station == k.station_key) | (m.nearest_walk_station.isna() & (m.nearest_sl_station == k.station_key))]
            if len(sub):
                rank(sub).to_excel(xw, sheet_name=k.station_en[:31], index=False)
        supp = df[df.supplementary_area.fillna(False).astype(bool) & df.credit.notna() & df.rent.notna()
                  & ~df.status.isin(("OVER_DEPOSIT_BUDGET", "OVER_RENT_BUDGET", "UNAVAILABLE"))]
        supp.to_excel(xw, sheet_name="Majidiyeh_supplementary", index=False)
        # negotiable-price ads: kept apart from strict matches as the brief requires
        df[df.reason.str.contains("negotiable", na=False)].to_excel(xw, sheet_name="negotiable_not_strict", index=False)
        pd.DataFrame([{"key": k, "value": json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v}
                      for k, v in meta.items()]).to_excel(xw, sheet_name="run_info", index=False)
    nlv = df[df.status == "NEEDS_LOCATION_VERIFICATION"]
    with pd.ExcelWriter(OUTPUTS / "needs_location_verification.xlsx", engine="openpyxl") as xw:
        nlv.sort_values("nearest_sl_m").to_excel(xw, sheet_name="needs_location_verification", index=False)
    import report
    report.write_all(st, nb, log_rows, df, meta)
