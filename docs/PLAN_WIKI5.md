# Implementation plan for Topic 5 — Hollywood Actor & Director Network

Supersedes the earlier direction in [PLAN.md](PLAN.md) (written before reading
[SUBJECT.md](SUBJECT.md)). This document maps the actual assignment requirements and lays out
an 8-day roadmap (deadline **23:59 on 11/11/2026**, today being 03/11/2026).

## 0. Decisions locked in

| Issue | Decision |
|---|---|
| Scope | **Hollywood/US** (using the "international topics may narrow their scope" exception) |
| Graph database | **Neo4j** — ships with the GDS library for centrality/community detection needed later in the final assignment, Cypher is easy to learn, good Python driver |
| Role | Doing the whole pipeline solo (collection → NLP → load into Neo4j → report) |
| NLP technique for the 2 new edges | **spaCy** (NER + dependency parsing), not an LLM, to avoid the risk of it "not counting as NLP done by hand" |

## 1. Why the current data (run1) falls short

| Assignment requirement | Current run1 | Gap |
|---|---|---|
| ≥1,000 nodes (narrowed scope) | 1,392 nodes, but only **99/165 films are American (60%)** | Need to collect more US films/people, drop the international portion we no longer need |
| ≥5,000 edges | 3,662 edges | Short by ~1,400+ |
| ≥10 detailed relation types | 6 types | Short by ≥4 types |
| The exact 3 edges Topic 5 names | Only `COLLABORATED_WITH` ≈ "Frequent collaboration"; **missing** "Commercial representation" and "Conflict/Role replacement" | Missing 2/3, and this is the **real NLP** part the assignment wants to see |
| NLP technique on text | 0% — everything comes from structured Wikidata SPARQL | Misses the assignment's core technique |
| Neo4j/ArangoDB/... | Not set up yet, only flat CSV | Not done |
| Report ≥10 pages | Not started | Not done |

**Key point to remember**: the footnote in SUBJECT.md says network quality ≥90% "is **not**
graded at this 11/11 submission step — it's graded in the final assignment." So the goal for
this submission is: **hit the quantity targets + reach 10 relation types + load into Neo4j +
write the report** — the NLP accuracy doesn't need to be perfect yet, as long as the report is
transparent about it (in a "not yet achieved" section).

## 2. New schema for Topic 5

### Nodes
| Type | Source | Notes |
|---|---|---|
| `Film` | Wikidata (country=US) | Scale up from 99 → target ~1,200-1,500 American films |
| `Director` | Wikidata | |
| `Actor` | Wikidata | |
| `Studio` (production company) | Wikidata P272 | |
| `Agency` (talent management company) | **NEW** — a fixed list (CAA, WME, UTA, ICM Partners, Paradigm, Gersh, APA, Independent Artist Group, Verve...) + detected via NLP in text | |
| `AwardEvent` | Wikidata + US-centric awards | Switch seeds to Hollywood-oriented awards |

### Edges — 10+ types total, in 2 groups

**A. Structured (from Wikidata, expanded from the existing 6 types, quick to fetch)**
1. `DIRECTED` (already have)
2. `ACTED_IN` (already have)
3. `PRODUCED_BY` (already have)
4. `WON_AWARD` — split out from the old `WON_OR_NOMINATED` (P166)
5. `NOMINATED_FOR` — split out separately, additionally sourced via P1411 "nominated for" (previously ignored)
6. `CO_STARRED_WITH` (already have, derived)
7. `COLLABORATED_WITH` — **this is exactly the "frequent collaboration"** edge Topic 5 asks for (which director keeps picking which actor) — already have it, keeping as-is but applying a weight≥2 threshold to match the "frequent" meaning
8. `DISTRIBUTED_BY` — distribution company (P750), distinct from the production company
9. `MARRIED_TO` — spouse (P26), kept only where both sides are already actors/directors in this dataset — a genuine social tie not derivable from any other relation here, structured/high-precision, real yield (111 unique pairs out of 2,383 people)

