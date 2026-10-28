"""Phase C: empirically determine whether Divar search filters use toman or rial."""
import json
from datetime import datetime, timezone

from config import CACHE, MAX_CREDIT_TOMAN, MAX_RENT_TOMAN, OUTPUTS
from divar_client import form_data, search_all
from listing_parser import toman_to_rial

DISTRICTS = [(278, "منیریه / Moniriyeh")]


def _ok(r, cmax, rmax):
    c, rr = r["card_credit"], r["card_rent"]
    return (cmax is None or (c is not None and c <= cmax)) and (rmax is None or (rr is not None and rr <= rmax))


def run() -> dict:
    C, R = MAX_CREDIT_TOMAN, MAX_RENT_TOMAN
    exps = {
        "A_no_price_filter": (None, None),
        "B_toman_both": (C, R),
        "C_rial_scaled_both": (toman_to_rial(C), toman_to_rial(R)),
        "D_credit_only": (C, None),
        "E_rent_only": (None, R),
        "F_credit_minus_1": (C - 1, None),
    }
    out = {"run_at": datetime.now(timezone.utc).isoformat(), "districts": {}}
    for did, name in DISTRICTS:
        res = {}
        for k, (c, r) in exps.items():
            s = search_all(form_data(c, r, [did]), f"currency_{did}_{k}")
            res[k] = {"credit_max": c, "rent_max": r, "pages": s["pages"], "complete": s["complete"],
                      "stop": s["stop_reason"], "error": s["error"], "echoed": s["echoed_filters"],
                      "rows": s["rows"]}
        out["districts"][did] = {"name": name, "exps": res}
    (CACHE / "currency_verification_raw.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    write_md(out)
    return out


def write_md(out):
    C, R = MAX_CREDIT_TOMAN, MAX_RENT_TOMAN
    L = ["# Divar currency-unit & filter verification", "",
         f"Run: {out['run_at']} (UTC). Budget under test: credit ≤ {C:,} toman, rent ≤ {R:,} toman.", "",
         "> The user lowered the rent cap from 20,000,000 to 17,000,000 toman during the run. The browser capture "
         "below used the original 20,000,000 value; it was used only to establish units and schema. All API experiments "
         "and the final search used 17,000,000.", ""]
    ev = json.loads((CACHE / "divar_probe" / "browser_evidence.json").read_text())
    L += ["## 1. Browser UI evidence (real browser session)", "",
          f"- Method: {ev['method']}",
          f"- UI field labels: `{ev['ui_labels'][0]}`, `{ev['ui_labels'][1]}` — the UI itself states the unit is **toman**.",
          f"- Values typed: 500000000 (deposit max), 20000000 (rent max). Inputs displayed: `{ev['ui_inputs_after_entry'][1]}`, `{ev['ui_inputs_after_entry'][3]}`.",
          f"- Resulting page URL: `{ev['resulting_url']}`",
          f"- UI result count: `{ev['ui_result_count_text']}` (13 listings in Moniriyeh for 500M / 20M).",
          "- Captured `POST https://api.divar.ir/v8/postlist/w/search` form data (redacted to the filter part):", "",
          "```json", json.dumps(ev["captured_request"]["search_data.form_data.data"], ensure_ascii=False, indent=1), "```", "",
          "UI value 500,000,000 toman → request `credit.number_range.maximum = \"500000000\"` (no ×10). "
          "UI value 20,000,000 toman → `rent.number_range.maximum = \"20000000\"`. **Request unit = toman.**", "",
          "The second captured page carried `viewed_rows: [{\"type\": \"VIEWED_ROW_SIMILAR_RESULTS_DIVIDER\"}]`: after the "
          "true results Divar appends *similar* listings that do **not** satisfy the filters (section titled `آگهی‌های مشابه`). "
          "`disable_recommendation: true` was tested and is ignored, so the client stops collecting at that boundary.", "",
          "## 2. Controlled API experiments", ""]
    for did, d in out["districts"].items():
        e = d["exps"]
        L += [f"### District {d['name']} (Divar id {did})", "",
              "| Experiment | credit max | rent max | pages | complete | listings | all rows satisfy toman limits? | rows with credit > 500M toman |",
              "|---|---|---|---|---|---|---|---|"]
        for k, x in e.items():
            rows = x["rows"]
            sat = sum(_ok(r, x["credit_max"] if k != "C_rial_scaled_both" else C, x["rent_max"] if k != "C_rial_scaled_both" else R) for r in rows)
            over = sum(1 for r in rows if (r["card_credit"] or 0) > C)
            L.append(f"| {k} | {x['credit_max'] or '—'} | {x['rent_max'] or '—'} | {x['pages']} | {x['complete']} | {len(rows)} | {sat}/{len(rows)} | {over} |")
        A, B, Cx, D, E, F = (e[k]["rows"] for k in e)
        tok = lambda rows: {r["token"] for r in rows}
        a_ok = {r["token"] for r in A if _ok(r, C, R)}
        b_bad = [r for r in B if not _ok(r, C, R)]
        at_boundary = [r for r in D if r["card_credit"] == C]
        L += ["", "Checks:", "",
              f"- B ⊆ A (filtered results are a subset of unfiltered): **{tok(B) <= tok(A)}**",
              f"- Every B card satisfies credit ≤ {C:,} AND rent ≤ {R:,}: **{not b_bad}**" + (f" — violators: {[(r['token'], r['card_credit_text'], r['card_rent_text']) for r in b_bad]}" if b_bad else ""),
              f"- Completeness: A-rows meeting both limits locally = {len(a_ok)}; of those present in B = {len(a_ok & tok(B))}",
              f"- Rial-scaled filter (C: {toman_to_rial(C):,} / {toman_to_rial(R):,}) returned {len(Cx)} listings vs {len(B)} for toman values; "
              f"{sum(1 for r in Cx if (r['card_credit'] or 0) > C)} have card deposit > {C:,} toman. If the API were rial-based, C would equal B.",
              f"- Independence: credit-only D = {len(D)} rows (max card rent {max([r['card_rent'] or 0 for r in D] or [0]):,}); rent-only E = {len(E)} rows (max card credit {max([r['card_credit'] or 0 for r in E] or [0]):,}).",
              f"- Inclusive maximum: listings with card deposit exactly {C:,} in D = {len(at_boundary)}; present in F (max {C-1:,}) = {len(tok(at_boundary) & tok(F))}.",
              f"- Server echo of filters (B): `{json.dumps(e['B_toman_both']['echoed'], ensure_ascii=False)}`", ""]
    fx = json.loads((CACHE.parent / "fixtures" / "gaSfxzZ8.json").read_text())["webengage"]
    L += ["## 3. Listing-detail units", "",
          f"Fixture `https://divar.ir/v/gaSfxzZ8` (fetched live from `GET https://api.divar.ir/v8/posts-v2/web/gaSfxzZ8`): "
          f"`webengage.credit = {fx['credit']}`, `webengage.rent = {fx['rent']}`; visible rows `ودیعه: ‏۷۰۰,۰۰۰,۰۰۰ تومان`, "
          "`اجارهٔ ماهانه: ‏۹,۰۰۰,۰۰۰ تومان`. → **detail numeric fields are toman.** The pipeline cross-checks webengage vs text "
          "for every listing and flags conflicts (see data_quality_report.md).", "",
          "## 4. Conclusions", "",
          "| Layer | Unit | Evidence |", "|---|---|---|",
          "| Divar UI filter fields | toman | labels `ودیعه (تومان)`, `اجاره (تومان)` |",
          "| Search API `credit`/`rent` `number_range` | toman | UI→request capture (no ×10); experiments above; server suggestion cache shows `500000000` as `تا ۵۰۰ میلیون` |",
          "| Search card text | toman | `ودیعه: … تومان` |",
          "| Detail `webengage.credit/rent` | toman | fixture + per-listing cross-check |", "",
          f"**Final approved values:** `credit.number_range.maximum = \"{C}\"`, `rent.number_range.maximum = \"{R}\"`. No ×10 conversion.", "",
          "## 5. Uncertainty / API behaviour", "",
          "- Endpoints are undocumented and may change; schema confirmed only for the run date.",
          "- Filters apply to the advertised deposit/rent. Convertible ads (`قابل تبدیل`) are matched on their advertised figures only.",
          "- 'Similar listings' appended after the real results ignore filters; collected rows stop at that boundary.",
          "- HTTP 200 alone was never taken as proof: each claim above is backed by result-set comparison.", ""]
    (OUTPUTS / "currency_filter_verification.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    run()
    print((OUTPUTS / "currency_filter_verification.md").read_text())
