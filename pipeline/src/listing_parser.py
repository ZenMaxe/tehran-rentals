"""Phase F: text normalisation, money parsing, and Divar post-detail parsing."""
import re

from geolocation import extract_map_location

_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_INVISIBLE = re.compile(r"[​-‏‪-‮⁦-⁩﻿]")
_SEP = re.compile(r"[,٬،\s]")

TOMAN_PER_RIAL = 0.1


def normalize_digits(s: str) -> str:
    return _INVISIBLE.sub("", s or "").translate(_DIGITS)


def rial_to_toman(rial: int) -> int:
    return rial // 10


def toman_to_rial(toman: int) -> int:
    return toman * 10


def parse_money_toman(text: str | None) -> tuple[int | None, str]:
    """Parse a human price string into toman. Returns (value, kind).

    kind: AMOUNT, ZERO (رهن کامل/رایگان -> rent 0), NEGOTIABLE (توافقی), UNKNOWN.
    """
    if text is None:
        return None, "UNKNOWN"
    t = normalize_digits(text)
    if "توافقی" in t:
        return None, "NEGOTIABLE"
    if "رایگان" in t or "رهن کامل" in t:
        return 0, "ZERO"
    m = re.search(r"(\d[\d,٬،\s.]*)", t)
    if not m:
        return None, "UNKNOWN"
    num = _SEP.sub("", m.group(1)).rstrip(".")
    try:
        val = float(num) if "." in num else int(num)
    except ValueError:
        return None, "UNKNOWN"
    if "میلیارد" in t:
        val *= 1_000_000_000
    elif "میلیون" in t:
        val *= 1_000_000
    elif "هزار" in t:
        val *= 1_000
    if "ریال" in t and "تومان" not in t:
        val = val / 10
    return int(val), "AMOUNT"


def parse_post_row(widget: dict) -> dict:
    """Search-list POST_ROW -> summary (prices as shown on the card)."""
    d = widget["data"]
    wi = d.get("action", {}).get("payload", {}).get("web_info", {})
    top, mid = d.get("top_description_text") or "", d.get("middle_description_text") or ""
    credit, ck = (parse_money_toman(top) if "ودیعه" in top else (None, "UNKNOWN"))
    rent, rk = (parse_money_toman(mid) if ("اجاره" in mid or "رهن کامل" in mid) else (None, "UNKNOWN"))
    if "رهن کامل" in mid:
        rent, rk = 0, "ZERO"
    return {"token": d.get("token"), "title": d.get("title"), "district_fa": wi.get("district_persian"),
            "card_credit_text": top, "card_rent_text": mid, "card_credit": credit, "card_rent": rent,
            "card_credit_kind": ck, "card_rent_kind": rk, "red_text": d.get("red_text"),
            "bottom_text": d.get("bottom_description_text")}


def _widgets(post):
    for sec in post.get("sections") or []:
        for w in sec.get("widgets") or []:
            yield sec.get("section_name"), w
            for inner in (w.get("data") or {}).get("widget_list") or []:
                yield sec.get("section_name"), inner


def _int_or_none(s):
    s = normalize_digits(str(s)) if s is not None else ""
    m = re.search(r"-?\d+", s)
    return int(m.group()) if m else None