**B. NLP-derived (extracted from text with spaCy — the assignment's actual focus)**
10. `REPRESENTED_BY` — **"Commercial representation"**: NER detects an ORG entity matching the agency list + dependency parsing finds a "sign/represent/client of" verb phrase near the agency name in the actor/director's bio
11. `REPLACED_IN_ROLE` — **"Conflict/Role replacement"**: scans the "Production"/"Casting" section of a film article for patterns like "replaced by / recast / dropped out / fired from / departed" plus 2 PERSON entities (the person replaced, the replacement), linked to the relevant film

→ Totals **11 detailed relation types**, above the required minimum.

**Dropped**: `BASED_ON` (P144, film based on another work) was tried and removed — after restricting it to "target must also be one of our collected films" (to avoid pulling in Book/Play nodes outside the schema), it only yielded 2 edges out of 714 films. Keeping a relation type that thin looked more like padding the type-count than genuine diversity, so it was cut. Replaced by `MARRIED_TO`, which uses the same low-cost structured-fetch pattern but yields a real, substantial edge count (111 pairs) instead of 2.

## 3. Hollywood data-scaling strategy (to fix the "60% American" gap)

Switch award seeds away from international/European/Asian awards (Cannes, Venice, Berlin,
Golden Horse...) toward **Hollywood-centric awards**, still via Wikidata SPARQL as before
(the `fetch_award_subjects` infrastructure already supports this):

- Golden Globe Awards (film + television)
- Screen Actors Guild (SAG) Awards
- Critics' Choice Awards
- Directors Guild of America (DGA) Award
- Producers Guild of America (PGA) Award
- Primetime Emmy Award (extending into **TV series** — matching the original assignment
  wording "actors/directors" without limiting it to film)
- Keep the Oscars/BAFTA (BAFTA still goes to plenty of American films)

If that still doesn't reach ~1,200-1,500 American films: widen further with a Wikidata query
for "American films with recorded box-office figures" (P2142, as a popularity proxy) instead
of relying on awards alone.

## 4. Setting up Neo4j

1. Install Neo4j Desktop (or Docker: `docker run -p7474:7474 -p7687:7687 neo4j:5`) — with the
   GDS + APOC plugins.
2. Write a `src/load_neo4j.py` script using the Python `neo4j` driver to:
   - Create a uniqueness constraint on `qid`/`event_id`/`agency_id` for each label.
   - Load nodes in batches (`UNWIND $rows AS row MERGE (n:Film {qid: row.qid}) SET n += row`).
   - Load edges in batches similarly, with `MATCH ... MERGE ... -[r:RELATION]->...`.
3. Sample queries for the report: top-10 directors by degree, number of connected components
   (`CALL gds.wcc.stream(...)`), a few of the most central nodes (`CALL gds.betweenness.stream(...)`).

## 4b. Network analysis stage (after loading Neo4j)

Use a **library** for both steps — no hand-rolled algorithms, no LLM:

1. **NetworkX** (Python, reading straight from the CSVs) — for quick checks during development:
   degree distribution, number of connected components, a few basic centrality metrics —
   doesn't require waiting for Neo4j to be fully set up.
2. **Neo4j Graph Data Science (GDS)** — the official version that goes into the report, run
   directly on the loaded database:
   - `CALL gds.graph.project(...)` creates an in-memory graph projection
   - `CALL gds.degree.stream(...)` / `CALL gds.betweenness.stream(...)` — finding central
     "hub" directors/actors
   - `CALL gds.louvain.stream(...)` or `gds.wcc.stream(...)` — community detection / connected
     components (do directors-actors cluster by studio or by decade?)
   - These results feed directly into the report's "Statistics on the built network" section.

## 5. 8-day schedule (03/11 → 11/11)

| Day | Task |
|---|---|
| Tue 03/11 (today) | Approve this plan; switch seeds to Hollywood awards; re-run the pipeline to scale up American films |
| Wed 04/11 | Finish the structured collection (hit node/edge targets), split WON/NOMINATED, add DISTRIBUTED_BY/BASED_ON |
| Thu 05/11 | Install spaCy, write + test the `REPLACED_IN_ROLE` extractor on a few known famous cases (Justice League, All the Money in the World...) |
| Fri 06/11 | Write + test the `REPRESENTED_BY` extractor (NER + agency gazetteer), add manual entries if the yield is too low |
| Sat 07/11 | Merge everything, run the full pipeline, QA the numbers (≥1,000 nodes/≥5,000 edges/≥10 types) |
| Sun 08/11 | Install Neo4j, write `load_neo4j.py`, load the data, try some queries |
| Mon 09/11 | Compute network statistics (degree, components, community) for the report + draw charts |
| Tue 10/11 | Write the 10-page report (covering every section from SUBJECT.md), clean up the GitHub repo, push |
| Wed 11/11 morning | Buffer / final review |

If we fall behind schedule, **cut scope in this priority order**: (1) simplify
`REPRESENTED_BY` (only needs a few dozen edges, manual entries are fine), (2) drop community
detection from the report (basic stats are enough), (3) never cut the required node/edge/
relation-type counts — those are the assignment's hard requirements.

## 5b. Deferred task — Infobox cross-validation (do later, not blocking current work)

Reduced-scope version: parse the raw Infobox wikitext (via `mwparserfromhell`) for a random
sample of ~30-50 films, compare director/cast against what Wikidata gave us, and report a
concrete agreement/accuracy percentage — goes into the report's "preprocessing steps" /
accuracy discussion. Addresses the earlier note: "dữ liệu từ Wiki phải để ý Infobox, một số
thực thể được gán nhãn sẵn nhưng chưa chắc đúng hết." Scheduled after the two NLP relations
(REPLACED_IN_ROLE, REPRESENTED_BY) and before report writing.

## 5c. Status: data + NLP stage complete

Final merged numbers in `data/output/run2/`: **3,956 nodes / 18,778 edges / 11 distinct
relation types** — all three assignment minimums (≥1,000 nodes, ≥5,000 edges, ≥10 relation
types) cleared with margin. `REPLACED_IN_ROLE`: 25 edges (714 films scanned, ~3.5% yield).
`REPRESENTED_BY`: 41 edges / 6 agencies (built by scanning each agency's own Wikipedia article
for "clients" mentions, not each actor's bio — direct bio-scanning was tested and found ~0%
yield). `BASED_ON` (P144) was tried and dropped — only 2/714 films yielded an edge after
restricting the target to films already in-dataset, too thin to justify keeping as a distinct
type. `MARRIED_TO` (P26) added in its place — structured, near-zero engineering cost (same
`fetch_relation` helper), 111 unique spouse pairs among the 2,383 actors/directors already
collected. Next: Neo4j (section 4), then network stats (section 4b), then the report.

## 6. Risks

- **`REPRESENTED_BY` from Wikipedia may yield very little**, since bios rarely state "signed
  with CAA" explicitly — mitigate by adding a small manually-curated table (citing public press
  sources) if automated NLP falls short, and be transparent in the report that this is a hybrid
  NLP + curation approach.
