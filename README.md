# International Film & Director Network Collection (Wikipedia/Wikidata)

Project for the Social Media Analysis course.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running data collection

```bash
# Quick pilot (pipeline sanity check, ~50 films)
python3 -m src.pipeline --pilot --film-limit 50 --out data/output/pilot

# Full run, auto-selecting N films via the source/region balancing algorithm
python3 -m src.pipeline --target-films 165 --out data/output/run1
```

Results land in `data/output/<name>/`: `nodes_films.csv`, `nodes_directors.csv`,
`nodes_actors.csv`, `nodes_studios.csv`, `nodes_events.csv`, `edges.csv`.
See [docs/PLAN_WIKI5.md](docs/PLAN_WIKI5.md) for the detailed schema, QA notes, and known
limitations of the current scope (rescoped to Hollywood/US per the actual assignment).

## Source code structure

- `src/config.py` — seed award/festival list, shared parameters.
- `src/http_utils.py` — HTTP session with retries + polite rate limiting.
- `src/wikidata_client.py` — Wikidata SPARQL queries (awards, directors, cast, studios...).
- `src/wiki_api_client.py` — MediaWiki Action API calls (lead text, title-to-QID lookup with redirect handling).
- `src/scrape_awardlists.py` + `src/html_table_utils.py` — scrapes "List of ..." HTML tables (e.g. Palme d'Or) when Wikidata doesn't have enough structure.
- `src/pipeline.py` — orchestrator: collect seeds → enrich relations → export CSV.

The 3 collection techniques required by the assignment (API, scraping, wiki dumps) are each
used for what they're best at: **SPARQL/API** for structured relations, **HTML scraping** for
award lists Wikidata doesn't fully cover, and **wiki dumps** (offline, large-scale) as the
next extension when API rate limits become a bottleneck — see the "Next steps" section in
[docs/PLAN_WIKI5.md](docs/PLAN_WIKI5.md).
