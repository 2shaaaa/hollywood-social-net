> ⚠️ **Superseded by [PLAN_WIKI5.md](PLAN_WIKI5.md)** — this document was written before reading
> [SUBJECT.md](SUBJECT.md) (the real assignment), so it assumes the wrong target numbers
> (5,000 combined samples, instead of ≥2,000 nodes/≥5,000 edges/≥10 relation types) and
> doesn't yet have the NLP/Neo4j techniques the assignment requires.
> The Wikidata/SPARQL/scrape collection part is still useful as a foundation, but **follow
> PLAN_WIKI5.md** going forward.

# Data collection plan: international film, TV, and director network

**Course:** Social Media Analysis (Social Media/Network Analysis)
**Goal:** Collect 5,000 samples from Wikipedia (API + Wikidata + wiki dumps + list-page
scraping) consisting of text, relationships between actors, and events, to build a network
for analysis.

**Decisions locked in with the user:**
- Unit of a "sample" = a mix of 3 types: **entity** (node) + **relationship** (edge) + **event**
  (event-node), combined to total 5,000.
- Source: **English Wikipedia + Wikidata** (not the Vietnamese edition, since international
  film data there is too thin).
- Topic scope: **global, multiple film industries** (not limited to 1-2 regions) to have
  both enough data and stay true to the "international" spirit.
- Relationship types: **the full set** — director-film, actor-film, co-starring, studio-film,
  director-actor collaboration, awards/nominations.
- Output: **CSV/JSONL as nodes + edges + events**, directly usable with pandas/NetworkX/Gephi/Neo4j.
- Current stage: **only handing over this written plan for approval**, no code yet. Timeline:
  flexible, organized around work milestones, no hard deadline.

---

## 1. Data model (data schema)

### 1.1 Entities (nodes)
| Type | Main attributes | Source |
|---|---|---|
| `Film` | id (Wikidata QID), title, release year, country, language, genre, runtime, plot summary (text) | Film infobox, Wikidata |
| `Director` | id, name, birth year, nationality, bio lead section (text) | Person infobox, Wikidata |
| `Actor` | id, name, birth year, nationality, bio lead section (text) | Person infobox, Wikidata |
| `Studio` (production/distribution company) | id, name, country, year founded | Film infobox, Wikidata |
| `AwardEvent` | id, award/festival name, year/edition, category | "List of … award winners" pages |

### 1.2 Relationships (edges)
- `DIRECTED(director → film)`
- `ACTED_IN(actor → film, billing order)`
- `CO_STARRED_WITH(actor ↔ actor, via film)` — derived from `ACTED_IN`
- `PRODUCED_BY(film → studio)`
- `COLLABORATED_WITH(director ↔ actor, weight = number of shared films)` — derived
- `WON / NOMINATED(film|director|actor → AwardEvent, category)`

### 1.3 Text
Every film/director/actor node keeps its lead-section summary for text analysis (topic
modeling, NER, comparing descriptions across film regions) — satisfying the "collect text"
requirement alongside relationships and events.

---

## 2. Data-scope strategy (enough richness, still feasible)

Rather than crawling the entire film catalog (too large, too noisy), the **seed** is drawn
from **major international film award/festival lists**, spanning **1950–2025**, spread across
regions:

- The Oscars (Best Picture, Best Director, Best International Feature)
- Cannes (Palme d'Or + competition lineups for selected years)
- Venice (Golden Lion), Berlin (Golden Bear)
- BAFTA, the Césars (France), the Goyas (Spain)
- Asian film awards: Asian Film Awards, Blue Dragon (South Korea), Golden Horse
  (Taiwan/Chinese-language), the Japan Academy
- (Optional add-on) Sundance, international TV awards (International Emmy) for TV titles
  matching the topic name

**Regional balance quota** (avoiding a Hollywood tilt): North America ~35%, Europe ~25%,
Asia ~25%, the rest (Latin America/Middle East/Africa/Oceania) ~15%.

### Quantity estimate (to be calibrated after the pilot — see section 4)

| Component | Estimate | Type |
|---|---|---|
| Films | 900 – 1,200 | node |
| Directors | 400 – 600 | node |
| Actors (top-billed, up to 3-5/film) | 900 – 1,200 | node |
| Studios | 150 – 250 | node |
| Award/festival events (per edition) | 150 – 250 | event-node |
| DIRECTED | 900 – 1,200 | edge |
| PRODUCED_BY | 900 – 1,200 | edge |
| WON/NOMINATED | 1,500 – 2,500 | edge |
| ACTED_IN | 2,500 – 3,500 | edge |

→ The total estimate **comfortably exceeds 5,000** (a safety margin). At the final-dataset
step (stage 4), we'll **prioritize keeping all entities + core relations** (DIRECTED,
PRODUCED_BY, WON/NOMINATED) then **controlled-sample** the `ACTED_IN` portion down to exactly
5,000 — making sure every node keeps at least one edge (no random cuts that fragment the
network).

---

## 3. Collection method — exactly the 3 required techniques (scraping / API / wiki dumps)

