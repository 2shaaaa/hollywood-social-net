"""Orchestrator pipeline: award seeds (SPARQL + scrape) -> enrich relations (SPARQL) ->
text (MediaWiki API) -> export nodes/edges/events CSV.

Run a small pilot:
    python -m src.pipeline --pilot --film-limit 50 --out data/output/pilot
"""
import argparse
import csv
import shutil
from collections import defaultdict
from itertools import combinations
from pathlib import Path

from . import config
from . import wikidata_client as wd
from . import wiki_api_client as wapi
from . import scrape_awardlists as scraper
from .http_utils import get_session


def collect_award_rows(session, verbose=True):
    rows = []
    for seed in config.SPARQL_AWARD_SEEDS:
        subject_type = seed.get("subject_type", "film")
        for prop, status in (("P166", "won"), ("P1411", "nominated")):
            subs = wd.fetch_award_subjects(session, seed["qid"], subject_type=subject_type, prop=prop)
            n_with_film = 0
            for r in subs:
                if subject_type == "film":
                    film_qid, film_label = r["subject_qid"], r["subject_label"]
                    person_qid, person_label = None, None
                else:
                    if not r["film_qid"]:
                        continue  # missing "for work" qualifier on Wikidata -> skip, don't guess
                    film_qid, film_label = r["film_qid"], r["film_label"]
                    person_qid, person_label = r["subject_qid"], r["subject_label"]
                n_with_film += 1
                rows.append(
                    {
                        "award_key": seed["key"],
                        "award_label": seed["label"],
                        "film_qid": film_qid,
                        "film_label": film_label,
                        "person_qid": person_qid,
                        "person_label": person_label,
                        "year": r["year"],
                        "status": status,
                        "source": "sparql",
                    }
                )
            if verbose:
                print(f"  [sparql:{status}] {seed['key']}: {n_with_film} rows with a film / {len(subs)} total")

    for seed in config.SCRAPE_AWARD_SEEDS:
        if seed["key"] != "palme_dor":
            continue
        records = scraper.scrape_palme_dor(session)
        all_titles = set()
        for rec in records:
            all_titles.add(rec["film_title"])
            all_titles.update(rec["director_titles"])
        title_to_qid = wapi.resolve_qids_for_titles(session, sorted(all_titles))
        n_with_film = 0
        for rec in records:
            film_qid = title_to_qid.get(rec["film_title"])
            if not film_qid:
                continue
            n_with_film += 1
            director_qid = title_to_qid.get(rec["director_titles"][0]) if rec["director_titles"] else None
            rows.append(
                {
                    "award_key": seed["key"],
                    "award_label": seed["label"],
                    "film_qid": film_qid,
                    "film_label": rec["film_title"],
                    "person_qid": director_qid,
                    "person_label": rec["director_titles"][0] if rec["director_titles"] else None,
                    "year": rec["year"],
                    "status": "won",  # the "List of winners" page has no nominee list to scrape
                    "source": "scrape",
                }
            )
        if verbose:
            print(f"  [scrape] {seed['key']}: {n_with_film} rows with a film / {len(records)} total")
    return rows


def select_balanced_films(award_rows: list[dict], target_films: int) -> set[str]:
    """Pick the final film set using 2 rules:
    1) Keep every film recognized by >=2 different awards/festivals (a "hub" film, important
       for network connectivity).
    2) Fill the rest via round-robin across award sources, so no single region/award dominates
       (a practical application of the regional-balance quota noted in PLAN.md).
    """
    mentions = defaultdict(set)
    by_seed = defaultdict(list)
    seen_in_seed = defaultdict(set)
    for r in award_rows:
        mentions[r["film_qid"]].add(r["award_key"])
        if r["film_qid"] not in seen_in_seed[r["award_key"]]:
            seen_in_seed[r["award_key"]].add(r["film_qid"])
            by_seed[r["award_key"]].append(r["film_qid"])

    selected = {f for f, keys in mentions.items() if len(keys) >= 2}
    seed_keys = list(by_seed.keys())
    idx = {k: 0 for k in seed_keys}
    while len(selected) < target_films:
        progressed = False
        for k in seed_keys:
            lst = by_seed[k]
            while idx[k] < len(lst) and lst[idx[k]] in selected:
                idx[k] += 1
            if idx[k] < len(lst):
                selected.add(lst[idx[k]])
                idx[k] += 1
                progressed = True
                if len(selected) >= target_films:
                    break
        if not progressed:
            break
    return selected


MIN_SHARED_FILMS = 2  # "frequent" collaboration = at least 2 films together


