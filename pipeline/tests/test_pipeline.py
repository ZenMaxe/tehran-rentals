import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from config import MAX_CREDIT_TOMAN, MAX_RENT_TOMAN  # noqa: E402
from deduplication import repost_score  # noqa: E402
from distance_calculator import classify_distance  # noqa: E402
from filters import classify, metro_mentions  # noqa: E402
from geolocation import (bbox_to_latlon, extract_map_location, from_geojson, haversine_m,  # noqa: E402
                         to_geojson, to_google, validate_point)
from listing_parser import (normalize_digits, parse_money_toman, parse_post_detail,  # noqa: E402
                            rial_to_toman, toman_to_rial)

FIX = json.loads((Path(__file__).resolve().parent.parent / "fixtures" / "gaSfxzZ8.json").read_text())


def test_digits_and_invisible_marks():
    assert normalize_digits("‏۷۰۰,۰۰۰,۰۰۰") == "700,000,000"
    assert normalize_digits("٣٤٥") == "345"


@pytest.mark.parametrize("text,val,kind", [
    ("‏۷۰۰,۰۰۰,۰۰۰ تومان", 700_000_000, "AMOUNT"),
    ("ودیعه: ۱,۳۰۰,۰۰۰,۰۰۰ تومان", 1_300_000_000, "AMOUNT"),
    ("۲۰ میلیون تومان", 20_000_000, "AMOUNT"),
    ("۱.۵ میلیارد تومان", 1_500_000_000, "AMOUNT"),
    ("۵,۰۰۰,۰۰۰,۰۰۰ ریال", 500_000_000, "AMOUNT"),
    ("رهن کامل", 0, "ZERO"),
    ("توافقی", None, "NEGOTIABLE"),
])
def test_money(text, val, kind):
    assert parse_money_toman(text) == (val, kind)


def test_toman_rial():
    assert toman_to_rial(500_000_000) == 5_000_000_000
    assert rial_to_toman(200_000_000) == 20_000_000


def _ok(c, r):
    rec = {"credit": c, "rent": r, "latitude": 35.68, "longitude": 51.40, "nearest_walk_m": 300,
           "nearest_walk_station": "moniriyeh", "walk_class": "Excellent", "coord_confidence": "api_exact_pin"}
    return classify(rec)[0]


@pytest.mark.parametrize("c,r,ok", [
    (300_000_000, 15_000_000, True), (MAX_CREDIT_TOMAN, MAX_RENT_TOMAN, True),
    (MAX_CREDIT_TOMAN, MAX_RENT_TOMAN + 1, False), (MAX_CREDIT_TOMAN + 1, 9_000_000, False),
    (700_000_000, 9_000_000, False), (200_000_000, 25_000_000, False), (500_000_000, 0, True), (75_000_000, 5_000_000, True),
])
def test_budget_boundaries(c, r, ok):
    assert (_ok(c, r) == "MATCH_VERIFIED") is ok


def test_fixture_webengage_and_text():
    rec = parse_post_detail(FIX)
    assert rec["we_credit"] == 700_000_000 and rec["we_rent"] == 9_000_000
    assert rec["text_credit"] == 700_000_000 and rec["text_rent"] == 9_000_000
    assert rec["credit"] == 700_000_000 and rec["rent"] == 9_000_000 and rec["price_conflict"] is None
    assert rec["area_m2"] == 54 and rec["rooms"] == 1 and rec["year_built"] == 1388
    assert rec["elevator"] is False and rec["parking"] is True and rec["storage"] is False
    assert rec["url"] == "https://divar.ir/v/gaSfxzZ8" and rec["neighborhood_fa"] == "ارامنه"


def test_fixture_coordinates():
    loc = extract_map_location(FIX)
    assert loc["latitude"] == 35.722982464614 and loc["longitude"] == 51.460563657123
    assert loc["coord_status"] == "VALID"
    assert loc["location_source_path"].endswith("exact_data.point")


def test_fixture_rejected_over_deposit():
    rec = parse_post_detail(FIX)
    rec.update(nearest_walk_m=500, nearest_walk_station="x", walk_class="Excellent")
    assert classify(rec)[0] == "OVER_DEPOSIT_BUDGET"