- **Whether the edge count should scale down proportionally with the narrowed scope** is not
  specified by the assignment; the safe call: still aim for the full ≥5,000 edges so we don't
  lose points if graded against the general requirement.
- **English spaCy model** (`en_core_web_sm`, or `en_core_web_trf` for higher accuracy but
  slower) — needs to be installed, not yet in `requirements.txt`.

## 7. Final decisions (locked in to start coding — 05/11)

1. The 11-relation-type schema in section 2: **keep as is**, not expanding with the previously
   discussed `Distributor`/`Role`/`Franchise`/`Genre-node` entities — to avoid scope creep with
   only ~6 days left; noted here as a possible extension for the final assignment later if time
   allows.
2. The Hollywood award list in section 3: **keep as is**, not adding the Tonys (theater is
   outside Topic 5's film/TV scope).
3. Neo4j: **Docker** (`docker run -p7474:7474 -p7687:7687 ... neo4j:5-enterprise`, or community
   + the GDS plugin) — check that the machine has Docker before running step 4.

### Actual schedule is 2 days behind the original plan — compressed starting today (05/11, 6 days left)

| Today 05/11 | Switch to Hollywood seeds + expand relation types (merging the old 03-04/11 work) |
|---|---|
| 06/11 | spaCy: `REPLACED_IN_ROLE` extractor |
| 07/11 | spaCy: `REPRESENTED_BY` extractor |
| 08/11 | Merge everything, run the full pipeline, QA the numbers |
| 09/11 | Neo4j (Docker) + load script + NetworkX/GDS stats |
| 10/11 | Write the 10-page report, clean up GitHub, push |
| 11/11 morning | Buffer |
