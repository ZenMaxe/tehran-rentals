"""report.html (Leaflet, RTL Persian), data_quality_report.md, FINAL_REPORT.md - all generated from run data."""
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from config import (ACCEPTABLE_M, CACHE, DETOUR_FACTOR, DISTRICT_SEARCH_RADIUS_M, EXCELLENT_M, MAX_CREDIT_TOMAN, MAX_RENT_TOMAN, MIN_CREDIT_TOMAN,
                    OUTPUTS, SECONDARY_M)

MATCH = ("MATCH_VERIFIED", "MATCH_PROVISIONAL_DISTANCE")
STATUSES = ["MATCH_VERIFIED", "MATCH_PROVISIONAL_DISTANCE", "NEEDS_LOCATION_VERIFICATION", "OVER_DEPOSIT_BUDGET",
            "OVER_RENT_BUDGET", "UNDER_MIN_DEPOSIT", "TOO_FAR_FROM_METRO", "WRONG_CATEGORY", "UNAVAILABLE", "DUPLICATE", "PARSING_ERROR",
            "ACCESS_BLOCKED"]


def _n(x):
    return None if pd.isna(x) else x


def fmt(v):
    return "—" if v is None or (isinstance(v, float) and pd.isna(v)) else f"{int(v):,}"


def md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for r in df.itertuples(index=False):
        out.append("| " + " | ".join("—" if (isinstance(v, float) and pd.isna(v)) or v is None else str(v).replace("|", "/").replace("\n", " ") for v in r) + " |")
    return "\n".join(out)


def write_all(st, nb, log_rows, df, meta):
    write_html(st, df, meta)
    write_quality(df, log_rows, meta)
    write_final(st, nb, log_rows, df, meta)


