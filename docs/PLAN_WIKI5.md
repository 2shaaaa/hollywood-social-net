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
6. `CO_STARRED_WITH` (derived) — two dataset people both cast (P161) in ≥2 films together
7. `COLLABORATED_WITH` — **this is exactly the "frequent collaboration"** edge Topic 5 asks for (which director keeps picking which actor): director (P57) and cast member (P161) on ≥2 films together. Both derived edges are counted over each person's **full Wikidata filmography** (non-documentary films only), not just the sampled films — see "Collaboration-edge recount" in section 5c
8. `DISTRIBUTED_BY` — distribution company (P750), distinct from the production company
9. `MARRIED_TO` — spouse (P26), kept only where both sides are already actors/directors in this dataset — a genuine social tie not derivable from any other relation here, structured/high-precision, real yield (111 unique pairs out of 2,383 people)

**B. NLP-derived (extracted from text with spaCy — the assignment's actual focus)**
10. `REPRESENTED_BY` — **"Commercial representation"**: NER detects an ORG entity matching the agency list + dependency parsing finds a "sign/represent/client of" verb phrase near the agency name in the actor/director's bio. Scope-filtered to keep only clients who are already actors/directors in this dataset (an agency's "clients" sentence also lists authors, athletes, TV hosts, and its own founders — not relevant to Topic 5)
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

Final merged numbers in `data/output/run2/`: **3,952 nodes / 18,204 edges / 11 distinct
relation types** — all three assignment minimums (≥1,000 nodes, ≥5,000 edges, ≥10 relation
types) cleared with margin. `REPLACED_IN_ROLE`: 25 edges (714 films scanned, ~3.5% yield).
`REPRESENTED_BY`: **12 edges / 5 agencies** (scanning each agency's own Wikipedia article for
"clients" mentions found 41 raw matches, but 29/41 (71%) named a person outside this dataset's
actor/director set — authors, athletes, TV hosts, or the agency's own founders/executives, not
film talent; added a scope filter requiring the person already be a collected actor/director,
dropping ICM Partners entirely since both of its matches were non-film authors). `BASED_ON`
(P144) was tried and dropped — only 2/714 films yielded an edge after restricting the target to
films already in-dataset, too thin to justify keeping as a distinct type. `MARRIED_TO` (P26)
added in its place — structured, near-zero engineering cost (same `fetch_relation` helper), 111
unique spouse pairs among the 2,383 actors/directors already collected.

A first NetworkX quick pass (`src/network_stats.py`) surfaced 3 data-quality issues, fixed before
moving to Neo4j:
1. 56 QIDs listed in both `nodes_directors.csv` and `nodes_actors.csv` (real dual-role people,
   e.g. Spielberg/Scorsese also credited as cast) — not fixed in the CSVs themselves (both roles
   are real), but noted for the Neo4j loader: `MERGE` by `qid` with both labels, don't create 2
   nodes.
2. `REPRESENTED_BY` precision gap (above) — fixed.
3. `DISTRIBUTED_BY` had 545 chronologically impossible edges (e.g. classic 1930s-80s films tagged
   "distributed by Netflix/Disney+" because Wikidata's P750 records whoever currently holds
   streaming rights, not the original theatrical distributor) — fixed by requiring the
   distributor's inception (P571) to predate the film's release year; dropped 3 studios left with
   zero edges as a result (`Turner Entertainment`, `Warner Bros. Home Entertainment`,
   `Central Motion Picture Exchange`). Netflix's degree dropped from 512 to 89, no longer an
   outlier dominating centrality.

## 4. Neo4j — load, done

`src/load_neo4j.py` loads all 6 node CSVs and `edges.csv` via the official `neo4j` driver. Every
node gets a universal `:Entity {id: ...}` label (the MERGE key) plus its specific type label(s) —
this is what collapses a dual-role person (the 56 above, plus 1 case found only at load time:
`Leo McCarey`, tagged as both `Director` and `Studio` since his own name is recorded as the
production company on some of his films) into one node instead of two.

