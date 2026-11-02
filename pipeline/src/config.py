"""Central configuration: budget, target stations, paths, service endpoints."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"
OUTPUTS = ROOT / "outputs"
FIXTURES = ROOT / "fixtures"

# 'target15' = the 15 stations below; 'all_tehran' = every OSM subway station inside Divar's Tehran districts
STATION_SCOPE = "all_tehran"
FAR_SOUTH_LAT = 35.63  # stations south of this are flagged (original brief: avoid far south / Azadegan)

# Budget in TOMAN (unit verified empirically, see outputs/currency_filter_verification.md)
MAX_CREDIT_TOMAN = 500_000_000
MIN_CREDIT_TOMAN = 75_000_000  # user: deposits under 75M are scams
MAX_RENT_TOMAN = 17_000_000  # user lowered from 20M on 2026-10-28

# Walking-distance classes (metres, inclusive upper bounds)
EXCELLENT_M = 800
ACCEPTABLE_M = 1200
SECONDARY_M = 1500

# Estimated walk = straight line x factor, until routing_check.py replaces it with a real route.
# 1.32 = median OSRM-foot/straight-line ratio over 1,491 listing->entrance pairs (300-2000 m) measured 2026-10-28.
DETOUR_FACTOR = 1.32
WALK_SPEED_MPS = 1.25  # OSRM foot profile speed

# Districts whose Divar centroid or bbox comes within this radius of a station get searched.
DISTRICT_SEARCH_RADIUS_M = 1800

# (key, Persian, English, OSM element "type/id") - OSM ids pinned after manual inspection
# of Overpass results on 2026-10-28; Beryanak exists only as a station *way* in OSM.
STATIONS = [
    ("mahdieh", "مهدیه", "Mahdieh", "node/11417020371"),
    ("moniriyeh", "منیریه", "Moniriyeh", "node/14084275563"),
    ("teatr_shahr", "تئاتر شهر", "Teatr-e Shahr", "node/5162910432"),
    ("vali_asr", "حضرت ولی عصر", "Hazrat-e Vali Asr", "node/10760685493"),
    ("jahad", "جهاد", "Jahad", "node/14060804178"),
    ("mirza_shirazi", "میرزای شیرازی", "Mirza-ye Shirazi", "node/8730248893"),
    ("shahid_beheshti", "شهید بهشتی", "Shahid Beheshti", "node/5540220849"),
    ("sohrevardi", "سهروردی", "Sohrevardi", "node/3778861785"),
    ("saadi", "سعدی", "Saadi", "node/13380785610"),
    ("darvazeh_dowlat", "دروازه دولت", "Darvazeh Dowlat", "node/5188247275"),
    ("taleghani", "طالقانی", "Taleghani", "node/13380785625"),
    ("haft_tir", "شهدای هفتم تیر", "Shohada-ye Haft-e Tir", "node/5183508081"),
    ("mofatteh", "شهید مفتح", "Shahid Mofatteh", "node/13381123725"),
    ("helal_ahmar", "هلال احمر", "Helal Ahmar", "node/3784645954"),
    ("beryanak", "بریانک", "Beryanak", "way/678594658"),
]

# Supplementary area (not a metro station): OSM neighbourhood node 6172365019
SUPPLEMENTARY = [("majidiyeh", "مجیدیه", "Majidiyeh", "node/6172365019")]

UA = "tehran-metro-rentals/0.1 (personal apartment search; contact via repo owner)"
OVERPASS = "https://overpass-api.de/api/interpreter"
DIVAR_SEARCH = "https://api.divar.ir/v8/postlist/w/search"
DIVAR_POST = "https://api.divar.ir/v8/posts-v2/web/{token}"
DIVAR_DISTRICTS = "https://api.divar.ir/v8/places/cities/1/districts"
FOOT_ROUTER = "https://routing.openstreetmap.de/routed-foot"
REQUEST_DELAY_S = 1.2  # polite spacing between Divar search requests
DETAIL_DELAY_S = 1.2  # serial; 0.35 s x 4 parallel workers triggered HTTP 429 on 2026-10-29
