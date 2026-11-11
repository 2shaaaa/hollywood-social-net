# Hollywood Actor & Director Network (Wikipedia/Wikidata + NLP + Neo4j)

Project for the Social Media Analysis course, Topic 5 — *Mạng lưới các diễn viên và đạo diễn
Quốc tế*, scoped to **Hollywood**: films with the United States among their production countries.

The network links films, directors, actors, studios, talent agencies and award events through
11 relation types. Three of them are the edges Topic 5 asks for:

| Topic 5 edge | Relation | How it is obtained |
|---|---|---|
| Frequent collaboration (director A keeps casting actor B) | `COLLABORATED_WITH` | director (P57) × cast (P161) over each person's full Wikidata filmography, ≥2 films together |
| Commercial representation (CAA, WME…) | `REPRESENTED_BY` | spaCy on talent-agency Wikipedia articles + Wikidata P1875 "represented by" |
| Conflict / role replacement during production | `REPLACED_IN_ROLE` | spaCy (NER + dependency parsing) on film articles, verified against Wikidata |

The other eight: `DIRECTED`, `ACTED_IN` (Wikipedia Infobox "Starring"), `PRODUCED_BY`,
`DISTRIBUTED_BY`, `WON_AWARD`, `NOMINATED_FOR`, `CO_STARRED_WITH`, `MARRIED_TO`.

Films are selected by award: every US film that won or was nominated for one of 11 major awards
(10 queried from Wikidata — Oscar Best Picture/Director, BAFTA Best Film, Golden Lion, Golden Bear,
Golden Globe Drama and Musical/Comedy, SAG cast, DGA, PGA — plus the Palme d'Or scraped from
Wikipedia). Design notes, QA findings and the history of fixes are in
[docs/PLAN_WIKI5.md](docs/PLAN_WIKI5.md).

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

Neo4j 5 with the Graph Data Science plugin, via Docker:

```bash
docker run -d --name neo4j-hollywood -p 7474:7474 -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/<password> -e 'NEO4J_PLUGINS=["graph-data-science"]' neo4j:5
```

## Building the network (6 steps)

Run from the repository root. Steps 2 and 3 only need step 1's output and can run in parallel;
step 2 is the longest (it reads every film article).

```bash
# 1. Structured collection (Wikidata SPARQL + MediaWiki API) -> node CSVs + edges.csv
python -m src.pipeline --out data/output/run3

# 2. REPLACED_IN_ROLE (NLP)
python -m src.run_role_replacement --films data/output/run3/nodes_films.csv \
    --out data/output/run3/replaced_in_role_edges.csv

# 3. REPRESENTED_BY (NLP + Wikidata P1875)
python -m src.run_agency_representation --out-dir data/output/run3 \
    --actors data/output/run3/nodes_actors.csv --directors data/output/run3/nodes_directors.csv

# 4. Merge the NLP edges into edges.csv
python -m src.merge_nlp_edges --dir data/output/run3

# 5. Load into Neo4j (--wipe clears the database first)
python -m src.load_neo4j --dir data/output/run3 --password <password> --wipe

# 6. Network analysis with Neo4j GDS, and the weighted-vs-unweighted sensitivity check
python -m src.gds_stats --dir data/output/run3 --password <password>
python -m src.gds_weight_check --dir data/output/run3 --password <password>
```

`load_neo4j`, `gds_stats` and `gds_weight_check` default to `bolt://localhost:7687`; pass
`--uri` for another port.

## Output files (`data/output/run3/`)

| File | Content |
|---|---|
| `nodes_films.csv`, `nodes_directors.csv`, `nodes_actors.csv`, `nodes_studios.csv`, `nodes_agencies.csv`, `nodes_events.csv` | Nodes, keyed by Wikidata QID (`event_id` for award events) |
| `edges.csv` | All edges: `source, target, relation, weight, context` |
| `edges_structured_only.csv` | Step 1 edges only (input of step 4) |
| `replaced_in_role_edges.csv`, `represented_by_edges.csv` | NLP edges, plus `*_evidence.csv` with the source sentence/source of each edge |
| `gds_stats_summary.csv`, `gds_communities.csv`, `gds_weight_check.csv` | GDS results |

`weight` is the number of shared films for `CO_STARRED_WITH` / `COLLABORATED_WITH` (1 elsewhere);
`context` holds the related film QID(s), or the evidence source for `REPRESENTED_BY`.

## Source code structure

Modules in `src/`, grouped by the step of the build they belong to:

| Step | Module | What it does |
|---|---|---|
| shared | `config.py` | Seed award list (10 Wikidata awards + Palme d'Or), batch sizes, request delay |
| shared | `http_utils.py` | HTTP session with retries (incl. HTTP 429) and polite rate limiting (0.25 s/request) |
| shared | `wikidata_client.py` | Wikidata SPARQL helpers, batched 50 QIDs per query (award subjects and years, relations, labels, filmographies, film-type and class checks) |
| shared | `wiki_api_client.py` | MediaWiki Action API calls: lead text, full article text, Infobox `starring` field, title-to-QID lookup with redirect handling |
| 1 | `scrape_awardlists.py`, `html_table_utils.py` | Scrapes the Palme d'Or "List of winners" HTML table (flattens rowspan/colspan cells) |
| 1 | `pipeline.py` | Structured collection: award seeds → US filter → film relations → attributes → award events → collaboration edges → 7 CSV files |
| 2 | `nlp_role_replacement.py`, `run_role_replacement.py` | `REPLACED_IN_ROLE`: spaCy NER + dependency parsing on film articles, verified against Wikidata (human, in the film's cast) |
| 3 | `nlp_agency_representation.py`, `run_agency_representation.py` | `REPRESENTED_BY`: spaCy on talent-agency articles + Wikidata P1875, merged per (person, agency) |
| 4 | `merge_nlp_edges.py` | Rebuilds `edges.csv` from `edges_structured_only.csv` + the two NLP edge files |
| 5 | `load_neo4j.py` | Loads nodes (merged by QID, so dual-role people get both labels) and edges into Neo4j |
| 6 | `gds_stats.py` | Neo4j GDS on the person–person projection: WCC, degree, PageRank, betweenness, Louvain |
| 6 | `gds_weight_check.py` | Sensitivity check: GDS results unweighted vs weighted by shared-film count |
| check | `network_stats.py` | Quick NetworkX pass over the full graph (used to choose the person–person projection) |

## Data collection techniques

- **Wikidata SPARQL** for structured relations (awards, directors, studios, spouses, filmographies).
- **MediaWiki Action API** for article text, the Infobox "Starring" field (parsed with
  mwparserfromhell) and title-to-QID lookup.
- **HTML scraping** (BeautifulSoup) for the Palme d'Or winners table, which Wikidata covers less cleanly.
- **NLP** (spaCy `en_core_web_sm`) for the two relations that only exist in article text.