def parse_post_detail(post: dict) -> dict:
    """posts-v2/web/{token} JSON -> flat record. Missing values stay None."""
    we = post.get("webengage") or {}
    rec = {
        "token": we.get("token"), "url": (post.get("share") or {}).get("web_url"),
        "title": None, "category": we.get("category"), "city": we.get("city"),
        "district_slug": we.get("district"), "business_type": we.get("business_type"),
        "we_credit": we.get("credit"), "we_rent": we.get("rent"),
        "text_credit": None, "text_rent": None, "text_credit_raw": None, "text_rent_raw": None,
        "convertible": None, "area_m2": None, "rooms": None, "year_built": None, "floor": None,
        "elevator": None, "parking": None, "storage": None, "photo_count": 0, "photos": [],
        "subtitle": None, "published": None, "last_bump": None, "description": None,
        "unavailable_after": (post.get("seo") or {}).get("unavailable_after"),
    }
    for sec, w in _widgets(post):
        t, d = w.get("widget_type"), w.get("data") or {}
        if t == "LEGEND_TITLE_ROW":
            rec["title"] = d.get("title")
        elif t == "EXPANDABLE_SECTION" and sec == "TITLE":
            rec["subtitle"] = d.get("title")
        elif t == "DESCRIPTION_ROW":
            txt = d.get("text") or ""
            if sec == "DESCRIPTION":
                rec["description"] = txt
            elif "انتشار آگهی" in txt or "نردبان" in txt:
                for line in txt.splitlines():
                    if "انتشار" in line:
                        rec["published"] = line.split(":", 1)[-1].strip()
                    if "نردبان" in line:
                        rec["last_bump"] = line.split(":", 1)[-1].strip()
        elif t == "GROUP_INFO_ROW":
            for it in d.get("items") or []:
                ti, v = it.get("title", ""), it.get("value")
                if "متراژ" in ti:
                    rec["area_m2"] = _int_or_none(v)
                elif "ساخت" in ti:
                    rec["year_built"] = _int_or_none(v)
                elif "اتاق" in ti:
                    rec["rooms"] = 0 if v and "بدون" in v else _int_or_none(v)
        elif t == "UNEXPANDABLE_ROW":
            ti, v = d.get("title", ""), d.get("value")
            if ti.strip() == "ودیعه":
                rec["text_credit_raw"] = v
                rec["text_credit"], _ = parse_money_toman(v)
            elif ti.strip().startswith("اجار"):
                rec["text_rent_raw"] = v
                rec["text_rent"], _ = parse_money_toman(v)
            elif "ودیعه و اجاره" in ti:
                rec["convertible"] = None if not v else ("غیر" not in v)
            elif ti.strip() == "طبقه":
                rec["floor"] = normalize_digits(v) if v else None
        elif t == "RENT_SLIDER":
            # Convertible ad: credit/rent .value are the advertised pair (absent = 0, protobuf default);
            # transformed_value is one alternative split, recorded but never used for eligibility.
            cv, rv = (d.get("credit") or {}).get("value"), (d.get("rent") or {}).get("value")
            rec["text_credit_raw"], rec["text_rent_raw"] = f"RENT_SLIDER credit.value={cv}", f"RENT_SLIDER rent.value={rv}"
            rec["text_credit"], rec["text_rent"] = int(cv or 0), int(rv or 0)
            rec["convertible"] = True
            rec["convertible_alternative"] = (f"credit {(d.get('credit') or {}).get('transformed_value')} / "
                                              f"rent {(d.get('rent') or {}).get('transformed_value')}")
        elif t == "GROUP_FEATURE_ROW":
            for it in d.get("items") or []:
                ti = it.get("title", "")
                val = not ("ندارد" in ti)
                if "آسانسور" in ti:
                    rec["elevator"] = val
                elif "پارکینگ" in ti:
                    rec["parking"] = val
                elif "انباری" in ti:
                    rec["storage"] = val
        elif t == "IMAGE_CAROUSEL":
            rec["photos"] = [i["image"]["url"] for i in d.get("items") or [] if i.get("image")]
            rec["photo_count"] = len(rec["photos"])
    # Neighbourhood text: "هفته پیش در تهران، ارامنه، خ سادگی"
    if rec["subtitle"] and " در " in rec["subtitle"]:
        parts = [p.strip() for p in rec["subtitle"].split(" در ", 1)[1].split("،")]
        rec["neighborhood_fa"] = parts[1] if len(parts) > 1 else None
        rec["street_hint"] = "، ".join(parts[2:]) or None
    else:
        rec["neighborhood_fa"] = rec["street_hint"] = None
    rec.update(extract_map_location(post))
    rec["credit"], rec["rent"], rec["price_conflict"] = reconcile_prices(rec)
    return rec


def reconcile_prices(rec) -> tuple[int | None, int | None, str | None]:
    """Prefer webengage numeric (verified toman); cross-check against the visible text rows."""
    notes = []
    out = []
    for f in ("credit", "rent"):
        we, tx = rec.get(f"we_{f}"), rec.get(f"text_{f}")
        raw = rec.get(f"text_{f}_raw")
        if we is not None and tx is not None and int(we) != int(tx):
            notes.append(f"{f}: webengage={we} text={tx}")
            out.append(None)  # conflict -> manual review, don't pick one
        elif tx is not None:
            out.append(int(tx))
        elif raw is None and we not in (None,):
            # no text row at all: webengage 0 is ambiguous (missing vs zero) unless it's rent with credit present
            out.append(int(we) if we else (0 if f == "rent" and rec.get("text_credit") is not None else None))
        else:
            out.append(None)
    return out[0], out[1], "; ".join(notes) or None