def test_typed_exact_location():
    p = copy.deepcopy(FIX)
    for s in p["sections"]:
        for w in s["widgets"]:
            if w["widget_type"] == "MAP_ROW":
                w["data"]["location"]["type"] = "EXACT"
    assert extract_map_location(p)["location_type"] == "EXACT"


def test_missing_map_row():
    p = copy.deepcopy(FIX)
    p["sections"] = [s for s in p["sections"] if s["section_name"] != "MAP"]
    loc = extract_map_location(p)
    assert loc["latitude"] is None and loc["coord_status"] == "MISSING"


def test_swapped_detection_not_corrected():
    assert validate_point(51.46, 35.72)[0] == "SWAPPED_SUSPECT"
    p = copy.deepcopy(FIX)
    for s in p["sections"]:
        for w in s["widgets"]:
            if w["widget_type"] == "MAP_ROW":
                w["data"]["location"]["exact_data"]["point"] = {"latitude": 51.46, "longitude": 35.72}
    loc = extract_map_location(p)
    assert loc["coord_status"] == "SWAPPED_SUSPECT" and loc["latitude"] is None


def test_coordinate_orders():
    assert to_google(35.7, 51.4) == "35.7,51.4"
    assert to_geojson(35.7, 51.4) == [51.4, 35.7]
    assert from_geojson([51.4, 35.7]) == (35.7, 51.4)
    assert bbox_to_latlon([51.43, 35.67, 51.44, 35.68]) == (35.67, 51.43, 35.68, 51.44)


def test_haversine():
    assert haversine_m(35.7, 51.4, 35.7, 51.4) == 0
    # 0.01 deg latitude ~ 1112 m
    assert abs(haversine_m(35.70, 51.4, 35.71, 51.4) - 1112) < 3


@pytest.mark.parametrize("m,c", [(0, "Excellent"), (800, "Excellent"), (801, "Acceptable"), (1200, "Acceptable"),
                                 (1500, "Secondary"), (1501, "Excluded (>1500 m)"), (None, None)])
def test_walk_class(m, c):
    assert classify_distance(m) == c


def test_estimated_walk_is_provisional():
    base = {"credit": 300_000_000, "rent": 10_000_000, "latitude": 35.68, "longitude": 51.40,
            "coord_confidence": "api_exact_pin", "nearest_sl_station": "moniriyeh"}
    assert classify(dict(base, nearest_sl_m=1000, est_walk_m=1320))[0] == "MATCH_PROVISIONAL_DISTANCE"
    assert classify(dict(base, nearest_sl_m=1200, est_walk_m=1584))[0] == "TOO_FAR_FROM_METRO"


def test_rent_slider_convertible():
    p = copy.deepcopy(FIX)
    for s in p["sections"]:
        if s["section_name"] == "LIST_DATA":
            s["widgets"] = [w for w in s["widgets"] if w["widget_type"] != "UNEXPANDABLE_ROW"] + [
                {"widget_type": "RENT_SLIDER", "data": {"credit": {"value": "410000000", "transformed_value": "300000000"},
                                                       "rent": {"transformed_value": "3800000"}}}]
    p["webengage"].update(credit=410000000, rent=0)
    rec = parse_post_detail(p)
    assert (rec["credit"], rec["rent"], rec["convertible"], rec["price_conflict"]) == (410_000_000, 0, True, None)


def test_negotiable_and_non_apartment():
    base = {"latitude": 35.68, "longitude": 51.40, "nearest_walk_m": 100, "nearest_walk_station": "jahad",
            "walk_class": "Excellent", "coord_confidence": "api_exact_pin"}
    st, why = classify(dict(base, credit=None, rent=5_000_000, text_credit_raw="توافقی"))
    assert st == "PARSING_ERROR" and "negotiable" in why
    for t in ("خوابگاه دخترانه آنا", "پارکینگ ماشین در میدان ولیعصر", "اجاره اتاق مبله"):
        assert classify(dict(base, credit=100_000_000, rent=1, title=t))[0] == "WRONG_CATEGORY", t
    assert classify(dict(base, credit=100_000_000, rent=1, title="آپارتمان ۵۰ متری با پارکینگ"))[0] == "MATCH_VERIFIED"


