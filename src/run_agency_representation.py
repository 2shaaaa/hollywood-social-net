"""CLI: extract REPRESENTED_BY edges from talent-agency Wikipedia articles and write both the
Agency node table and the edge table as standalone CSVs (merged into the main dataset separately).

Usage:
    python -m src.run_agency_representation --out-dir data/output/run2 \
        --actors data/output/run2/nodes_actors.csv --directors data/output/run2/nodes_directors.csv
"""
import argparse
import csv

from . import nlp_agency_representation as ar
from . import wiki_api_client as wapi
from .http_utils import get_session


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
    edges_raw = ar.extract_agency_representation(session, seeds)
    edges = [e for e in edges_raw if e["person_qid"] in allowed_person_qids]
    print(f"  [nlp:represented_by] {len(edges)}/{len(edges_raw)} edges kept after restricting to actors/directors already in this dataset")

    agency_titles = {s["title"] for s in seeds}
    agency_qids = wapi.resolve_qids_for_titles(session, sorted(agency_titles))

    # resolve_qids_for_titles can return both the queried title and its redirect target for the
    # same QID (e.g. "Gersh Agency" and "The Gersh Agency" -> same QID) -> dedupe by QID, keeping
    # the exact title we originally seeded with when available. Only keep an agency that still
    # has >=1 surviving edge after the actor/director scope filter above, to avoid writing an
    # orphan Agency node with zero edges.
    agencies_with_edges = {e["agency_qid"] for e in edges}
    qid_to_name = {}
    for title in agency_titles:
        qid = agency_qids.get(title)
        if qid and qid in agencies_with_edges and qid not in qid_to_name:
            qid_to_name[qid] = title

    with open(f"{args.out_dir}/nodes_agencies.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["qid", "name"])
        for qid, name in qid_to_name.items():
            w.writerow([qid, name])

    with open(f"{args.out_dir}/represented_by_edges.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["source", "target", "relation", "weight", "context"])
        for e in edges:
            w.writerow([e["person_qid"], e["agency_qid"], "REPRESENTED_BY", 1, ""])

    evidence_path = f"{args.out_dir}/represented_by_evidence.csv"
    with open(evidence_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["person_qid", "agency_qid", "agency_title", "sentence"])
        for e in edges:
            w.writerow([e["person_qid"], e["agency_qid"], e["agency_title"], e["sentence"]])

    print(f"\nWrote {len(qid_to_name)} agency nodes to {args.out_dir}/nodes_agencies.csv")
    print(f"Wrote {len(edges)} REPRESENTED_BY edges to {args.out_dir}/represented_by_edges.csv")
    print(f"Wrote evidence sentences to {evidence_path}")


if __name__ == "__main__":
    main()