# ---------------------------------------------------------------- HTML
def write_html(st, df, meta):
    names = {r.station_key: r.station_fa for r in st.itertuples()}
    show = df[df.status.isin(MATCH + ("NEEDS_LOCATION_VERIFICATION",))]
    listings = []
    for r in show.itertuples():
        stn = _n(r.nearest_walk_station) or _n(r.nearest_sl_station)
        listings.append({"t": r.token, "u": r.url, "ti": r.title, "s": r.status, "nb": _n(r.neighborhood_fa) or "",
                         "c": _n(r.credit), "r": _n(r.rent), "a": _n(r.area_m2), "rm": _n(r.rooms), "y": _n(r.year_built),
                         "lat": _n(r.latitude), "lon": _n(r.longitude), "lt": _n(r.location_type), "rad": _n(r.coord_radius_m),
                         "st": stn, "stfa": names.get(stn, ""), "w": _n(r.nearest_walk_m), "wm": _n(r.walk_minutes),
                         "sl": _n(r.nearest_sl_m), "e": _n(r.est_walk_m), "em": _n(r.est_walk_minutes), "why": r.reason, "pub": _n(r.published), "supp": bool(r.supplementary_area)})
    stations = [{"k": r.station_key, "fa": r.station_fa, "en": r.station_en, "lines": r.lines if isinstance(r.lines, str) else "",
                 "lat": r.lat, "lon": r.lon, "ents": json.loads(r.entrances_json), "kind": r.kind} for r in st.itertuples()]
    collected = datetime.fromisoformat(meta["finished_utc"]).strftime("%Y-%m-%d %H:%M UTC")
    data = json.dumps({"listings": listings, "stations": stations, "collected": collected,
                       "budget": [MAX_CREDIT_TOMAN, MAX_RENT_TOMAN, MIN_CREDIT_TOMAN], "inspected": int(len(df)),
                       "counts": df.status.value_counts().to_dict()}, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    # Leaflet inlined: viewers and some networks block third-party CSS/JS, and without L the whole page stops
    css = (Path(__file__).parent / "assets" / "leaflet-1.9.4.css").read_text()
    js = (Path(__file__).parent / "assets" / "leaflet-1.9.4.js").read_text()
    html = HTML.replace("__LEAFLET_CSS__", css).replace("__LEAFLET_JS__", js).replace("__DARK__", DARK).replace("__DATA__", data.replace("</", "<\\/"))
    (OUTPUTS / "report.html").write_text(html, encoding="utf-8")


DARK = ("--page:#09090a;--surface:#151515;--sunken:#1c1c1d;--inverse:#fff;--on-inverse:#151515;--t1:#f5f5f5;--t2:#c9c9c9;--b1:rgba(255,255,255,.08);--b2:#3d3d3d;--b3:#fff;--bh:#7a7a7a;--panel:rgba(24,24,26,.94);--overlay:rgba(0,0,0,.55);--hl-d:rgba(255,255,255,.14);--s8:rgba(0,0,0,.4);--s18:rgba(0,0,0,.55);"
        "--g-fill:rgba(255,255,255,.07);--g-strong:rgba(255,255,255,.11);--g-elev:rgba(255,255,255,.18);--g-card:rgba(255,255,255,.05);--g-stroke:rgba(255,255,255,.12);--hl:rgba(255,255,255,.1);--hl2:rgba(255,255,255,.14);"
        "--s4:rgba(0,0,0,.3);--s6:rgba(0,0,0,.35);--s12:rgba(0,0,0,.45);--s16:rgba(0,0,0,.5);"
        "--ok:#4ade80;--ok-bg:#052e16;--ok-t:#4ade80;--wa:#fbbf24;--wa-bg:#451a03;--wa-t:#fbbf24;--in:#60a5fa;--in-bg:#172554;--in-t:#60a5fa;--er:#f87171;"
        "--amb1:rgba(255,200,40,.10);--amb2:rgba(150,200,80,.07);--amb3:rgba(80,130,255,.11);--amb4:rgba(200,90,140,.07);color-scheme:dark")

HTML = r"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>آپارتمان‌های نزدیک مترو</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>__LEAFLET_CSS__</style>
<script>__LEAFLET_JS__</script>
<style>
/* Look follows the Lemon Design System (lemonui.ir, Figma kit with no code package): its tokens and component shapes, rebuilt here. */
:root{--page:#f4f4f1;--surface:#fff;--sunken:#f2f2f2;--inverse:#151515;--on-inverse:#fff;--t1:#151515;--t2:#5c5c5c;--b1:rgba(0,0,0,.07);--b2:#e3e3e3;--b3:#151515;--bh:#a3a3a3;
--g-fill:rgba(255,255,255,.55);--g-strong:rgba(255,255,255,.78);--g-elev:rgba(255,255,255,.92);--g-card:rgba(255,255,255,.5);--g-stroke:rgba(255,255,255,.75);--hl:rgba(255,255,255,.85);--hl2:rgba(255,255,255,.95);--hl-d:rgba(255,255,255,.22);
--panel:rgba(255,255,255,.93);--s4:rgba(0,0,0,.04);--s6:rgba(0,0,0,.06);--s8:rgba(0,0,0,.08);--s12:rgba(0,0,0,.12);--s16:rgba(0,0,0,.16);--s18:rgba(0,0,0,.18);--overlay:rgba(20,15,46,.28);
--ok:#16a34a;--ok-bg:#f0fdf4;--ok-t:#166534;--wa:#d97706;--wa-bg:#fffbeb;--wa-t:#92400e;--in:#2563eb;--in-bg:#eff6ff;--in-t:#1d4ed8;--er:#dc2626;--lemon:#ffd43b;
--amb1:rgba(255,214,64,.42);--amb2:rgba(196,228,96,.30);--amb3:rgba(140,190,255,.30);--amb4:rgba(255,180,205,.22);color-scheme:light}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){__DARK__}}
:root[data-theme="dark"]{__DARK__}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--page);color:var(--t1);font:13px/1.7 Vazirmatn,Tahoma,"Segoe UI",system-ui,sans-serif}
a{color:inherit}button,input,select{font:inherit;color:inherit}
:focus-visible{outline:2px solid var(--b3);outline-offset:2px}
#amb{position:fixed;inset:0;z-index:-1;pointer-events:none;overflow:hidden}
#amb i{position:absolute;border-radius:50%;filter:blur(90px)}
#amb i:nth-child(1){width:46vw;height:46vw;max-width:640px;max-height:640px;background:var(--amb1);top:-14vw;left:-10vw}
#amb i:nth-child(2){width:38vw;height:38vw;max-width:520px;max-height:520px;background:var(--amb2);top:30vh;left:28vw}
#amb i:nth-child(3){width:42vw;height:42vw;max-width:600px;max-height:600px;background:var(--amb3);top:-8vw;right:-14vw}
#amb i:nth-child(4){width:34vw;height:34vw;max-width:480px;max-height:480px;background:var(--amb4);bottom:-10vw;right:18vw}
.gc{background:var(--g-card);border:1px solid var(--g-stroke);-webkit-backdrop-filter:blur(28px) saturate(1.5);backdrop-filter:blur(28px) saturate(1.5);box-shadow:0 1px 2px var(--s4),0 16px 40px -18px var(--s12),inset 0 1px 0 var(--hl)}
.hdr{position:sticky;top:calc(env(safe-area-inset-top,0px) + 14px);z-index:1100;display:flex;justify-content:center;padding-inline:16px;pointer-events:none;margin-top:14px}
.cap{pointer-events:auto;display:flex;align-items:center;gap:2px;height:48px;padding:0 8px;border-radius:999px;background:var(--g-strong);border:1px solid var(--g-stroke);-webkit-backdrop-filter:blur(24px) saturate(1.6);backdrop-filter:blur(24px) saturate(1.6);box-shadow:0 1px 2px var(--s4),0 18px 40px -16px var(--s16),inset 0 1px 0 var(--hl2)}
.brand{display:flex;align-items:center;gap:8px;padding:0 8px;font-weight:700;white-space:nowrap}.brand i{width:18px;height:18px;border-radius:50%;background:var(--lemon);box-shadow:inset 0 1px 0 rgba(255,255,255,.7)}
.cap .sep{width:1px;height:20px;background:var(--b1);margin:0 4px}
.cap a{display:inline-flex;align-items:center;height:36px;padding:0 14px;border-radius:999px;font-size:12.5px;color:var(--t2);text-decoration:none;transition:background .2s,color .2s}.cap a:hover{color:var(--t1);background:var(--g-elev);box-shadow:0 2px 8px var(--s6),inset 0 1px 0 var(--hl2)}
main{max-width:1360px;margin:auto;padding:14px 24px calc(48px + env(safe-area-inset-bottom,0px));display:flex;flex-direction:column;gap:14px}
.top{padding-top:14px}h1{margin:0;font-size:28px;font-weight:800;line-height:1.35}.sub{color:var(--t2);font-size:12.5px;margin-top:4px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}
.stat{border-radius:16px;padding:12px 14px}.stat b{display:block;font-size:20px;font-weight:700;font-variant-numeric:tabular-nums;line-height:1.5}.stat span{color:var(--t2);font-size:11px}
.stcounts{display:flex;gap:6px;overflow-x:auto;padding:2px;scrollbar-width:thin}
.chp{flex:none;display:inline-flex;align-items:center;gap:5px;height:28px;padding:0 10px;border-radius:99px;font-size:11.5px;background:var(--g-strong);border:1px solid var(--g-stroke);box-shadow:0 2px 6px var(--s6),inset 0 1px 0 var(--hl2);cursor:pointer;white-space:nowrap}
.chp small{color:var(--t2);font-size:10.5px}.chp b{font-weight:600}
.chp.on{background:var(--inverse);color:var(--on-inverse);border-color:var(--inverse)}.chp.on small{color:inherit;opacity:.75}
#mapsec{position:relative;display:flex;align-items:flex-start;min-height:700px;padding:14px;border-radius:20px;overflow:hidden;background:var(--sunken);border:1px solid var(--g-stroke);box-shadow:0 1px 2px var(--s4),0 16px 40px -18px var(--s12);scroll-margin-top:76px}
#map{position:absolute;inset:0;isolation:isolate;background:var(--sunken)}
.leaflet-container{font:inherit}.leaflet-popup-content-wrapper,.leaflet-popup-tip{background:var(--surface);color:var(--t1);box-shadow:0 16px 40px -14px var(--s16)}.leaflet-popup-content-wrapper{border-radius:16px}.leaflet-popup-content{font-size:12.5px;line-height:1.7;margin:12px 14px}.leaflet-popup-content a{color:var(--t1)}
.legend{position:absolute;bottom:32px;left:14px;z-index:900;display:flex;flex-direction:column;gap:2px;padding:8px 12px;border-radius:12px;font-size:11px;color:var(--t1);background:var(--panel);box-shadow:0 2px 6px var(--s6);pointer-events:none}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-left:6px;vertical-align:middle;flex:none}
#filters{position:relative;z-index:1000;width:min(320px,100%);padding:14px;border-radius:18px;background:var(--panel);border:1px solid var(--g-stroke);-webkit-backdrop-filter:blur(20px) saturate(1.4);backdrop-filter:blur(20px) saturate(1.4);box-shadow:0 1px 2px var(--s4),0 8px 24px -10px var(--s8),inset 0 1px 0 var(--hl);display:flex;flex-direction:column;gap:12px}
.fhead{display:flex;align-items:center;gap:8px;min-height:28px}.fhead strong{font-size:13px;font-weight:700}
.fc{min-width:18px;height:18px;padding:0 5px;border-radius:99px;background:var(--lemon);color:#151515;font-size:10.5px;font-weight:700;display:inline-grid;place-items:center}.fc[hidden],.clr[hidden]{display:none}
.clr{margin-inline-start:auto;height:28px;padding:0 10px;border:0;border-radius:8px;background:transparent;color:var(--t2);font-size:11.5px;font-weight:500;cursor:pointer}.clr:hover{background:var(--sunken);color:var(--t1)}
.f{display:flex;flex-direction:column;gap:5px;min-width:0}.f>label,.f>span{color:var(--t2);font-size:11.5px}
.row2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
input[type=text],select{width:100%;height:36px;padding:0 12px;border:1px solid var(--b2);border-radius:12px;background:var(--g-strong);font-size:12.5px;outline:0;transition:border-color .15s,box-shadow .15s}
input[type=text]::placeholder{color:var(--t2);opacity:.75}input[type=text]:focus,select:focus{border-color:var(--b3);box-shadow:0 0 0 3px var(--s6)}
select{appearance:none;-webkit-appearance:none;cursor:pointer;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath d='M2.5 4.5 6 8l3.5-3.5' fill='none' stroke='%23888' stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:left 10px center;padding-left:28px}
.seg{display:flex;gap:2px;height:34px;padding:3px;border-radius:12px;background:var(--g-fill);border:1px solid var(--g-stroke);box-shadow:0 1px 2px var(--s4),0 8px 24px -6px var(--s6),inset 0 1px 0 var(--hl)}
.seg button{flex:1;border:0;background:transparent;border-radius:9px;font-size:12px;color:var(--t2);cursor:pointer;padding:0 6px;white-space:nowrap}
.seg button[aria-pressed="true"]{background:var(--inverse);color:var(--on-inverse);font-weight:500}
.opts{display:flex;flex-direction:column;gap:9px}
.opt{position:relative;display:flex;align-items:center;gap:10px;font-size:12.5px;line-height:1.6;cursor:pointer}
.opt input{position:absolute;inset:0;width:100%;height:100%;margin:0;opacity:0;cursor:pointer}
.sw{position:relative;width:40px;height:24px;border-radius:99px;background:var(--g-strong);border:1px solid var(--bh);flex:none;transition:background .2s}
.sw::after{content:"";position:absolute;top:2px;right:2px;width:18px;height:18px;border-radius:50%;background:#fff;box-shadow:0 2px 5px rgba(0,0,0,.16),0 0 1px rgba(0,0,0,.06);transition:right .22s cubic-bezier(.3,.7,.3,1)}
input:checked~.sw{background:var(--inverse);border-color:var(--inverse)}input:checked~.sw::after{right:18px;background:var(--page)}input:focus-visible~.sw{outline:2px solid var(--b3);outline-offset:2px}
.nm{flex:1;min-width:0}.nm small{display:block;color:var(--t2);font-size:11px;line-height:1.5}.opt b{color:var(--t2);font-size:11.5px;font-weight:400;font-variant-numeric:tabular-nums}
.fgo,.msearch,#bd,.wk{display:none}
.tbl{border-radius:16px;overflow:hidden;scroll-margin-top:76px}
.tb{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:10px 14px;flex-wrap:wrap}.tb b{font-size:12.5px;font-weight:700}.tb label{display:flex;align-items:center;gap:8px;font-size:11.5px;color:var(--t2)}.tb select{width:auto;height:28px;border-radius:8px;font-size:11.5px}
.tablewrap{overflow-x:auto}
table{border-collapse:collapse;width:100%;min-width:980px;font-size:11.5px}
th{font-weight:500;color:var(--t2);font-size:10.5px;background:var(--sunken);text-align:right;padding:7px 12px;cursor:pointer;white-space:nowrap}th[data-a]::after{content:attr(data-a);margin-right:3px}
td{padding:8px 12px;border-top:1px solid var(--b1);text-align:right;white-space:nowrap;vertical-align:middle}
tbody tr:hover td{background:var(--g-fill)}td.num{font-variant-numeric:tabular-nums}td.pr{font-weight:600}td.ti{white-space:normal;min-width:240px;font-size:12.5px;font-weight:500}
.tag{display:inline-block;font-size:11px;padding:1px 8px;border-radius:99px;white-space:nowrap}
.MATCH_VERIFIED{background:var(--ok-bg);color:var(--ok-t)}.MATCH_PROVISIONAL_DISTANCE{background:var(--wa-bg);color:var(--wa-t)}.NEEDS_LOCATION_VERIFICATION{background:var(--in-bg);color:var(--in-t)}
.b{display:inline-flex;align-items:center;justify-content:center;height:28px;padding:0 10px;border-radius:8px;font-size:11.5px;font-weight:500;text-decoration:none;white-space:nowrap;background:var(--inverse);color:var(--on-inverse)}
.note{color:var(--t2);font-size:11.5px;margin:0 2px;max-width:80ch}
/* phone: map on top, listings below, filters in a bottom sheet. Cards stay unblurred: hundreds of backdrop-filters stutter on phones. */
@media(max-width:720px){
body{font-size:14px}.hdr{display:none}main{padding:0 0 calc(32px + env(safe-area-inset-bottom,0px));gap:12px}
#mapsec{order:-3;min-height:0;height:340px;padding:0;border:0;border-radius:0;box-shadow:none}
.msearch{position:absolute;top:calc(14px + env(safe-area-inset-top,0px));right:14px;left:14px;z-index:1000;display:flex;align-items:center;gap:4px;height:54px;padding:0 5px;border-radius:999px;background:var(--panel);border:1px solid var(--g-stroke);-webkit-backdrop-filter:blur(24px) saturate(1.6);backdrop-filter:blur(24px) saturate(1.6);box-shadow:0 1px 2px var(--s4),0 18px 40px -16px var(--s16),inset 0 1px 0 var(--hl2)}
.msearch i{flex:none;width:18px;height:18px;margin:0 8px;border-radius:50%;background:var(--lemon)}
.msearch input[type=text],.msearch input[type=text]:focus{flex:1;min-width:0;height:44px;padding:0;border:0;background:none;box-shadow:none;font-size:16px}
.fbtn{flex:none;display:flex;align-items:center;gap:6px;height:44px;padding:0 14px;border:0;border-radius:999px;background:var(--inverse);color:var(--on-inverse);font-size:12.5px;font-weight:500;cursor:pointer}
.leaflet-top.leaflet-left{top:72px}.legend{display:none}
.stcounts{order:-2;margin-top:-30px;position:relative;z-index:1000;padding:14px;border-radius:24px 24px 0 0;background:var(--page);scrollbar-width:none}
.chp{height:44px;padding:0 12px;font-size:12.5px}
.tbl{order:-1;margin-top:-12px;padding-inline:14px;background:none;border:0;box-shadow:none;-webkit-backdrop-filter:none;backdrop-filter:none;overflow:visible}.tb{padding:0 2px 10px}.tb b{font-size:16px;font-weight:800}
.tb select{height:44px;font-size:16px}
.top,.stats,.note{padding-inline:14px;margin:0}.top{padding-top:6px}h1{font-size:20px}.stats{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
.tablewrap{overflow:visible}table,tbody{display:block;min-width:0;width:100%}thead{display:none}
tbody tr{position:relative;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;padding:14px;margin-bottom:10px;border-radius:18px;background:var(--surface);border:1px solid var(--b1);box-shadow:0 1px 2px var(--s4)}
tbody tr:hover td{background:none}
td{display:block;border:0;padding:0;white-space:normal;min-width:0;font-size:13px}td[data-l]::before{content:attr(data-l);display:block;color:var(--t2);font-size:11px;line-height:1.5}
td.st{position:absolute;top:12px;left:14px}td.sta{grid-column:1/-1;order:-3;padding-left:70px;font-size:12.5px;font-weight:700}td.sta::before{display:none!important}td.sta .wk{display:inline;margin-right:6px;color:var(--t2);font-weight:400}
td.ti{grid-column:1/-1;order:-2;min-width:0;font-size:14px}td.pr{font-size:14px;font-weight:700}td.dd,td.wm{display:none}td.go{grid-column:1/-1}td.no{grid-column:1/-1;text-align:center;color:var(--t2)}
.b{width:100%;height:44px;font-size:13px;border-radius:12px}
#filters{position:fixed;right:0;left:0;bottom:0;z-index:2000;width:auto;max-height:92dvh;overflow-y:auto;padding:14px 16px calc(16px + env(safe-area-inset-bottom,0px));border-radius:24px 24px 0 0;border-width:1px 0 0;background:var(--surface);-webkit-backdrop-filter:none;backdrop-filter:none;transform:translateY(100%);visibility:hidden;transition:transform .25s cubic-bezier(.2,.8,.2,1),visibility .25s}
#filters.open{transform:none;visibility:visible}#filters>*{flex:none}
#bd{position:fixed;inset:0;z-index:1999;background:var(--overlay)}#bd.open{display:block}
.fhead strong{font-size:16px;font-weight:800}.clr{height:44px;font-size:12.5px}
.f>label,.f>span{font-size:12px}input[type=text],select{height:48px;font-size:16px}.seg{height:50px}.seg button{font-size:13px}.opts{gap:0}.opt{min-height:50px;font-size:13.5px}
.fgo{position:sticky;bottom:0;display:flex;align-items:center;justify-content:center;height:48px;margin-top:4px;border:0;border-radius:12px;background:var(--inverse);color:var(--on-inverse);font-size:13px;font-weight:500;box-shadow:0 6px 14px -3px var(--s18),0 1px 2px var(--s12),inset 0 1px 0 var(--hl-d);cursor:pointer}
}
</style></head>
<body>
<div id="amb" aria-hidden="true"><i></i><i></i><i></i><i></i></div>
<div class="hdr"><nav class="cap" aria-label="بخش‌ها"><span class="brand"><i></i>نزدیک مترو</span><span class="sep"></span><a href="#mapsec">نقشه</a><a href="#list">فهرست آگهی‌ها</a></nav></div>
<main>
<header class="top"><h1 id="h1">آپارتمان‌های اجاره‌ای نزدیک ایستگاه‌های مترو تهران</h1>
<div class="sub" id="sub"></div></header>
<div class="stats" id="stats"></div>
<div class="stcounts" id="stc"></div>
<section id="mapsec" aria-label="نقشه و فیلترها">
<div id="map"></div>
<div class="legend"><span><i class="dot" style="background:var(--er)"></i>ایستگاه مترو</span><span><i class="dot" style="background:var(--ok)"></i>پین دقیق</span><span><i class="dot" style="background:var(--wa);opacity:.6"></i>پین تقریبی (دایره = شعاع عدم قطعیت)</span><span><i class="dot" style="background:var(--in)"></i>نیاز به تأیید</span></div>
<div class="msearch"><i aria-hidden="true"></i><input id="q2" type="text" aria-label="جستجو" placeholder="عنوان یا محله"><button type="button" class="fbtn" id="fb" aria-controls="filters" aria-expanded="false">فیلترها<span class="fc" id="fc2" hidden></span></button></div>
<div id="bd"></div>
<form id="filters" aria-label="فیلترها">
<div class="fhead"><strong>فیلترها</strong><span class="fc" id="fc" hidden></span><button type="button" class="clr" id="clr" hidden>پاک کردن</button></div>
<div class="f"><label for="q">جستجو</label><input id="q" type="text" placeholder="عنوان یا محله، مثلاً یوسف‌آباد"></div>
<div class="f"><label for="stn">ایستگاه مترو</label><select id="stn"><option value="">همه</option></select></div>
<div class="row2">
<div class="f"><label for="mc">ودیعه تا (میلیون)</label><input id="mc" type="text" inputmode="decimal"></div>
<div class="f"><label for="mr">اجاره تا (میلیون)</label><input id="mr" type="text" inputmode="decimal"></div>
<div class="f"><label for="amin">متراژ از</label><input id="amin" type="text" inputmode="numeric" placeholder="متر"></div>
<div class="f"><label for="amax">متراژ تا</label><input id="amax" type="text" inputmode="numeric" placeholder="متر"></div>
</div>
<div class="f"><span id="mdl">فاصله پیاده تا مترو (متر)</span>
<div class="seg" id="md" role="group" aria-labelledby="mdl"><button type="button" data-v="800" aria-pressed="false">۸۰۰</button><button type="button" data-v="1200" aria-pressed="false">۱۲۰۰</button><button type="button" data-v="1500" aria-pressed="true">۱۵۰۰</button><button type="button" data-v="99999" aria-pressed="false">همه</button></div></div>
<div class="opts">
<label class="opt"><input type="checkbox" id="sV" checked><span class="sw"></span><span class="nm"><i class="dot" style="background:var(--ok)"></i>تأیید شده<small>پین دقیق</small></span><b id="nV"></b></label>
<label class="opt"><input type="checkbox" id="sP" checked><span class="sw"></span><span class="nm"><i class="dot" style="background:var(--wa)"></i>موقت<small>پین تقریبی ±۵۰۰ متر</small></span><b id="nP"></b></label>
<label class="opt"><input type="checkbox" id="sN"><span class="sw"></span><span class="nm"><i class="dot" style="background:var(--in)"></i>نیاز به تأیید<small>موقعیت نامطمئن</small></span><b id="nN"></b></label>
<label class="opt"><input type="checkbox" id="sS"><span class="sw"></span><span class="nm">مجیدیه<small>منطقه تکمیلی</small></span></label>
<label class="opt"><input type="checkbox" id="sHas" checked><span class="sw"></span><span class="nm">فقط ایستگاه‌های دارای آگهی<small>مرتب بر اساس تعداد</small></span></label>
</div>
<button type="button" class="fgo" id="fgo"></button>
</form>
</section>
<section class="tbl gc" id="list"><div class="tb"><b id="foot"></b><label>مرتب‌سازی <select id="so"><option value="d">فاصله تا مترو</option><option value="r">اجاره</option><option value="c">ودیعه</option><option value="a">متراژ</option></select></label></div>
<div class="tablewrap"><table><thead><tr>
<th data-k="s">وضعیت</th><th data-k="stfa">ایستگاه</th><th data-k="ti">عنوان</th><th data-k="nb">محله</th><th data-k="c">ودیعه</th><th data-k="r">اجاره</th><th data-k="a">متراژ</th><th data-k="rm">اتاق</th><th data-k="y">ساخت</th><th data-k="d">فاصله (متر)</th><th data-k="wm">دقیقه پیاده</th><th>لینک</th>
</tr></thead><tbody id="tb"></tbody></table></div></section>
<p class="note">فاصله‌های دارای «~ (تخمینی)» برابر فاصله مستقیم × ۱٫۳۲ است (میانه نسبت مسیر واقعی به خط مستقیم در تهران). پس از اجرای routing_check.py فاصله پیاده واقعی (OSRM، پروفایل پیاده) تا نزدیک‌ترین ورودی جایگزین می‌شود. موقعیت آگهی پینی است که آگهی‌دهنده در دیوار انتخاب کرده و به‌طور مستقل تأیید نشده است.</p>
</main>
<script>
const D=__DATA__;
const $=s=>document.querySelector(s), fa=n=>n==null?'—':Number(n).toLocaleString('fa-IR'), mil=n=>n==null?'—':(n/1e6).toLocaleString('fa-IR',{maximumFractionDigits:1})+' م';
const faYear=y=>Number(y).toLocaleString('fa-IR',{useGrouping:false});
// listing text comes from Divar advertisers, so it is escaped before going into innerHTML
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const css=v=>getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const col={MATCH_VERIFIED:'--ok',MATCH_PROVISIONAL_DISTANCE:'--wa',NEEDS_LOCATION_VERIFICATION:'--in'};
const lab={MATCH_VERIFIED:'تأیید شده',MATCH_PROVISIONAL_DISTANCE:'موقت',NEEDS_LOCATION_VERIFICATION:'تأیید موقعیت'};
const lineLab=s=>s.lines?'خط '+s.lines.split(',').map(fa).join('،'):'';
$('#h1').textContent=`آپارتمان‌های اجاره‌ای نزدیک ${fa(D.stations.filter(s=>s.kind==='metro_station').length)} ایستگاه مترو تهران`;
$('#sub').textContent=`ودیعه از ${fa(D.budget[2])} · سقف ودیعه ${fa(D.budget[0])} تومان · سقف اجاره ${fa(D.budget[1])} تومان · زمان جمع‌آوری داده: ${D.collected} · ${fa(D.inspected)} آگهی بررسی شد`;
$('#mc').placeholder=fa(D.budget[0]/1e6);$('#mr').placeholder=fa(D.budget[1]/1e6);
const metro=D.stations.filter(s=>s.kind==='metro_station');
// matches (verified + provisional, excluding Majidiyeh) per station; fixed for the dataset
const cnt={};D.listings.filter(l=>l.s!=='NEEDS_LOCATION_VERIFICATION'&&!l.supp).forEach(l=>cnt[l.st]=(cnt[l.st]||0)+1);
const shownStations=()=>$('#sHas').checked?metro.filter(s=>cnt[s.k]).sort((a,b)=>cnt[b.k]-cnt[a.k]):metro;
const map=L.map('map',{attributionControl:false}).setView([35.700,51.410],13);
// the filter card covers the map's right side, so credits go bottom-left
L.control.attribution({position:'bottomleft'}).addTo(map);
// Hosted (https): OSM tiles, Persian labels. file:// sends no Referer and OSM/CARTO answer 403, so use keyless Esri there ({y}/{x} order).
if(location.protocol==='file:')L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',{maxZoom:19,attribution:'Tiles © Esri — Esri, HERE, Garmin, © OpenStreetMap contributors'}).addTo(map);
else L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap contributors'}).addTo(map);
const stLayer=L.layerGroup().addTo(map);let stKey=null;
function drawStations(){const list=shownStations(),key=list.map(s=>s.k).join();if(key===stKey)return;stKey=key;
 const v=$('#stn').value;$('#stn').innerHTML='<option value="">همه</option>'+list.map(s=>`<option value="${s.k}">${s.fa}${s.lines?` (${lineLab(s)})`:''}${cnt[s.k]?' – '+fa(cnt[s.k]):''}</option>`).join('');
 if(list.some(s=>s.k===v))$('#stn').value=v;
 stLayer.clearLayers();list.forEach(s=>{
  L.circleMarker([s.lat,s.lon],{radius:8,color:css('--er'),weight:3,fillColor:'#fff',fillOpacity:1}).bindTooltip(`${s.fa} · ${s.en}${s.lines?' · '+lineLab(s):''} · ${fa(cnt[s.k]||0)} آگهی`).addTo(stLayer);
  s.ents.forEach(e=>L.circleMarker([e.lat,e.lon],{radius:3,color:css('--er'),weight:1,fillOpacity:.8}).bindTooltip('ورودی '+s.fa+(e.name?' – '+esc(e.name):'')).addTo(stLayer));});}
const layer=L.layerGroup().addTo(map);let sortK='d',sortDir=1,stSel='',maxDist=1500;
const dist=l=>l.w??l.e;
// type=number drops Persian digits, which is what a Persian keyboard types
const num=id=>+$(id).value.replace(/[۰-۹]/g,d=>'۰۱۲۳۴۵۶۷۸۹'.indexOf(d)).replace(/[٠-٩]/g,d=>'٠١٢٣٤٥٦٧٨٩'.indexOf(d)).replace('٫','.');
function filt(){const q=$('#q').value.trim(),st=$('#stn').value||stSel,mc=num('#mc')*1e6||Infinity,mr=num('#mr')*1e6||Infinity,md=maxDist,amin=num('#amin')||0,amax=num('#amax')||Infinity;
 const ok={MATCH_VERIFIED:$('#sV').checked,MATCH_PROVISIONAL_DISTANCE:$('#sP').checked,NEEDS_LOCATION_VERIFICATION:$('#sN').checked};
 return D.listings.filter(l=>ok[l.s]&&(!l.supp||$('#sS').checked)&&(!q||(l.ti+' '+l.nb).includes(q))&&(!st||l.st===st)&&(l.c??0)<=mc&&(l.r??0)<=mr&&(l.s==='NEEDS_LOCATION_VERIFICATION'||(dist(l)??1e9)<=md)&&(l.a==null||(l.a>=amin&&l.a<=amax)));}
function render(){drawStations();const L2=filt();layer.clearLayers();
 L2.forEach(l=>{if(l.lat==null)return;const c=css(col[l.s]);const pop=`<b>${esc(l.ti)}</b><br>ودیعه ${mil(l.c)} · اجاره ${mil(l.r)}<br>${l.a?fa(l.a)+' متر · ':''}${esc(l.stfa)} ${l.w!=null?fa(l.w)+' متر پیاده':l.e!=null?'~'+fa(l.e)+' متر پیاده (تخمینی)':''}<br><a href="${esc(l.u)}" target="_blank" rel="noopener">مشاهده در دیوار</a>`;
  if(l.lt==='FUZZY'&&l.rad)L.circle([l.lat,l.lon],{radius:l.rad,color:c,weight:1,dashArray:'4 4',fillOpacity:.05}).addTo(layer);
  L.circleMarker([l.lat,l.lon],{radius:l.lt==='FUZZY'?5:7,color:c,fillColor:c,fillOpacity:l.lt==='FUZZY'?.45:.9,weight:l.lt==='FUZZY'?1:2}).bindPopup(pop).addTo(layer);});
 const rows=[...L2].sort((a,b)=>{const va=sortK==='d'?dist(a):a[sortK],vb=sortK==='d'?dist(b):b[sortK];return((va??1e12)>(vb??1e12)?1:(va??1e12)<(vb??1e12)?-1:0)*sortDir});
 $('#tb').innerHTML=rows.map(l=>`<tr><td class="st"><span class="tag ${l.s}">${lab[l.s]}</span></td><td class="sta">${esc(l.stfa)||'—'}<span class="wk">${l.w!=null?fa(l.w)+' متر پیاده':l.e!=null?'~'+fa(l.e)+' متر پیاده':''}</span></td><td class="ti">${esc(l.ti)}</td><td class="nb" data-l="محله">${esc(l.nb)||'—'}</td><td class="num pr" data-l="ودیعه">${mil(l.c)}</td><td class="num pr" data-l="اجاره">${mil(l.r)}</td><td class="num" data-l="متراژ">${fa(l.a)}</td><td class="num" data-l="اتاق">${fa(l.rm)}</td><td class="num" data-l="ساخت">${l.y?faYear(l.y):'—'}</td><td class="num dd" data-l="فاصله (متر)">${l.w!=null?fa(l.w):l.e!=null?'~'+fa(l.e)+' (تخمینی)':'—'}</td><td class="num wm" data-l="دقیقه پیاده">${l.wm!=null?fa(l.wm):l.em!=null?'~'+fa(l.em):'—'}</td><td class="go"><a class="b" href="${esc(l.u)}" target="_blank" rel="noopener">مشاهده در دیوار ↗</a></td></tr>`).join('')||'<tr><td class="no" colspan="12">موردی با این فیلترها یافت نشد.</td></tr>';
 $('#stc').innerHTML=shownStations().map(s=>`<button type="button" data-k="${s.k}" class="chp ${stSel===s.k?'on':''}" aria-pressed="${stSel===s.k}">${s.fa}${s.lines?`<small>${lineLab(s)}</small>`:''}<b>${fa(cnt[s.k]||0)}</b></button>`).join('');
 document.querySelectorAll('th[data-k]').forEach(t=>{if(t.dataset.k===sortK)t.dataset.a=sortDir>0?'↑':'↓';else delete t.dataset.a;});
 $('#foot').textContent=`${fa(rows.length)} آگهی`;$('#fgo').textContent=`نمایش ${fa(rows.length)} آگهی`;
 const act=['#q','#stn','#mc','#mr','#amin','#amax'].filter(i=>$(i).value.trim()).length+(stSel?1:0)+(maxDist!==1500?1:0)+(!$('#sV').checked)+(!$('#sP').checked)+$('#sN').checked+$('#sS').checked;
 $('#fc').hidden=$('#fc2').hidden=$('#clr').hidden=!act;$('#fc').textContent=$('#fc2').textContent=fa(act);}
const c=D.counts,sv=k=>c[k]||0;
$('#stats').innerHTML=[['آگهی بررسی‌شده',D.inspected],['تأیید شده',sv('MATCH_VERIFIED')],['موقت (پین تقریبی)',sv('MATCH_PROVISIONAL_DISTANCE')],['نیاز به تأیید موقعیت',sv('NEEDS_LOCATION_VERIFICATION')]].map(([a,b])=>`<div class="stat gc"><b>${fa(b)}</b><span>${a}</span></div>`).join('');
$('#nV').textContent=fa(sv('MATCH_VERIFIED'));$('#nP').textContent=fa(sv('MATCH_PROVISIONAL_DISTANCE'));$('#nN').textContent=fa(sv('NEEDS_LOCATION_VERIFICATION'));
$('#clr').addEventListener('click',e=>{e.preventDefault();['#q','#q2','#stn','#mc','#mr','#amin','#amax'].forEach(i=>$(i).value='');stSel='';$('#sV').checked=$('#sP').checked=true;$('#sN').checked=$('#sS').checked=false;$('#md button[data-v="1500"]').click();});
// phone bottom sheet; on desktop the card is always visible and these do nothing visible
function sheet(open){$('#filters').classList.toggle('open',open);$('#bd').classList.toggle('open',open);$('#fb').setAttribute('aria-expanded',open);document.body.style.overflow=open?'hidden':'';if(!open&&document.activeElement&&$('#filters').contains(document.activeElement))$('#fb').focus();}
$('#fb').addEventListener('click',()=>{sheet(true);$('#fgo').focus();});$('#fgo').addEventListener('click',()=>sheet(false));$('#bd').addEventListener('click',()=>sheet(false));
document.addEventListener('keydown',e=>{if(e.key==='Escape')sheet(false);});
$('#filters').addEventListener('submit',e=>e.preventDefault());
$('#q2').addEventListener('input',e=>{$('#q').value=e.target.value;});$('#q').addEventListener('input',e=>{$('#q2').value=e.target.value;});
$('#so').addEventListener('input',e=>{sortK=e.target.value;sortDir=1;});
document.querySelectorAll('input,select').forEach(e=>e.addEventListener('input',render));
$('#stc').addEventListener('click',e=>{const k=e.target.closest('button')?.dataset.k;if(!k)return;stSel=stSel===k?'':k;render();});
$('#md').addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;maxDist=+b.dataset.v;$('#md').querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',x===b));render();});
document.querySelectorAll('th[data-k]').forEach(th=>th.addEventListener('click',()=>{const k=th.dataset.k;sortDir=sortK===k?-sortDir:1;sortK=k;$('#so').value=k;render();}));
render();
</script></body></html>"""


# ---------------------------------------------------------------- data quality
def write_quality(df, log_rows, meta):
    lg = pd.DataFrame(log_rows)
    n = len(df)
    miss = {c: int(df[c].isna().sum()) for c in ["credit", "rent", "area_m2", "rooms", "year_built", "floor", "latitude", "published", "description"]}
    L = ["# Data quality report", "", f"Run {meta['started_utc']} → {meta['finished_utc']} (UTC). {n} unique listings inspected.", "",
         "## Search coverage", "",
         f"- Districts searched: {len(lg)}; pagination complete: {int(lg.pagination_complete.sum())}; incomplete/error: {int((~lg.pagination_complete).sum())}",
         f"- Stop reasons: {lg.stop_reason.value_counts().to_dict()}",
         f"- Out-of-filter 'similar' listings skipped after Divar's `آگهی‌های مشابه` boundary: {int(lg.similar_results_skipped.sum())}",
         f"- Raw candidate rows (before cross-district dedup): {int(lg.candidates.sum())}; unique tokens: {n}", "",
         "## Detail retrieval", "", md_table(df.fetch_status.value_counts().rename_axis("fetch_status").reset_index()), "",
         "## Missing fields (of all inspected)", "", md_table(pd.DataFrame([{"field": k, "missing": v, "pct": f"{100*v/max(n,1):.1f}%"} for k, v in miss.items()])), "",
         "## Coordinates", "", md_table(df.groupby(["location_type", "coord_status"], dropna=False).size().rename("listings").reset_index()), "",
         "- `EXACT_DATA_UNTYPED`: the live API returned `location.exact_data.point` **without** a `type` field (the user-supplied copy of the fixture showed `type: EXACT`; the live fetch on the run date did not). Treated as Divar's exact pin.",
         "- `FUZZY`: Divar deliberately blurs the point (`fuzzy_data.radius`, observed 500 m). Distances from fuzzy points can be off by up to the radius, so such listings are never `MATCH_VERIFIED`.",
         "- Even exact pins are seller-chosen; no property-level address verification was possible.", "",
         f"- Swapped lat/lon suspects: {int((df.coord_status == 'SWAPPED_SUSPECT').sum())} (flagged, never auto-corrected)",
         f"- Walking route unavailable (fell back to straight line): {int((df.latitude.notna() & df.nearest_walk_m.isna()).sum())}", "",
         "## Price cross-checks", "",
         f"- webengage vs visible text vs search card conflicts: {int(df.price_conflict.notna().sum())}"]
    pc = df[df.price_conflict.notna()][["token", "url", "price_conflict"]]
    if len(pc):
        L += ["", md_table(pc.head(50))]
    L += ["", "## Duplicates / reposts", "",
          f"- Token-level duplicates across district searches merged: {int(lg.candidates.sum()) - n}",
          f"- Content-level possible reposts flagged: {int(df.possible_repost_of.notna().sum())}; marked DUPLICATE (near-identical): {int((df.status == 'DUPLICATE').sum())}"]
    rp = df[df.possible_repost_of.notna()][["token", "possible_repost_of", "status", "repost_evidence"]]
    if len(rp):
        L += ["", md_table(rp)]
    L += ["", "## Category noise", "",
          f"- Room-share / seeker ads filed under apartment-rent and rejected as WRONG_CATEGORY: {int(df.reason.str.contains('room-share', na=False).sum())}",
          f"- Negotiable-price ads (توافقی), kept out of strict matches (sheet `negotiable_not_strict`): {int(df.reason.str.contains('negotiable', na=False).sum())}", "",
          "## Errors", ""]
    er = lg[lg.error.notna()][["divar_district_id", "neighborhood_fa", "stop_reason", "error"]]
    L.append(md_table(er) if len(er) else "No search errors.")
    (OUTPUTS / "data_quality_report.md").write_text("\n".join(L), encoding="utf-8")


# ---------------------------------------------------------------- final report
def write_final(st, nb, log_rows, df, meta):
    lg = pd.DataFrame(log_rows)
    metro = st[st.kind == "metro_station"]
    vc = df.status.value_counts()
    v = lambda k: int(vc.get(k, 0))
    main_df = df[~df.supplementary_area.fillna(False).astype(bool)]
    m = main_df[main_df.status.isin(MATCH)].copy()
    m["dist"] = m.nearest_walk_m.fillna(m.est_walk_m)
    budget_ok = df[(df.credit <= MAX_CREDIT_TOMAN) & (df.rent <= MAX_RENT_TOMAN)]
    cv = (OUTPUTS / "currency_filter_verification.md").read_text()
    raw = json.loads((CACHE / "currency_verification_raw.json").read_text())
    e = list(raw["districts"].values())[0]["exps"]
    pv = json.loads((CACHE / "divar_probe" / "page_validation.json").read_text())
    names = dict(zip(metro.station_key, metro.station_en))
    L = []
    A = L.append
    A("# Tehran Metro Apartment Rental Discovery — Final Report\n")
    A(f"Data collected {meta['started_utc'][:16]} → {meta['finished_utc'][:16]} UTC from divar.ir (city: Tehran, category: apartment-rent).\n")

    A("## 1. Executive summary\n")
    A(f"- **{len(df)}** unique listings inspected from **{len(lg)}** Divar districts around {len(metro)} metro stations in Tehran city (+ Majidiyeh).")
    A(f"- **{v('MATCH_VERIFIED')}** verified matches (exact Divar pin, ≤ {SECONDARY_M} m *routed* walk to a station entrance, within budget). Verified status requires `routing_check.py`; "
      f"{'routing has been run' if meta.get('routing_check') else '**routing has NOT been run yet, so all distances are estimates**'}.")
    A(f"- **{v('MATCH_PROVISIONAL_DISTANCE')}** provisional matches (within budget and ≤ {SECONDARY_M} m walk, but the walk is an estimate — straight line × {DETOUR_FACTOR} — or Divar only exposes a blurred ±500 m pin).")
    A(f"- **{v('NEEDS_LOCATION_VERIFICATION')}** affordable listings need location confirmation (no pin, or the pin is far but the ad text names a target metro station).")
    A(f"- **{v('WRONG_CATEGORY')}** room-share / seeker ads that Divar files under apartment-rent were removed; **{v('TOO_FAR_FROM_METRO')}** were too far.")
    A(f"- Divar filters were verified to be **toman**, independent and inclusive; budget used: deposit ≤ {MAX_CREDIT_TOMAN:,}, rent ≤ {MAX_RENT_TOMAN:,} toman.\n")

    A("## 2. Exact budget and search constraints\n")
    A(f"- Deposit (ودیعه) between **{MIN_CREDIT_TOMAN:,}** (user rule: lower deposits are treated as scams) and **{MAX_CREDIT_TOMAN:,} toman**; monthly rent ≤ **{MAX_RENT_TOMAN:,} toman** — independent maxima, inclusive. "
      "The rent cap was lowered from 20,000,000 to 17,000,000 by the user during the run; every search and classification used 17,000,000.")
    A("- No deposit↔rent conversion. Convertible ads are judged on their advertised figures (`convertible` column).")
    A(f"- Walking classes: Excellent ≤ {EXCELLENT_M} m, Acceptable ≤ {ACCEPTABLE_M} m, Secondary ≤ {SECONDARY_M} m, otherwise excluded.")
    A(f"- Stations: every OSM subway station inside Divar's Tehran districts ({len(metro)}; suburban ends such as Karaj/Parand/Kahrizak excluded). "
      f"{int(metro.far_south.sum())} far-south stations (lat < 35.63) are included and flagged `far_south` in metro_stations.csv.")
    A(f"- Districts searched: every Divar district whose centroid or bbox lies within {DISTRICT_SEARCH_RADIUS_M} m of a target station (1,200 m of Majidiyeh centre). No far-south districts (e.g. Azadegan) are in range.")
    A("- Added on user request: when the pin is far or missing, the title + description are scanned for `مترو …`/`ایستگاه …`; a named target station (or an unnamed metro mention within 3 km) moves the ad to *needs location verification* instead of rejection.\n")

    A("## 3. Verified Divar currency units\n")
    A("| Layer | Unit |\n|---|---|\n| UI filter | toman (`ودیعه (تومان)`) |\n| Search API `credit`/`rent` | toman |\n| Card text | toman |\n| Detail `webengage` | toman |\n")
    A(f"Key evidence (Moniriyeh, district 278): no filter → {len(e['A_no_price_filter']['rows'])} ads; toman filter → {len(e['B_toman_both']['rows'])} ads, all compliant and equal to the locally-filtered subset of the unfiltered set; "
      f"rial-scaled filter (×10) → {len(e['C_rial_scaled_both']['rows'])} ads, most with deposits far over budget. Exactly-500M deposits are included by a 500,000,000 cap and excluded by 499,999,999. Full detail: `currency_filter_verification.md`.\n")

    A("## 4. Search API behaviour and limitations\n")
    A("- `POST https://api.divar.ir/v8/postlist/w/search` with `search_data.form_data.data` = `category`, `credit`, `rent` (`number_range.maximum`), `districts` (`repeated_string`), optional `bbox` (`repeated_float`, [minLon,minLat,maxLon,maxLat]). Confirmed from a live browser capture.")
    A("- Pagination: resend the previous response's `pagination.data` as `pagination_data` until `has_next_page` is false.")
    A("- **After the true results Divar appends `آگهی‌های مشابه` (similar listings) that ignore the filters.** `disable_recommendation: true` is ignored. The client stops at that boundary; these rows were never counted.")
    A("- `GET https://api.divar.ir/v8/posts-v2/web/{token}` for details; `GET https://api.divar.ir/v8/places/cities/1/districts` for district ids, centroids, bboxes and street tags.")
    A(f"- Requests were spaced ≥ 1.2 s; no authentication, CAPTCHA or access control was encountered or bypassed. Access-blocked detail fetches: {v('ACCESS_BLOCKED')}.\n")

    A("## 5–6. Target stations, verified coordinates and sources\n")
    A(md_table(st[["station_fa", "station_en", "lines", "lat", "lon", "entrance_count", "osm_vs_wikidata_m", "confidence", "source_url"]].rename(
        columns={"osm_vs_wikidata_m": "OSM↔Wikidata (m)"})))
    A(f"\nPrimary source: OpenStreetMap (Overpass API, pinned element ids). Cross-check: Wikidata P625 via each OSM element's `wikidata` tag; {int((metro.osm_vs_wikidata_m <= 250).sum())}/{len(metro)} agree within 250 m; larger gaps are marked low confidence. "
      "Lines from OSM `route=subway` relations' stop positions within 400 m. Entrances: OSM `railway=subway_entrance` within 350 m whose nearest station is this one; walking distances target the nearest entrance (station centre where OSM maps none). "
      "Majidiyeh is a neighbourhood, not a metro station (OSM place node 6172365019).\n")

    A("## 7. Neighbourhood inventory per station\n")
    for s in st.itertuples():
        sub = nb[nb.station_key == s.station_key].sort_values("centroid_distance_m")
        A(f"**{s.station_fa} — {s.station_en}** ({len(sub)} districts): " + "، ".join(
            f"{r.neighborhood_fa} ({r.centroid_distance_m} m{', P'+str(r.search_priority)})" for r in sub.itertuples()))
        A("")
    A("Full table with aliases, OSM sub-neighbourhoods and street tags: `station_neighborhoods.csv`.\n")

    A("## 8. Search coverage and methodology\n")
    A(f"- {len(lg)} district searches, {int(lg.pages_fetched.sum())} result pages, pagination complete for {int(lg.pagination_complete.sum())}/{len(lg)}.")
    A(f"- Stop reasons: {lg.stop_reason.value_counts().to_dict()}.")
    A(f"- Each unique token → detail fetch → prices re-verified (webengage vs visible text vs search card) → MAP_ROW coordinates → Haversine to all {len(metro)} stations → estimated walk = straight line × {DETOUR_FACTOR} → classification.")
    A(f"- The factor {DETOUR_FACTOR} is the median OSRM-foot/straight-line ratio measured on 1,491 real listing→entrance routes during this run (p25 1.22, p75 1.41, p90 1.50).")
    A("- `routing_check.py` (separate step) replaces estimates with batched OSRM foot-profile routes (routing.openstreetmap.de) to the entrances of stations within 2.5 km, for every affordable apartment, then reclassifies and regenerates all outputs. "
      + (f"Run: {meta['routing_check']}." if meta.get('routing_check') else "Not run yet."))
    A(f"- End-to-end pilot on Moniriyeh before scaling; listing `{pv['token']}` checked against its live page: {pv['result']}.\n")

    A("## 9–15. Counts\n")
    A(f"| Metric | Count |\n|---|---|\n| 9. Listings discovered (raw rows across districts) | {int(lg.candidates.sum())} |\n| 10. Unique listings inspected | {len(df)} |\n"
      f"| 11. Budget-compliant (detail-verified prices) | {len(budget_ok)} |\n| 12. Geographically verified matches | {v('MATCH_VERIFIED')} |\n| 13. Provisional matches | {v('MATCH_PROVISIONAL_DISTANCE')} |\n"
      f"| 14. Need location verification | {v('NEEDS_LOCATION_VERIFICATION')} |\n")
    A("\n**15. By status / rejection reason**\n")
    A(md_table(pd.DataFrame([{"status": k, "listings": v(k)} for k in STATUSES])))
    A("")

    A("## 16. Results by metro station\n")
    rows = []
    for k in metro.itertuples():
        mk = m[(m.nearest_walk_station == k.station_key) | (m.nearest_walk_station.isna() & (m.nearest_sl_station == k.station_key))]
        nbs = nb[nb.station_key == k.station_key]
        searched = lg[lg.divar_district_id.isin(nbs.divar_district_id)]
        rows.append({"station": f"{k.station_fa} / {k.station_en}", "districts searched": len(searched),
                     "candidates in those districts": int(searched.candidates.sum()),
                     "verified": int((mk.status == "MATCH_VERIFIED").sum()), "provisional": int((mk.status == "MATCH_PROVISIONAL_DISTANCE").sum()),
                     "excellent ≤800": int((mk.dist <= EXCELLENT_M).sum()), "median rent": fmt(mk.rent.median()) if len(mk) else "—"})
    A(md_table(pd.DataFrame(rows)))
    A("\nA station with 0 matches above still had every listed district fully searched; the zero is a result of that search, not missing coverage, unless the search log shows an error for that district.\n")

    A("## 17. Best matching apartments (direct links)\n")
    top = m.sort_values(["status", "dist", "rent"], ascending=[False, True, True]).head(40)
    top = top.assign(station=top.nearest_walk_station.fillna(top.nearest_sl_station).map(names),
                     deposit=top.credit.map(fmt), monthly=top.rent.map(fmt),
                     distance=[f"{fmt(w)} walk (routed)" if not pd.isna(w) else f"~{fmt(e)} est. ({fmt(s)} straight)" for w, e, s in zip(top.nearest_walk_m, top.est_walk_m, top.nearest_sl_m)],
                     pin=top.location_type)
    A(md_table(top[["status", "title", "neighborhood_fa", "deposit", "monthly", "area_m2", "rooms", "station", "distance", "pin", "url"]]))
    A("\nFull ranked list: `matching_apartments.xlsx` (sheet per station).\n")

    A("## 18. Comparison: deposit, rent, size, distance (matches)\n")
    if len(m):
        A(md_table(m.groupby("status").agg(listings=("token", "size"), median_deposit=("credit", "median"), median_rent=("rent", "median"),
                                            median_area=("area_m2", "median"), median_distance_m=("dist", "median")).round(0).reset_index()))
        bands = pd.cut(m.dist, [0, EXCELLENT_M, ACCEPTABLE_M, SECONDARY_M], labels=["Excellent", "Acceptable", "Secondary"])
        A("")
        A(md_table(m.groupby(bands, observed=False).agg(listings=("token", "size"), median_rent=("rent", "median"), median_deposit=("credit", "median"), median_area=("area_m2", "median")).round(0).reset_index().rename(columns={"dist": "walk band"})))
    A("")

    A("## 19. Geographic accuracy limitations\n")
    A(f"- Location types: {df.location_type.value_counts(dropna=False).to_dict()}.")
    A("- FUZZY pins are blurred by Divar (radius 500 m); their walking distances can be wrong by that much → provisional only.")
    A("- Exact pins are chosen by advertisers; not an independently verified address. OSRM routes use OSM footpaths and add the off-network snap legs; crossings, underpasses and building access are not modelled.")
    A("- Walking times assume ~4.5 km/h (1.25 m/s, OSRM foot profile). Estimated walks (×1.32) can be off by roughly ±20% (p25–p90 of measured ratios: 1.22–1.50).\n")

    A("## 20. Divar access limitations\n")
    A("- Undocumented endpoints; schema confirmed on the run date only. No login: contact details (phone numbers) were not accessed and are not included.")
    A(f"- Search errors: {int(lg.error.notna().sum())}. Detail fetch failures: unavailable {v('UNAVAILABLE')}, blocked {v('ACCESS_BLOCKED')}, parse errors {v('PARSING_ERROR')}.\n")

    A("## 21. Data freshness and availability\n")
    A("- Snapshot of the collection window above. Divar ads typically disappear within days; a 200 response at collection time is the only availability evidence. `unavailable_after` is SEO metadata and was not treated as proof of activity.")
    A("- Re-run the pipeline (cached per token) before contacting advertisers.\n")

    A("## 22. Recommended neighbourhoods to prioritise\n")
    if len(m):
        g = m.groupby("neighborhood_fa").agg(matches=("token", "size"), verified=("status", lambda s: int((s == "MATCH_VERIFIED").sum())),
                                              median_rent=("rent", "median"), median_walk=("dist", "median")).sort_values(["verified", "matches"], ascending=False).head(15).round(0).reset_index()
        A(md_table(g))
    A("")

    A("## 23. Suggested next steps for contacting advertisers\n")
    A("1. Start with `MATCH_VERIFIED` rows in `matching_apartments.xlsx`; open the Divar link and use Divar's in-app contact (requires your own login).")
    A("2. For provisional (fuzzy-pin) rows, ask the advertiser for the exact street/alley and recheck walking distance.")
    A("3. For `needs_location_verification.xlsx`, ask which metro station the unit is closest to — the `metro_mention_snippets` column shows what the ad text claims.")
    A("4. Confirm the deposit/rent are not negotiable-only and whether the unit is still available; ads are often reposted (see `possible_repost_of`).")
    A("5. Watch for agency ads (`business_type`) that charge commission.\n")

    A("## 24. File manifest and re-run\n")
    A("| File | Contents |\n|---|---|\n| outputs/metro_stations.csv | stations, lines, coordinates, entrances, sources |\n| outputs/station_neighborhoods.csv | station→district inventory |\n"
      "| outputs/all_listings.csv | every inspected listing with status + reason |\n| outputs/matching_apartments.xlsx | ranked matches, sheet per station, Majidiyeh sheet |\n"
      "| outputs/needs_location_verification.xlsx | affordable, location unconfirmed |\n| outputs/rejected_listings.csv | rejected with reasons |\n| outputs/search_log.csv | per-district search coverage |\n"
      "| outputs/currency_filter_verification.md | toman/rial proof |\n| outputs/data_quality_report.md | missing fields, coords, duplicates, errors |\n| outputs/report.html | interactive RTL dashboard (needs internet for map tiles/Leaflet) |\n"
      "| cache/ | raw OSM, search page snapshots, post JSON, routing responses, browser evidence |\n")
    A("```bash\ncd tehran-metro-rentals\npython -m venv .venv && .venv/bin/pip install -r requirements.txt\n.venv/bin/python -m pytest -q tests\n.venv/bin/python src/main.py            # resumes from cache/; delete cache/checkpoint and cache/posts for a fresh snapshot\n```")
    (OUTPUTS / "FINAL_REPORT.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    import json as _j
    d = _j.loads((CACHE / "results.json").read_text())
    from exporter import export
    from main import reclassify
    reclassify(d["records"])
    (CACHE / "results.json").write_text(_j.dumps(d, ensure_ascii=False, default=str))
    print(pd.Series([r["status"] for r in d["records"]]).value_counts().to_string())
    st = pd.read_csv(OUTPUTS / "metro_stations.csv")
    nb = pd.read_csv(OUTPUTS / "station_neighborhoods.csv")
    export(st, nb, d["search_log"], d["records"], d["meta"])