Loading surfaced one more precision bug: 17/25 `REPLACED_IN_ROLE` edges referenced a person QID
that had never been collected as an Actor/Director node (`MAX_CAST_PER_FILM=5` only keeps the
top-billed cast, so a replaced/replacing person past that cutoff was a real person but not yet a
node) — fixed by resolving and adding those 23 QIDs as Actor nodes. Checking all 25 edges'
endpoints against Wikidata's P31 (instance of) then found `nlp_role_replacement.py` was missing
the human-instance filter `nlp_agency_representation.py` already has: 5 edges resolved to a
non-human entity (2 Wikipedia name-disambiguation pages, 1 bare "hyphenated family name" entity,
and — the actual bug — 1 case where a **film production company** was mistagged PERSON by
spaCy's NER and ended up as a "replaced actor"). Added the same P31=Q5 filter to
`nlp_role_replacement.py` and dropped those 5 edges plus the resulting orphan nodes.

One more upstream data error found at load time: `Leo McCarey` (QID Q332530) showed up as both a
`Director` and a `Studio` node. Verified against Wikidata directly (not assumed) and against
external sources — McCarey never owned a studio; his real production company was Rainbow
Productions. The Wikidata item for the film *The Bells of St. Mary's* simply has his own person
QID listed as a second P272 "production company" value alongside the correct one (RKO Pictures)
— a genuine editing error in Wikidata's source data, not something our pipeline introduced.
Dropped that 1 `PRODUCED_BY` edge and McCarey's `Studio` label.

**Final loaded graph**: 3,911 distinct nodes, 18,193 relationships, 11 types — this is the true
de-duplicated count (CSV row-sums overlap across files for dual-role people); `REPLACED_IN_ROLE`
now 20 edges (down from 25, all verified human-to-human).

**Collaboration-edge recount (09/11).** The weight≥2 threshold for `COLLABORATED_WITH` written
in section 2 was never actually applied in code: 95.6% of `COLLABORATED_WITH` and 98.5% of
`CO_STARRED_WITH` edges had weight 1. Applying the threshold as-is would have left only 158 / 104
edges, because the weight was counted only inside the sampled films (1-3 award films per
director, top-5 cast each), which undercounts a pair's real history: Coen-McDormand 1 sampled
film vs 9 real ones, Tarantino-Samuel L. Jackson 0 vs 6, Ford-Wayne 4 vs 23. Fixed by keeping the
node set as sampled and counting edges between those nodes over their full Wikidata filmographies
(`compute_collaboration_edges` in `src/pipeline.py`): works where both people appear, restricted
to films (P31 subclass of Q11424), excluding documentaries (P31/P136 subclass of Q93204), so a
shared TV series or documentary appearance doesn't count (2,643 of 23,047 shared works dropped).
Result with ≥2 films: `COLLABORATED_WITH` 3,864, `CO_STARRED_WITH` 16,938; `edges.csv` now
28,544 edges, 11 types, nodes unchanged (3,911); largest connected component 99.7% (was 98.8%).
Caveat for weighted analysis: the highest weights are silent-era one-reel shorts (D. W. Griffith's
Biograph stock company, up to 128 films with one actor; Laurel & Hardy 147), which are real
collaborations but will dominate any weight-based metric. Also fixed in passing: the Leo McCarey
`PRODUCED_BY` row was still present in `edges_structured_only.csv`.

**Neo4j reload + first GDS run (09/11).** Reloaded with `load_neo4j.py --wipe` (MERGE alone keeps
edges that were dropped from the CSVs): 3,911 nodes, 28,539 relationships (5 duplicate CSV rows
merged). `src/gds_stats.py` runs GDS on the person-person projection (Actor/Director +
`COLLABORATED_WITH`/`CO_STARRED_WITH`, a pair with both types = 1 edge, unweighted): 2,072 of
2,399 people have ≥1 collaboration edge, 20,529 edges (matches a direct Cypher count), 9
components, largest 99.1%; Louvain 13 communities, modularity 0.495, split by era and national
industry (modern US auteur circle, median birth 1956: S. L. Jackson, Dafoe, De Niro, Buscemi;
studio-era contract players, 1896; Ford/Wayne westerns, 1917; 1950s-60s MGM/British, 1921;
contemporary British, 1964: Caine, Cumberbatch, Gleeson, Fiennes; plus small German and Chilean
clusters).

The run exposed a **node-selection flaw**: Bess Flowers, an uncredited background extra, ranks #1
on degree, PageRank and betweenness. Cause: `MAX_CAST_PER_FILM=5` keeps the first 5 rows of a
P161 SPARQL query that has no `ORDER BY` and Wikidata has no billing order, so the "top 5" is
arbitrary — *It Happened One Night* kept Bess Flowers, Claire McDowell and Dolores Fuller (all
uncredited) next to Gable and Colbert; *Titanic* kept Danny Nucci but not Kate Winslet;
*Casablanca* kept Paul Panzer and Curt Bois but not Claude Rains. Full-filmography counting then
amplifies such prolific extras (Bess Flowers: 242 P161 works). Also found: 129 nodes have no
display name (42 actors, 4 directors incl. Nolan and Cameron, 83 films). The run2 GDS numbers
above are superseded by run3.

**Cast-selection fix → `data/output/run3` (09/11).** Cast now comes from each film's Wikipedia
`Infobox film` `starring` field (credited leads in poster billing order, linked titles resolved to
QIDs, P31=Q5 required), replacing the arbitrary first-5 P161 rows; `MAX_CAST_PER_FILM` removed.
Checked on the problem films: *It Happened One Night* → Gable, Colbert; *Titanic* → DiCaprio,
Winslet, Zane, Bates…; *Casablanca* → Bogart, Bergman, Henreid, Rains… Only 5 films have no usable
`starring` field. Other fixes in the same pass: names via the `en` label falling back to `mul`
(Nolan, Cameron etc. only have `mul` labels; 0 unnamed people/films now, 5 unnamed studios);
`PRODUCED_BY` targets that are humans dropped (Leo McCarey plus 4 producers wrongly recorded as
production companies, e.g. on *The Graduate*); `--films-from` reuses run2's film set but drops 12
films no current seed selects (foreign-language films with a minor US co-producer credit, left over
from the removed International Feature seed — they had produced the Chilean/German clusters);
NLP merge is now `src/merge_nlp_edges.py` instead of a manual step. Build:
`pipeline --films-from run2/nodes_films.csv --out run3` → `run_agency_representation` →
copy run2's `replaced_in_role_edges*.csv` (same films) → `merge_nlp_edges`.

run3 totals: 4,155 nodes (702 films, 2,681 people, 374 studios, 5 agencies, 393 award events),
34,320 edges (34,315 relationships in Neo4j after MERGE), 11 types — `CO_STARRED_WITH` 21,899,
`COLLABORATED_WITH` 4,250, `ACTED_IN` 3,967, `PRODUCED_BY` 1,049, `DISTRIBUTED_BY` 1,005,
`NOMINATED_FOR` 899, `DIRECTED` 771, `WON_AWARD` 315, `MARRIED_TO` 132, `REPLACED_IN_ROLE` 20,
`REPRESENTED_BY` 13. 0 dangling edges, every film has ≥1 award edge.

run3 GDS (person-person projection, unweighted): 2,356/2,681 people with ≥1 collaboration edge,
25,847 edges, 5 components (largest 99.7%). Degree top: Ward Bond, John Carradine, Henry O'Neill,
Frank Faylen, Reginald Owen (credited studio-era character actors who worked with many stars),
then Samuel L. Jackson, Walter Brennan, Willem Dafoe. PageRank top: S. L. Jackson, Dafoe, Ward Bond,
Carradine, De Niro. Betweenness top (bridges across eras/industries): Christopher Lee, Harry Dean
Stanton, Carradine, Michael Caine, De Niro. Louvain: 12 communities, modularity 0.503 — modern US
(median birth 1957, 939 people), studio era (1901, 544), postwar (1921, 515), contemporary
British/international (1967, 320), plus small ensembles (the *Cocoon* cast, the *Crouching Tiger*
cast).

Next: network stats via Neo4j GDS (section 4b), then the report.

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