| Technique | Used for | Tooling |
|---|---|---|
| **API** (MediaWiki Action API + Wikidata Query Service/SPARQL) | Build a structured seed list (e.g. a SPARQL query for every person with occupation = film director and ≥1 film on Wikidata); fetch summaries, text extracts, categories per page by QID | `requests`, `SPARQLWrapper`, the `wikipedia`/`pywikibot` libraries |
| **Wiki dumps** | Bulk-extract film/person infoboxes (directors, actors, studios, awards) at scale, without the API's rate limits; or use the Wikidata JSON dump to get ready-made relation triples, more reliable than free-form parsing | `mwxml`, `mwparserfromhell`, `WikiExtractor`, or a Wikidata dump (JSON/TTL) filtered by entity type |
| **Scraping (controlled crawling)** | Fetch "list" pages (List of Academy Award for Best Director winners, List of Cannes Palme d'Or winners…) that the API/dumps don't expose in a tidy form — the main source for **events** | `requests` + `BeautifulSoup`/`pandas.read_html`, respecting `robots.txt`, rate limiting, a clearly identifying User-Agent (academic purpose) |

The 3 techniques complement each other: **API/Wikidata** builds the seed & canonical
relations; **dumps** bulk-scan infoboxes; **crawling** pulls event/award tables.

---

## 4. Execution plan (stages)

0. **Pilot (feasibility check)** — run the whole pipeline at a small scale (~100–150 samples,
   e.g. just Oscar Best Picture 2015–2024) to confirm the API/dump/crawl steps work correctly,
   measure speed and real-world missing-data rates → **recalibrate the section 2 estimates**
   before scaling to 5,000.
1. **Seed & final design** — lock the list of awards/festivals to pull, lock the final schema.
2. **Bulk collection** — run API + dump + crawl in parallel per award source, save raw data.
3. **Relation extraction & normalization** — parse infoboxes, build the edge tables, dedupe by
   Wikidata QID (merging data from the 3 sources).
4. **Cleaning & balancing** — drop films missing minimum required info, check region/time
   quotas, trim to exactly 5,000 samples using the priority rules from section 2.
5. **Export the dataset** — `nodes.csv`, `edges.csv`, `events.csv` + `README.md` (data
   dictionary, sources, license).
6. **(Optional) Quick illustrative analysis** — load into NetworkX, try degree/betweenness/
   community metrics to prove the dataset is usable, feeding the usefulness-evaluation section
   of the report.

*(As currently scoped, this stops at planning only — the stages above will be implemented in
code once the plan is approved.)*

---

## 5. Risks & notes

- **The full English dump is very heavy** (~20GB compressed). Mitigation: use the Wikidata
  Query Service to get the list of relevant pages first, then only fetch that set via the API;
  dumps are only needed for the "bulk extraction" technical requirement, and a (smaller,
  entity-type-filterable) Wikidata dump can be used instead of the full Wikipedia dump.
- **Rate limits while crawling**: respect robots.txt, add delays, prefer API/dumps over
  crawling individual film pages directly.
- **Licensing**: Wikipedia text is CC BY-SA 4.0, Wikidata is CC0 — cite the source & license
  clearly in the README when submitting.
- **If the pilot still doesn't yield 5,000 quality samples**, see the fallback options in
  section 7.

---

## 6. Evaluating the usefulness of this topic

**In the context of the Social Media Analysis course:**
- This is a **collaboration/affiliation network** (not real user-interaction data like
  likes/shares/follows), but it's well suited to illustrate the core concepts of network
  analysis: building a network from unstructured data, bipartite projection (actor–film →
  actor–actor network), centrality measures (degree/betweenness/eigenvector centrality to find
  "connector stars"), community detection (clusters by country/film movement), the "small
  world" effect (akin to the famous Bacon Number problem, extended internationally), temporal
  network analysis (1950–2025), and homophily (directors tending to re-team with the same
  crew/country).
- **A limitation worth flagging**: it contains no real social-media behavioral data (posts,
  comments, user interactions). The report should clarify this is a "social network" in the
  network-science sense (a graph of social relations), not "social media" in the platform
  sense — worth cross-checking against the instructor's specific rubric/requirements to be
  sure it fits.

**In general practice:** this kind of collaboration network is genuinely used in
recommendation systems (films), entertainment-industry analysis (predicting success from crew
networks), influence/reputation analysis, and research on network inequality (who's always
central, gender/nationality bias in international cinema).

---

## 7. Fallback options (if the main topic lacks data)

1. **Nobel Prize network** — laureates, nominees, affiliated institutes/universities; Wikidata
   has very strong, highly structured SPARQL coverage here.
2. **International football transfer network** — very large dataset, transfer events are
   clearly recorded by season.
3. **International music artist network** — collaborations, record labels, Grammy Awards;
   a structure similar to the film topic.
4. **Scientific co-authorship network** (via Wikidata "educated at"/"doctoral advisor") — a
   classic in academic SNA.

---

## 8. Breakthrough / extension ideas (optional, not required)

1. **Cross-referencing two kinds of networks**: add real data from Twitter/X or Reddit about
   the films/directors in the dataset, comparing the "knowledge network" (Wikipedia) against
   the "public-opinion network" (real social-media buzz).
2. **Temporal/dynamic analysis**: build the network per decade to observe shifts in cinema's
   center of power (Hollywood → globalization, the post-*Parasite* (2020) Asian cinema wave,
   streaming's influence).
3. **Bias & fairness analysis**: measure gender/nationality representation at central network
   positions — a sociological, topical angle that stands out.
4. **Link prediction with Graph ML**: train a model to predict future collaborations or
   award-winning likelihood based on a crew's network position.
5. **Knowledge graph + LLM (Graph RAG)**: build a film-network lookup chatbot, answering things
   like "which director connects Scorsese and Bong Joon-ho in the fewest steps" — illustrating
   a modern network + AI application.

---

## 9. Items needing approval

Feedback requested on:
- The quantity estimates in section 2 (does any type's ratio need adjusting?).
- The award/festival source list in section 2 (add/remove any sources?).
- Whether to add TV series as their own dedicated node type, or treat film as the primary
  focus with TV as secondary?
- Once approved, implementation: write the collection code following the 4 stages in section 4.