def compute_collaboration_edges(session, director_qids: list[str], actor_qids: list[str], verbose: bool = True):
    """CO_STARRED_WITH / COLLABORATED_WITH between people already in the dataset, counted over their
    full Wikidata filmographies: counting only inside the 1-3 sampled films per director undercounts
    a pair's real history (Coen-McDormand: 1 sampled film vs 9 real ones)."""
    people = sorted(set(director_qids) | set(actor_qids))
    directed = wd.fetch_works_by_person(session, sorted(director_qids), "P57")
    cast_in = wd.fetch_works_by_person(session, people, "P161")

    cast_by_work, directors_by_work = defaultdict(set), defaultdict(set)
    for person, works in cast_in.items():
        for w in works:
            cast_by_work[w].add(person)
    for d, works in directed.items():
        for w in works:
            directors_by_work[w].add(d)

    # only a work shared by >=2 dataset people can produce an edge -> type-check just those
    candidates = {w for w, cast in cast_by_work.items() if len(cast | directors_by_work.get(w, set())) >= 2}
    films = wd.filter_feature_films(session, candidates)

    costar = defaultdict(lambda: {"weight": 0, "films": set()})
    collab = defaultdict(lambda: {"weight": 0, "films": set()})
    for w in films:
        cast = cast_by_work[w]
        for a1, a2 in combinations(sorted(cast), 2):
            costar[(a1, a2)]["weight"] += 1
            costar[(a1, a2)]["films"].add(w)
        for d in directors_by_work.get(w, ()):
            for a in cast - {d}:
                collab[(d, a)]["weight"] += 1
                collab[(d, a)]["films"].add(w)

    costar = {k: v for k, v in costar.items() if v["weight"] >= MIN_SHARED_FILMS}
    collab = {k: v for k, v in collab.items() if v["weight"] >= MIN_SHARED_FILMS}
    if verbose:
        print(
            f"    -> {len(candidates)} works shared by >=2 dataset people, {len(films)} of them are non-documentary films"
            f" | CO_STARRED_WITH: {len(costar)} | COLLABORATED_WITH: {len(collab)} (>= {MIN_SHARED_FILMS} films together)"
        )
    return costar, collab


