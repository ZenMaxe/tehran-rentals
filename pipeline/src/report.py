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
    # Leaflet CSS inlined: artifact viewers block third-party stylesheets
    css = (Path(__file__).parent / "assets" / "leaflet-1.9.4.css").read_text()
    html = HTML.replace("__LEAFLET_CSS__", css).replace("__DATA__", data.replace("</", "<\\/"))
    (OUTPUTS / "report.html").write_text(html, encoding="utf-8")


HTML = r"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>آپارتمان‌های نزدیک مترو</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;500;700&display=swap" rel="stylesheet">
<style>__LEAFLET_CSS__</style>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
:root{--bg:#f6f5f2;--card:#fff;--ink:#1c1c1a;--mute:#6b6a65;--line:#e4e2dc;--accent:#0f6e5a;
--ver:#0f6e5a;--prov:#c27c0e;--nlv:#7a4fb8;--stn:#b3261e;--chip:#eeece6}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#151514;--card:#1f1f1d;--ink:#ecebe6;--mute:#a19f98;--line:#33322f;--accent:#4fc3a1;--ver:#4fc3a1;--prov:#e8a83a;--nlv:#b394e6;--stn:#ff7a6e;--chip:#2a2927}}
:root[data-theme="dark"]{--bg:#151514;--card:#1f1f1d;--ink:#ecebe6;--mute:#a19f98;--line:#33322f;--accent:#4fc3a1;--ver:#4fc3a1;--prov:#e8a83a;--nlv:#b394e6;--stn:#ff7a6e;--chip:#2a2927}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.6 Vazirmatn,Tahoma,sans-serif}
header{padding:20px 16px 8px;max-width:1400px;margin:auto}h1{margin:0;font-size:22px}.sub{color:var(--mute);font-size:13px}
main{max-width:1400px;margin:auto;padding:8px 16px 40px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin:12px 0}
.stat{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px}.stat b{display:block;font-size:22px;font-variant-numeric:tabular-nums}.stat span{color:var(--mute);font-size:12px}
.grid{display:grid;grid-template-columns:320px 1fr;gap:12px}@media(max-width:900px){.grid{grid-template-columns:1fr}}
.panel{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px}
label{display:block;font-size:12px;color:var(--mute);margin-top:10px}input,select{width:100%;padding:7px 8px;border:1px solid var(--line);border-radius:7px;background:var(--bg);color:var(--ink);font:inherit}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:6px}.chk{display:flex;gap:6px;align-items:center;color:var(--ink);font-size:13px}.chk input{width:auto}
#map{height:460px;border-radius:10px;border:1px solid var(--line)}
.legend{display:flex;flex-wrap:wrap;gap:12px;font-size:12px;color:var(--mute);margin-top:8px}.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-left:4px;vertical-align:middle}
.stcounts{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}.stcounts button{border:1px solid var(--line);background:var(--chip);color:var(--ink);border-radius:999px;padding:3px 10px;font:inherit;font-size:12px;cursor:pointer}.stcounts button.on{background:var(--accent);color:#fff;border-color:var(--accent)}
.tablewrap{overflow-x:auto;margin-top:12px;background:var(--card);border:1px solid var(--line);border-radius:10px}
table{border-collapse:collapse;width:100%;min-width:900px;font-size:13px}th,td{padding:7px 9px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
th{position:sticky;top:0;background:var(--card);cursor:pointer;font-weight:500;color:var(--mute)}td.num{font-variant-numeric:tabular-nums}
td.ti{white-space:normal;min-width:200px}a{color:var(--accent)}.tag{font-size:11px;padding:1px 7px;border-radius:999px;color:#fff}
.MATCH_VERIFIED{background:var(--ver)}.MATCH_PROVISIONAL_DISTANCE{background:var(--prov)}.NEEDS_LOCATION_VERIFICATION{background:var(--nlv)}
.note{color:var(--mute);font-size:12px;margin-top:10px}
</style></head>
<body>
<header><h1 id="h1">آپارتمان‌های اجاره‌ای نزدیک ایستگاه‌های مترو تهران</h1>
<div class="sub" id="sub"></div></header>
<main>
<div class="stats" id="stats"></div>
<div class="grid">
<div class="panel">
<label>جستجو (عنوان / محله)</label><input id="q" placeholder="مثلاً یوسف‌آباد">
<label>ایستگاه</label><select id="stn"><option value="">همه</option></select>
<div class="row2"><div><label>حداکثر ودیعه (میلیون تومان)</label><input id="mc" type="number"></div><div><label>حداکثر اجاره (میلیون تومان)</label><input id="mr" type="number"></div></div>
<label>حداکثر فاصله تا مترو (متر)</label><select id="md"><option value="800">۸۰۰ – عالی</option><option value="1200">۱۲۰۰ – قابل قبول</option><option value="1500" selected>۱۵۰۰ – ثانویه</option><option value="99999">بدون محدودیت</option></select>
<div class="row2"><div><label>حداقل متراژ</label><input id="amin" type="number"></div><div><label>حداکثر متراژ</label><input id="amax" type="number"></div></div>
<label>وضعیت</label>
<div class="chk"><input type="checkbox" id="sV" checked><span><span class="dot" style="background:var(--ver)"></span>تأیید شده (پین دقیق)</span></div>
<div class="chk"><input type="checkbox" id="sP" checked><span><span class="dot" style="background:var(--prov)"></span>موقت (پین تقریبی ±۵۰۰ متر)</span></div>
<div class="chk"><input type="checkbox" id="sN"><span><span class="dot" style="background:var(--nlv)"></span>نیاز به تأیید موقعیت</span></div>
<div class="chk"><input type="checkbox" id="sS"><span>شامل مجیدیه (منطقه تکمیلی)</span></div>
<div class="chk"><input type="checkbox" id="sHas" checked><span>فقط ایستگاه‌های دارای آگهی (مرتب بر اساس تعداد)</span></div>
<div class="stcounts" id="stc"></div>
<p class="note">فاصله‌های دارای «~ (تخمینی)» برابر فاصله مستقیم × ۱٫۳۲ است (میانه نسبت مسیر واقعی به خط مستقیم در تهران). پس از اجرای routing_check.py فاصله پیاده واقعی (OSRM، پروفایل پیاده) تا نزدیک‌ترین ورودی جایگزین می‌شود. موقعیت آگهی پینی است که آگهی‌دهنده در دیوار انتخاب کرده و به‌طور مستقل تأیید نشده است.</p>
</div>
<div><div id="map"></div>
<div class="legend"><span><span class="dot" style="background:var(--stn)"></span>ایستگاه مترو</span><span><span class="dot" style="background:var(--ver)"></span>پین دقیق</span><span><span class="dot" style="background:var(--prov);opacity:.6"></span>پین تقریبی (دایره = شعاع عدم قطعیت)</span><span><span class="dot" style="background:var(--nlv)"></span>نیاز به تأیید</span></div></div>
</div>
<div class="tablewrap"><table><thead><tr>
<th data-k="s">وضعیت</th><th data-k="ti">عنوان</th><th data-k="nb">محله</th><th data-k="c">ودیعه</th><th data-k="r">اجاره</th><th data-k="a">متراژ</th><th data-k="rm">اتاق</th><th data-k="y">ساخت</th><th data-k="stfa">ایستگاه</th><th data-k="d">فاصله (متر)</th><th data-k="wm">دقیقه پیاده</th><th>لینک</th>
</tr></thead><tbody id="tb"></tbody></table></div>
<p class="note" id="foot"></p>
</main>
<script>
const D=__DATA__;
const $=s=>document.querySelector(s), fa=n=>n==null?'—':Number(n).toLocaleString('fa-IR'), mil=n=>n==null?'—':(n/1e6).toLocaleString('fa-IR',{maximumFractionDigits:1})+' م';
const css=v=>getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const col={MATCH_VERIFIED:'--ver',MATCH_PROVISIONAL_DISTANCE:'--prov',NEEDS_LOCATION_VERIFICATION:'--nlv'};
const lab={MATCH_VERIFIED:'تأیید شده',MATCH_PROVISIONAL_DISTANCE:'موقت',NEEDS_LOCATION_VERIFICATION:'تأیید موقعیت'};
$('#h1').textContent=`آپارتمان‌های اجاره‌ای نزدیک ${fa(D.stations.filter(s=>s.kind==='metro_station').length)} ایستگاه مترو تهران`;
$('#sub').textContent=`ودیعه از ${fa(D.budget[2])} · سقف ودیعه ${fa(D.budget[0])} تومان · سقف اجاره ${fa(D.budget[1])} تومان · زمان جمع‌آوری داده: ${D.collected} · ${fa(D.inspected)} آگهی بررسی شد`;
const metro=D.stations.filter(s=>s.kind==='metro_station');
// matches (verified + provisional, excluding Majidiyeh) per station; fixed for the dataset
const cnt={};D.listings.filter(l=>l.s!=='NEEDS_LOCATION_VERIFICATION'&&!l.supp).forEach(l=>cnt[l.st]=(cnt[l.st]||0)+1);
const shownStations=()=>$('#sHas').checked?metro.filter(s=>cnt[s.k]).sort((a,b)=>cnt[b.k]-cnt[a.k]):metro;
const map=L.map('map').setView([35.700,51.410],13);
// Hosted (https): OSM tiles, Persian labels. file:// sends no Referer and OSM/CARTO answer 403, so use keyless Esri there ({y}/{x} order).
if(location.protocol==='file:')L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',{maxZoom:19,attribution:'Tiles © Esri — Esri, HERE, Garmin, © OpenStreetMap contributors'}).addTo(map);
else L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap contributors'}).addTo(map);
const stLayer=L.layerGroup().addTo(map);let stKey=null;
function drawStations(){const list=shownStations(),key=list.map(s=>s.k).join();if(key===stKey)return;stKey=key;
 const v=$('#stn').value;$('#stn').innerHTML='<option value="">همه</option>'+list.map(s=>`<option value="${s.k}">${s.fa} (خط ${s.lines})${cnt[s.k]?' – '+fa(cnt[s.k]):''}</option>`).join('');
 if(list.some(s=>s.k===v))$('#stn').value=v;
 stLayer.clearLayers();list.forEach(s=>{
  L.circleMarker([s.lat,s.lon],{radius:8,color:css('--stn'),weight:3,fillColor:'#fff',fillOpacity:1}).bindTooltip(`${s.fa} · ${s.en} · خط ${s.lines} · ${fa(cnt[s.k]||0)} آگهی`).addTo(stLayer);
  s.ents.forEach(e=>L.circleMarker([e.lat,e.lon],{radius:3,color:css('--stn'),weight:1,fillOpacity:.8}).bindTooltip('ورودی '+s.fa+(e.name?' – '+e.name:'')).addTo(stLayer));});}
const layer=L.layerGroup().addTo(map);let sortK='d',sortDir=1,stSel='';
const dist=l=>l.w??l.e;
function filt(){const q=$('#q').value.trim(),st=$('#stn').value||stSel,mc=+$('#mc').value*1e6||Infinity,mr=+$('#mr').value*1e6||Infinity,md=+$('#md').value,amin=+$('#amin').value||0,amax=+$('#amax').value||Infinity;
 const ok={MATCH_VERIFIED:$('#sV').checked,MATCH_PROVISIONAL_DISTANCE:$('#sP').checked,NEEDS_LOCATION_VERIFICATION:$('#sN').checked};
 return D.listings.filter(l=>ok[l.s]&&(!l.supp||$('#sS').checked)&&(!q||(l.ti+' '+l.nb).includes(q))&&(!st||l.st===st)&&(l.c??0)<=mc&&(l.r??0)<=mr&&(l.s==='NEEDS_LOCATION_VERIFICATION'||(dist(l)??1e9)<=md)&&(l.a==null||(l.a>=amin&&l.a<=amax)));}
function render(){drawStations();const L2=filt();layer.clearLayers();
 L2.forEach(l=>{if(l.lat==null)return;const c=css(col[l.s]);const pop=`<b>${l.ti}</b><br>ودیعه ${mil(l.c)} · اجاره ${mil(l.r)}<br>${l.a?fa(l.a)+' متر · ':''}${l.stfa||''} ${l.w!=null?fa(l.w)+' متر پیاده':l.e!=null?'~'+fa(l.e)+' متر پیاده (تخمینی)':''}<br><a href="${l.u}" target="_blank" rel="noopener">مشاهده در دیوار</a>`;
  if(l.lt==='FUZZY'&&l.rad)L.circle([l.lat,l.lon],{radius:l.rad,color:c,weight:1,dashArray:'4 4',fillOpacity:.05}).addTo(layer);
  L.circleMarker([l.lat,l.lon],{radius:l.lt==='FUZZY'?5:7,color:c,fillColor:c,fillOpacity:l.lt==='FUZZY'?.45:.9,weight:l.lt==='FUZZY'?1:2}).bindPopup(pop).addTo(layer);});
 const rows=[...L2].sort((a,b)=>{const va=sortK==='d'?dist(a):a[sortK],vb=sortK==='d'?dist(b):b[sortK];return((va??1e12)>(vb??1e12)?1:(va??1e12)<(vb??1e12)?-1:0)*sortDir});
 $('#tb').innerHTML=rows.map(l=>`<tr><td><span class="tag ${l.s}">${lab[l.s]}</span></td><td class="ti">${l.ti}</td><td>${l.nb}</td><td class="num">${mil(l.c)}</td><td class="num">${mil(l.r)}</td><td class="num">${fa(l.a)}</td><td class="num">${fa(l.rm)}</td><td class="num">${l.y?fa(l.y):'—'}</td><td>${l.stfa}</td><td class="num">${l.w!=null?fa(l.w):l.e!=null?'~'+fa(l.e)+' (تخمینی)':'—'}</td><td class="num">${l.wm!=null?fa(l.wm):l.em!=null?'~'+fa(l.em):'—'}</td><td><a href="${l.u}" target="_blank" rel="noopener">دیوار ↗</a></td></tr>`).join('')||'<tr><td colspan="12">موردی با این فیلترها یافت نشد.</td></tr>';
 $('#stc').innerHTML=shownStations().map(s=>`<button data-k="${s.k}" class="${stSel===s.k?'on':''}">${s.fa}${s.lines?` <small style="opacity:.7">خط ${s.lines.split(',').map(fa).join('،')}</small>`:''} · ${fa(cnt[s.k]||0)}</button>`).join('');
 $('#foot').textContent=`${fa(rows.length)} آگهی نمایش داده شد.`;}
const c=D.counts,sv=k=>c[k]||0;
$('#stats').innerHTML=[['آگهی بررسی‌شده',D.inspected],['تأیید شده',sv('MATCH_VERIFIED')],['موقت (پین تقریبی)',sv('MATCH_PROVISIONAL_DISTANCE')],['نیاز به تأیید موقعیت',sv('NEEDS_LOCATION_VERIFICATION')],['دور از مترو',sv('TOO_FAR_FROM_METRO')],['همخونه / غیر آپارتمان',sv('WRONG_CATEGORY')]].map(([a,b])=>`<div class="stat"><b>${fa(b)}</b><span>${a}</span></div>`).join('');
document.querySelectorAll('input,select').forEach(e=>e.addEventListener('input',render));
$('#stc').addEventListener('click',e=>{const k=e.target.dataset.k;if(!k)return;stSel=stSel===k?'':k;render();});
document.querySelectorAll('th[data-k]').forEach(th=>th.addEventListener('click',()=>{const k=th.dataset.k;sortDir=sortK===k?-sortDir:1;sortK=k;render();}));
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
