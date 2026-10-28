# Divar currency-unit & filter verification

Run: 2026-10-28T20:11:04.082003+00:00 (UTC). Budget under test: credit ≤ 500,000,000 toman, rent ≤ 17,000,000 toman.

> The user lowered the rent cap from 20,000,000 to 17,000,000 toman during the run. The browser capture below used the original 20,000,000 value; it was used only to establish units and schema. All API experiments and the final search used 17,000,000.

## 1. Browser UI evidence (real browser session)

- Method: Built-in browser: opened https://divar.ir/s/tehran/rent-apartment/moniriyeh, typed 500000000 into ودیعه(تومان) max and 20000000 into اجاره(تومان) max, pressed Enter; fetch/XHR hooked via JS to capture request bodies
- UI field labels: `ودیعه (تومان)`, `اجاره (تومان)` — the UI itself states the unit is **toman**.
- Values typed: 500000000 (deposit max), 20000000 (rent max). Inputs displayed: `۵۰۰٬۰۰۰٬۰۰۰`, `۲۰٬۰۰۰٬۰۰۰`.
- Resulting page URL: `https://divar.ir/s/tehran/rent-apartment/moniriyeh?credit=-500000000&map_bbox=51.392347%2C35.665967%2C51.410688%2C35.701762&map_place_hash=REDACTED&rent=-20000000`
- UI result count: `۱۳ آگهی در این محدوده` (13 listings in Moniriyeh for 500M / 20M).
- Captured `POST https://api.divar.ir/v8/postlist/w/search` form data (redacted to the filter part):

```json
{
 "category": {
  "str": {
   "value": "apartment-rent"
  }
 },
 "rent": {
  "number_range": {
   "maximum": "20000000",
   "value": {
    "maximum": "20000000"
   }
  }
 },
 "credit": {
  "number_range": {
   "maximum": "500000000",
   "value": {
    "maximum": "500000000"
   }
  }
 },
 "districts": {
  "repeated_string": {
   "value": [
    "278"
   ]
  }
 },
 "bbox": {
  "repeated_float": {
   "value": [
    {
     "value": 51.3923454
    },
    {
     "value": 35.665966
    },
    {
     "value": 51.4106865
    },
    {
     "value": 35.7017632
    }
   ]
  }
 }
}
```

UI value 500,000,000 toman → request `credit.number_range.maximum = "500000000"` (no ×10). UI value 20,000,000 toman → `rent.number_range.maximum = "20000000"`. **Request unit = toman.**

The second captured page carried `viewed_rows: [{"type": "VIEWED_ROW_SIMILAR_RESULTS_DIVIDER"}]`: after the true results Divar appends *similar* listings that do **not** satisfy the filters (section titled `آگهی‌های مشابه`). `disable_recommendation: true` was tested and is ignored, so the client stops collecting at that boundary.

## 2. Controlled API experiments

### District منیریه / Moniriyeh (Divar id 278)

| Experiment | credit max | rent max | pages | complete | listings | all rows satisfy toman limits? | rows with credit > 500M toman |
|---|---|---|---|---|---|---|---|
| A_no_price_filter | — | — | 7 | True | 133 | 133/133 | 101 |
| B_toman_both | 500000000 | 17000000 | 2 | True | 10 | 10/10 | 0 |
| C_rial_scaled_both | 5000000000 | 170000000 | 7 | True | 127 | 10/127 | 95 |
| D_credit_only | 500000000 | — | 3 | True | 32 | 32/32 | 0 |
| E_rent_only | — | 17000000 | 5 | True | 84 | 84/84 | 74 |
| F_credit_minus_1 | 499999999 | — | 2 | True | 20 | 20/20 | 0 |

Checks:

- B ⊆ A (filtered results are a subset of unfiltered): **True**
- Every B card satisfies credit ≤ 500,000,000 AND rent ≤ 17,000,000: **True**
- Completeness: A-rows meeting both limits locally = 10; of those present in B = 10
- Rial-scaled filter (C: 5,000,000,000 / 170,000,000) returned 127 listings vs 10 for toman values; 95 have card deposit > 500,000,000 toman. If the API were rial-based, C would equal B.
- Independence: credit-only D = 32 rows (max card rent 120,000,000); rent-only E = 84 rows (max card credit 8,000,000,000).
- Inclusive maximum: listings with card deposit exactly 500,000,000 in D = 12; present in F (max 499,999,999) = 0.
- Server echo of filters (B): `{"category": {"str": {"value": "apartment-rent"}}, "credit": {"number_range": {"maximum": "500000000", "value": {"maximum": "500000000"}}}, "rent": {"number_range": {"maximum": "17000000", "value": {"maximum": "17000000"}}}, "districts": {"repeated_string": {"value": ["278"]}}}`

## 3. Listing-detail units

Fixture `https://divar.ir/v/gaSfxzZ8` (fetched live from `GET https://api.divar.ir/v8/posts-v2/web/gaSfxzZ8`): `webengage.credit = 700000000`, `webengage.rent = 9000000`; visible rows `ودیعه: ‏۷۰۰,۰۰۰,۰۰۰ تومان`, `اجارهٔ ماهانه: ‏۹,۰۰۰,۰۰۰ تومان`. → **detail numeric fields are toman.** The pipeline cross-checks webengage vs text for every listing and flags conflicts (see data_quality_report.md).

## 4. Conclusions

| Layer | Unit | Evidence |
|---|---|---|
| Divar UI filter fields | toman | labels `ودیعه (تومان)`, `اجاره (تومان)` |
| Search API `credit`/`rent` `number_range` | toman | UI→request capture (no ×10); experiments above; server suggestion cache shows `500000000` as `تا ۵۰۰ میلیون` |
| Search card text | toman | `ودیعه: … تومان` |
| Detail `webengage.credit/rent` | toman | fixture + per-listing cross-check |

**Final approved values:** `credit.number_range.maximum = "500000000"`, `rent.number_range.maximum = "17000000"`. No ×10 conversion.

## 5. Uncertainty / API behaviour

- Endpoints are undocumented and may change; schema confirmed only for the run date.
- Filters apply to the advertised deposit/rent. Convertible ads (`قابل تبدیل`) are matched on their advertised figures only.
- 'Similar listings' appended after the real results ignore filters; collected rows stop at that boundary.
- HTTP 200 alone was never taken as proof: each claim above is backed by result-set comparison.