def run_pipeline(pilot: bool, film_limit: int | None, out_dir: Path, target_films: int | None = None, films_from: Path | None = None):
    session = get_session()
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[1/8] Collecting seeds from awards (SPARQL + scrape)...")
    award_rows = collect_award_rows(session)

    all_film_qids = sorted({r["film_qid"] for r in award_rows})
    print(f"    -> {len(all_film_qids)} unique films before country filtering")

    print("[2/8] Filtering to Hollywood scope (production country includes the US, P495=Q30)...")
    country_edges_all = wd.fetch_relation(session, all_film_qids, "P495")
    country_by_film = defaultdict(set)
    country_label_by_qid = {}
    for f, c_qid, c_label in country_edges_all:
        country_by_film[f].add(c_qid)
        if c_label:
            country_label_by_qid[c_qid] = c_label
    us_film_qids = {f for f in all_film_qids if config.WIKIDATA_US_QID in country_by_film.get(f, set())}
    print(f"    -> {len(us_film_qids)}/{len(all_film_qids)} films have the US among their production countries")
    award_rows = [r for r in award_rows if r["film_qid"] in us_film_qids]
    all_film_qids = sorted(us_film_qids)

    print(f"    -> {len(all_film_qids)} unique US films before final selection, {len(award_rows)} award rows")

    if films_from:
        # reuse an earlier run's film set, so film-level NLP output (REPLACED_IN_ROLE) stays valid,
        # minus films no current award seed selects (e.g. ones from a seed since removed)
        with open(films_from, newline="", encoding="utf-8") as f:
            reused = {r["qid"] for r in csv.DictReader(f)}
        film_qids = sorted(reused & {r["film_qid"] for r in award_rows})
        print(f"    -> Reusing {len(film_qids)}/{len(reused)} films from {films_from} (the rest no longer have a seeding award)")
    elif pilot and film_limit:
        film_qids = all_film_qids[:film_limit]
    elif target_films:
        film_qids = sorted(select_balanced_films(award_rows, target_films))
    else:
        film_qids = all_film_qids
    film_qid_set = set(film_qids)
    award_rows = [r for r in award_rows if r["film_qid"] in film_qid_set]
    print(f"    -> Selected {len(film_qids)} films for this run, {len(award_rows)} related award rows")

    print("[3/8] Fetching director / production / distribution (Wikidata) + starring cast (Wikipedia infobox)...")
    director_edges = wd.fetch_relation(session, film_qids, "P57")
    studio_edges = wd.fetch_relation(session, film_qids, "P272")
    genre_edges = wd.fetch_relation(session, film_qids, "P136")
    distributor_edges = wd.fetch_relation(session, film_qids, "P750")

    # Cast = the infobox `starring` field (credited leads, billing order). Wikidata's P161 can't
    # pick the leads: it has no billing order and also lists uncredited extras.
    film_titles = wd.fetch_enwiki_titles(session, film_qids)
    starring_by_title = wapi.fetch_infobox_starring(session, sorted(set(film_titles.values())))
    starring_titles = sorted({t for lst in starring_by_title.values() for t in lst})
    starring_qid = wapi.resolve_qids_for_titles(session, starring_titles) if starring_titles else {}
    p31_subjects = sorted(set(starring_qid.values()) | {s for _, s, _ in studio_edges})
    humans = {q for q, v, _ in wd.fetch_relation(session, p31_subjects, "P31") if v == "Q5"}
    cast_edges = []
    for film_qid in film_qids:
        kept = set()
        for title in starring_by_title.get(film_titles.get(film_qid), []):
            actor_qid = starring_qid.get(title)
            if actor_qid in humans and actor_qid not in kept:  # links to a band, a duo article, etc. -> drop
                kept.add(actor_qid)
                cast_edges.append((film_qid, actor_qid, title))
    films_without_cast = len(set(film_qids) - {f for f, _, _ in cast_edges})

    # A person recorded as a film's production company is a Wikidata editing error (Leo McCarey
    # on The Bells of St. Mary's), not a studio.
    studio_edges = [(f, s, label) for f, s, label in studio_edges if s not in humans]

    print(
        f"    -> DIRECTED: {len(director_edges)} | ACTED_IN (infobox starring): {len(cast_edges)} "
        f"({films_without_cast} films with no usable starring field) | PRODUCED_BY: {len(studio_edges)}"
    )

    award_person_qids = {r["person_qid"] for r in award_rows if r["person_qid"]}
    director_qids = sorted({d for _, d, _ in director_edges} | award_person_qids)
    actor_qids = sorted({a for _, a, _ in cast_edges})
    studio_qids = sorted({s for _, s, _ in studio_edges})

    print("[4/8] Fetching entity attributes (year, nationality, birth year)...")
    film_years = wd.fetch_min_year(session, film_qids, "P577")
    all_person_qids = sorted(set(director_qids) | set(actor_qids))
    person_birth_years = wd.fetch_min_year(session, all_person_qids, "P569") if all_person_qids else {}
    person_nat_edges = wd.fetch_relation(session, all_person_qids, "P27") if all_person_qids else []

    # MARRIED_TO: spouse (P26), kept only where both sides are already actors/directors in this
    # dataset. P26 is symmetric on Wikidata (recorded on both entities) -> dedupe to one edge
    # per unordered pair using a canonical (min, max) qid ordering.
    person_qid_set = set(all_person_qids)
    spouse_edges_raw = wd.fetch_relation(session, all_person_qids, "P26") if all_person_qids else []
    married_pairs = {tuple(sorted((a, b))) for a, b, _ in spouse_edges_raw if b in person_qid_set}
    nationality_by_person = {}
    for p, _, label in person_nat_edges:
        nationality_by_person.setdefault(p, label)

    genre_by_film = defaultdict(list)
    for f, _, label in genre_edges:
        if label:
            genre_by_film[f].append(label)
    # country_by_film is already available (a set of QIDs) from the Hollywood-filter step above
    # -> turn it into labels here for the CSV output
    country_labels_by_film = {
        f: [country_label_by_qid.get(q, q) for q in qids] for f, qids in country_by_film.items()
    }

    print("[5/8] Fetching English Wikipedia titles + lead text...")
    distributor_qids = sorted({s for _, s, _ in distributor_edges})

    # Drop chronologically impossible DISTRIBUTED_BY edges: Wikidata's P750 often records a
    # company's CURRENT streaming-rights holder rather than the film's original distributor (e.g.
    # classic-era films tagged "Netflix"/"Disney+" because that's who streams them today, even
    # though neither existed yet). Keep an edge only if the distributor's inception (P571)
    # predates or matches the film's release year; keep it by default if either date is missing
    # (common for small/defunct classic-era distributors) rather than risk dropping a real edge.
    distributor_inception = wd.fetch_min_year(session, distributor_qids, "P571") if distributor_qids else {}
    _before = len(distributor_edges)
    distributor_edges = [
        (f_qid, s_qid, label)
        for f_qid, s_qid, label in distributor_edges
        if not (film_years.get(f_qid) and distributor_inception.get(s_qid) and int(film_years[f_qid]) < int(distributor_inception[s_qid]))
    ]
    print(f"    -> DISTRIBUTED_BY: dropped {_before - len(distributor_edges)} anachronistic edges (distributor founded after the film's release)")

    all_entity_qids = sorted(set(film_qids) | set(all_person_qids) | set(studio_qids) | set(distributor_qids))
    titles_map = wd.fetch_enwiki_titles(session, all_entity_qids)
    unique_titles = sorted(set(titles_map.values()))
    extracts_by_title = wapi.fetch_lead_extracts(session, unique_titles)
    display_names = wd.fetch_labels(session, sorted(set(film_qids) | set(all_person_qids)))

    def extract_for(qid):
        t = titles_map.get(qid)
        return extracts_by_title.get(t, "") if t else ""

    print("[6/8] Building award-event nodes + WON_AWARD/NOMINATED_FOR edges...")
    # Process winners first, so we can drop any NOMINATED_FOR that would be semantically
    # redundant with WON_AWARD (a winner isn't also counted as "merely nominated").
    won_keys = set()
    for r in award_rows:
        if r["status"] == "won":
            won_keys.add((r["person_qid"] or r["film_qid"], r["award_key"], r["year"]))

    events = {}
    won_edges = []
    nominated_edges = []
    for r in award_rows:
        # An event is one award in one year. With no year on Wikidata (statement nor ceremony),
        # give the row its own event rather than a shared "<award>_unknown" node, which would
        # falsely put films from different years in the same ceremony.
        event_id = f"{r['award_key']}_{r['year']}" if r["year"] else f"{r['award_key']}_unknown_{r['film_qid']}"
        if event_id not in events:
            events[event_id] = {
                "event_id": event_id,
                "award_key": r["award_key"],
                "award_label": r["award_label"],
                "year": r["year"],
            }
        subject_qid = r["person_qid"] or r["film_qid"]
        if r["status"] == "won":
            won_edges.append((subject_qid, event_id, r["film_qid"]))
        elif (subject_qid, r["award_key"], r["year"]) not in won_keys:
            nominated_edges.append((subject_qid, event_id, r["film_qid"]))

    print("[7/8] Computing derived edges: CO_STARRED_WITH, COLLABORATED_WITH over each person's full filmography...")
    costar_weight, collab_weight = compute_collaboration_edges(session, director_qids, actor_qids)

    # ---------------- CSV export ----------------
    def label_map_from_edges(edges):
        m = {}
        for _, qid, label in edges:
            if label:
                m[qid] = label
        return m

    director_labels = label_map_from_edges(director_edges)
    actor_labels = label_map_from_edges(cast_edges)
    studio_labels = label_map_from_edges(studio_edges)
    distributor_labels = label_map_from_edges(distributor_edges)
    award_person_labels = {r["person_qid"]: r["person_label"] for r in award_rows if r["person_qid"]}
    film_labels = {r["film_qid"]: r["film_label"] for r in award_rows}

    with open(out_dir / "nodes_films.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["qid", "title", "year", "country", "genre", "lead_text"])
        for qid in film_qids:
            w.writerow(
                [
                    qid,
                    display_names.get(qid) or film_labels.get(qid, ""),
                    film_years.get(qid, ""),
                    "; ".join(sorted(set(country_labels_by_film.get(qid, [])))),
                    "; ".join(sorted(set(genre_by_film.get(qid, [])))),
                    extract_for(qid),
                ]
            )

    def write_people_csv(path, qids):
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["qid", "name", "birth_year", "nationality", "lead_text"])
            for qid in qids:
                name = display_names.get(qid) or director_labels.get(qid) or actor_labels.get(qid) or award_person_labels.get(qid, "")
                w.writerow([qid, name, person_birth_years.get(qid, ""), nationality_by_person.get(qid, ""), extract_for(qid)])

    write_people_csv(out_dir / "nodes_directors.csv", director_qids)
    write_people_csv(out_dir / "nodes_actors.csv", actor_qids)

    studio_qids_set, distributor_qids_set = set(studio_qids), set(distributor_qids)
    all_company_qids = sorted(studio_qids_set | distributor_qids_set)
    with open(out_dir / "nodes_studios.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["qid", "name", "role"])
        for qid in all_company_qids:
            roles = []
            if qid in studio_qids_set:
                roles.append("production")
            if qid in distributor_qids_set:
                roles.append("distribution")
            name = studio_labels.get(qid) or distributor_labels.get(qid, "")
            w.writerow([qid, name, ";".join(roles)])

    with open(out_dir / "nodes_events.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["event_id", "award_key", "award_label", "year"])
        for ev in events.values():
            w.writerow([ev["event_id"], ev["award_key"], ev["award_label"], ev["year"]])

    with open(out_dir / "edges.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["source", "target", "relation", "weight", "context"])
        for f_qid, d_qid, _ in director_edges:
            w.writerow([d_qid, f_qid, "DIRECTED", 1, ""])
        for f_qid, a_qid, _ in cast_edges:
            w.writerow([a_qid, f_qid, "ACTED_IN", 1, ""])
        for f_qid, s_qid, _ in studio_edges:
            w.writerow([f_qid, s_qid, "PRODUCED_BY", 1, ""])
        for f_qid, s_qid, _ in distributor_edges:
            w.writerow([f_qid, s_qid, "DISTRIBUTED_BY", 1, ""])
        for subject_qid, event_id, film_qid in won_edges:
            w.writerow([subject_qid, event_id, "WON_AWARD", 1, film_qid or ""])
        for subject_qid, event_id, film_qid in nominated_edges:
            w.writerow([subject_qid, event_id, "NOMINATED_FOR", 1, film_qid or ""])
        for (a1, a2), info in costar_weight.items():
            w.writerow([a1, a2, "CO_STARRED_WITH", info["weight"], "|".join(sorted(info["films"]))])
        for (d, a), info in collab_weight.items():
            w.writerow([d, a, "COLLABORATED_WITH", info["weight"], "|".join(sorted(info["films"]))])
        for p1, p2 in sorted(married_pairs):
            w.writerow([p1, p2, "MARRIED_TO", 1, ""])
    # src.merge_nlp_edges rebuilds edges.csv from this copy + the NLP edge files
    shutil.copy2(out_dir / "edges.csv", out_dir / "edges_structured_only.csv")

    n_nodes = len(film_qids) + len(director_qids) + len(actor_qids) + len(all_company_qids) + len(events)
    n_edges = (
        len(director_edges)
        + len(cast_edges)
        + len(studio_edges)
        + len(distributor_edges)
        + len(won_edges)
        + len(nominated_edges)
        + len(costar_weight)
        + len(collab_weight)
        + len(married_pairs)
    )
    structured_relation_types = {
        "DIRECTED", "ACTED_IN", "PRODUCED_BY", "DISTRIBUTED_BY",
        "WON_AWARD", "NOMINATED_FOR", "CO_STARRED_WITH", "COLLABORATED_WITH", "MARRIED_TO",
    }
    print("\n=== SUMMARY ===")
    print(f"Films: {len(film_qids)} | Directors: {len(director_qids)} | Actors: {len(actor_qids)} | Studios/Distributors: {len(all_company_qids)} | Events: {len(events)}")
    print(f"DIRECTED: {len(director_edges)} | ACTED_IN: {len(cast_edges)} | PRODUCED_BY: {len(studio_edges)} | DISTRIBUTED_BY: {len(distributor_edges)}")
    print(f"WON_AWARD: {len(won_edges)} | NOMINATED_FOR: {len(nominated_edges)} | CO_STARRED_WITH: {len(costar_weight)} | COLLABORATED_WITH: {len(collab_weight)} | MARRIED_TO: {len(married_pairs)}")
    print(f"RELATION TYPES (structured): {len(structured_relation_types)}/10 — still missing REPRESENTED_BY, REPLACED_IN_ROLE (the spaCy NLP step)")
    print(f"TOTAL NODES: {n_nodes} (assignment requires >=1,000, Hollywood scope narrowed) | TOTAL EDGES: {n_edges} (assignment requires >=5,000)")
    print(f"CSV written to: {out_dir}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pilot", action="store_true")
    parser.add_argument("--film-limit", type=int, default=None)
    parser.add_argument("--target-films", type=int, default=None)
    parser.add_argument("--films-from", type=str, default=None, help="reuse the film set of an existing nodes_films.csv")
    parser.add_argument("--out", type=str, default=str(config.DATA_OUTPUT_DIR / "pilot"))
    args = parser.parse_args()
    run_pipeline(
        pilot=args.pilot,
        film_limit=args.film_limit,
        out_dir=Path(args.out),
        target_films=args.target_films,
        films_from=Path(args.films_from) if args.films_from else None,
    )


if __name__ == "__main__":
    main()
