# Tehran Metro Apartment Rental Discovery

Finds Divar apartment-rent listings within walking distance of 15 Tehran metro stations, under a fixed budget
(deposit ≤ 500,000,000 toman, rent ≤ 17,000,000 toman — edit `src/config.py`).

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q tests
.venv/bin/python src/main.py                 # full run, resumable
.venv/bin/python src/main.py --only 278      # one Divar district (pilot)
.venv/bin/python src/report.py               # regenerate reports from cache/results.json
```

Pipeline: OSM/Wikidata stations → Divar districts near stations → filtered Divar search (toman, verified) →
post details → MAP_ROW coordinates → OSRM foot routing to station entrances → classification → outputs/.

Cache: `cache/checkpoint` (completed district searches), `cache/posts` (post JSON), `cache/routing`.
Delete those for a fresh snapshot. See `outputs/FINAL_REPORT.md` for results and method.

## Run on GitHub
Actions tab → **refresh-listings** → *Run workflow*. Takes ~1.5–2 h (serial, 1.2 s between Divar requests).
When done, `index.html` (GitHub Pages) and the Excel files at the repo root are updated; full outputs are attached
to the run as the `outputs` artifact.
