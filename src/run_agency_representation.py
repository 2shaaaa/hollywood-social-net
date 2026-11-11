"""CLI: build REPRESENTED_BY edges (person -> talent agency) from two sources and write the Agency
node table, the edge table and an evidence table as standalone CSVs (merged into the main dataset
separately):
  1. Wikipedia text — spaCy NER over "client" sentences in the seeded agencies' own articles
     (nlp_agency_representation.py);
  2. Wikidata P1875 "represented by" on the dataset's actors/directors, kept only when the value
     is a talent agency.
Both sources are thin: Wikipedia keeps no client rosters (those live in trade press / IMDbPro),
and on Wikidata only ~1% of this dataset's people carry P1875.

Usage:
    python -m src.run_agency_representation --out-dir data/output/run3 \
        --actors data/output/run3/nodes_actors.csv --directors data/output/run3/nodes_directors.csv
"""
import argparse
import csv

from . import nlp_agency_representation as ar
from . import wiki_api_client as wapi
from . import wikidata_client as wd
from .http_utils import get_session

TALENT_AGENCY_QID = "Q5354754"  # "talent agency" on Wikidata
SOURCE_TEXT = "wikipedia_text"
SOURCE_P1875 = "wikidata_P1875"


def _load_qids(path: str) -> set[str]:
    with open(path, newline="", encoding="utf-8") as f:
        return {row[0] for row in csv.reader(f)} - {"qid"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", required=True, help="directory to write nodes_agencies.csv and represented_by_edges.csv into")
    parser.add_argument("--actors", required=True, help="path to nodes_actors.csv from a pipeline run")
    parser.add_argument("--directors", required=True, help="path to nodes_directors.csv from a pipeline run")
    args = parser.parse_args()

    # Scope filter: a Wikipedia "clients" sentence on an agency's page lists ALL of that
    # agency's clients (authors, athletes, TV hosts, agency founders...), not just film
    # actors/directors. Topic 5 is specifically about actor/director representation, so keep
    # only edges whose person is already one of the actors/directors this dataset collected.
    allowed_person_qids = _load_qids(args.actors) | _load_qids(args.directors)

    session = get_session()
    seeds = [s for s in ar.AGENCY_SEEDS if s["key"] != "innovative_artists"]  # no Wikidata item found

    # resolve_qids_for_titles can return both the queried title and its redirect target for the
    # same QID (e.g. "Gersh Agency" and "The Gersh Agency" -> same QID) -> dedupe by QID, keeping
    # the title we seeded with.
    seed_qids = wapi.resolve_qids_for_titles(session, [s["title"] for s in seeds])
    seed_name_by_qid = {}
    for s in seeds:
        if seed_qids.get(s["title"]):
            seed_name_by_qid.setdefault(seed_qids[s["title"]], s["title"])

    # --- Source 1: Wikipedia text (NLP) ---
    text_edges_raw = ar.extract_agency_representation(session, seeds)
    text_edges = [e for e in text_edges_raw if e["person_qid"] in allowed_person_qids]
    print(f"  [nlp:represented_by] {len(text_edges)}/{len(text_edges_raw)} edges kept after restricting to actors/directors already in this dataset")

    # --- Source 2: Wikidata P1875 "represented by" ---
    # The value must be a talent agency: an instance of (a subclass of) talent agency, or one of the
    # seeded agencies (ICM Partners is typed only as "business"). This drops modeling agencies,
    # art galleries, film distributors and individual agents that P1875 also points to.
    p1875 = wd.fetch_relation(session, sorted(allowed_person_qids), "P1875")
    candidate_agencies = sorted({agency for _, agency, _ in p1875})
    talent_agencies = wd.fetch_instances_of(session, candidate_agencies, TALENT_AGENCY_QID) | set(seed_name_by_qid)
    p1875_edges = [(person, agency) for person, agency, _ in p1875 if agency in talent_agencies]
    print(
        f"  [wikidata:represented_by] {len(p1875)} P1875 statements on {len({p for p, _, _ in p1875})} dataset people"
        f" -> {len(p1875_edges)} point to a talent agency"
    )

    # --- Merge: one edge per (person, agency), remembering which source(s) support it ---
    pairs = {}
    for e in text_edges:
        d = pairs.setdefault((e["person_qid"], e["agency_qid"]), {"sources": set(), "sentence": ""})
        d["sources"].add(SOURCE_TEXT)
        d["sentence"] = d["sentence"] or e["sentence"]
    for person, agency in p1875_edges:
        pairs.setdefault((person, agency), {"sources": set(), "sentence": ""})["sources"].add(SOURCE_P1875)
    both = sum(1 for d in pairs.values() if len(d["sources"]) == 2)
    print(f"  [represented_by] {len(pairs)} unique person-agency edges ({both} found by both sources)")

    # Agency node names: the seeded title, else the Wikidata label (any language as a last resort,
    # e.g. a Japanese talent agency labelled only in `ja`). Only agencies with >=1 edge are written.
    used_agencies = sorted({agency for _, agency in pairs})
    names = {q: seed_name_by_qid[q] for q in used_agencies if q in seed_name_by_qid}
    names.update(wd.fetch_labels(session, [q for q in used_agencies if q not in names], any_language=True))

    with open(f"{args.out_dir}/nodes_agencies.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["qid", "name"])
        for qid in used_agencies:
            w.writerow([qid, names.get(qid, "")])

    # `context` carries the supporting source(s), e.g. "wikidata_P1875" or "wikidata_P1875+wikipedia_text".
    with open(f"{args.out_dir}/represented_by_edges.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["source", "target", "relation", "weight", "context"])
        for (person, agency), d in sorted(pairs.items()):
            w.writerow([person, agency, "REPRESENTED_BY", 1, "+".join(sorted(d["sources"]))])

    evidence_path = f"{args.out_dir}/represented_by_evidence.csv"
    with open(evidence_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["person_qid", "agency_qid", "agency_name", "sources", "sentence"])
        for (person, agency), d in sorted(pairs.items()):
            w.writerow([person, agency, names.get(agency, ""), "+".join(sorted(d["sources"])), d["sentence"]])

    print(f"\nWrote {len(used_agencies)} agency nodes to {args.out_dir}/nodes_agencies.csv")
    print(f"Wrote {len(pairs)} REPRESENTED_BY edges to {args.out_dir}/represented_by_edges.csv")
    print(f"Wrote evidence to {evidence_path}")


if __name__ == "__main__":
    main()