def test_fuzzy_pin_corroborated_by_text():
    rec = {"credit": 300_000_000, "rent": 10_000_000, "latitude": 35.67, "longitude": 51.38, "coord_confidence": "api_approximate",
           "location_type": "FUZZY", "coord_radius_m": 500, "nearest_walk_m": 400, "nearest_walk_station": "beryanak",
           "walk_class": "Excellent", "walk_all_json": '{"beryanak": 400, "helal_ahmar": 1900}'}
    assert classify(dict(rec, metro_mentions=metro_mentions("۵۳ متر/مترو بریانک", "")))[0] == "MATCH_VERIFIED"
    # naming a station the pin is NOT within walking range of does not corroborate
    assert classify(dict(rec, metro_mentions=metro_mentions("نزدیک مترو هلال احمر", "")))[0] == "MATCH_PROVISIONAL_DISTANCE"
    assert classify(dict(rec, metro_mentions=metro_mentions("آپارتمان ۵۰ متری", "")))[0] == "MATCH_PROVISIONAL_DISTANCE"


def test_min_deposit():
    rec = {"credit": 74_999_999, "rent": 5_000_000, "latitude": 35.68, "longitude": 51.40, "nearest_walk_m": 100,
           "nearest_walk_station": "jahad", "walk_class": "Excellent", "coord_confidence": "api_exact_pin"}
    assert classify(rec)[0] == "UNDER_MIN_DEPOSIT"
    assert classify(dict(rec, credit=75_000_000))[0] == "MATCH_VERIFIED"


def test_dedup():
    a = {"token": "a", "credit": 1, "rent": 2, "area_m2": 50, "rooms": 1, "latitude": 35.7, "longitude": 51.4,
         "title": "آپارتمان ۵۰ متری", "description": "x" * 50, "photos": ["p1"]}
    b = dict(a, token="b", latitude=35.7001)
    likely, strong, _ = repost_score(a, b)
    assert likely and strong
    c = dict(a, token="c", area_m2=60, photos=[])
    assert repost_score(a, c)[0] is False


def test_metro_mentions():
    m = metro_mentions("آپارتمان نزدیک مترو", "دسترسی ۵ دقیقه به مترو هفت تیر")
    assert m["target_stations"] == ["haft_tir"]
    m = metro_mentions(None, FIX_DESC := "دسترسی 4دقیقه به مترو مدنی")
    assert m["any"] and m["target_stations"] == [] and m["named_non_target"]
    assert metro_mentions("خیابان ولیعصر", "")["any"] is False  # street, not metro


def test_far_pin_rescued_by_text():
    base = {"credit": 400_000_000, "rent": 10_000_000, "latitude": 35.80, "longitude": 51.40,
            "nearest_walk_m": 4000, "nearest_walk_station": "jahad", "nearest_sl_m": 3500}
    rec = dict(base, metro_mentions=metro_mentions("", "۲ دقیقه تا مترو میدان جهاد"))
    assert classify(rec)[0] == "NEEDS_LOCATION_VERIFICATION"
    rec = dict(base, metro_mentions=metro_mentions("", "نزدیک مترو مدنی"))
    assert classify(rec)[0] == "TOO_FAR_FROM_METRO"


def test_fuzzy_pin_is_provisional():
    p = copy.deepcopy(FIX)
    for s in p["sections"]:
        for w in s["widgets"]:
            if w["widget_type"] == "MAP_ROW":
                w["data"]["location"] = {"type": "FUZZY", "fuzzy_data": {"point": {"latitude": 35.681, "longitude": 51.401}, "radius": 500}}
    loc = extract_map_location(p)
    assert loc["coord_status"] == "APPROXIMATE" and loc["coord_radius_m"] == 500 and loc["latitude"] == 35.681
    rec = dict(loc, credit=100_000_000, rent=5_000_000, nearest_walk_m=300, nearest_walk_station="moniriyeh", walk_class="Excellent")
    assert classify(rec)[0] == "MATCH_PROVISIONAL_DISTANCE"


def test_roommate_ads_rejected():
    rec = {"credit": 100_000_000, "rent": 1_000_000, "title": "همخونه آقا هستم متقاضی اتاق", "latitude": 35.68, "longitude": 51.40,
           "nearest_walk_m": 50, "nearest_walk_station": "moniriyeh", "walk_class": "Excellent", "coord_confidence": "api_exact_pin"}
    assert classify(rec)[0] == "WRONG_CATEGORY"
    assert classify(dict(rec, title="آپارتمان ۶۰ متری"))[0] == "MATCH_VERIFIED"
