"""CLI: extract REPRESENTED_BY edges from talent-agency Wikipedia articles and write both the
Agency node table and the edge table as standalone CSVs (merged into the main dataset separately).

Usage:
    python -m src.run_agency_representation --out-dir data/output/run2
"""
import argparse
import csv

from . import nlp_agency_representation as ar
from . import wiki_api_client as wapi
from .http_utils import get_session


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", required=True, help="directory to write nodes_agencies.csv and represented_by_edges.csv into")
    args = parser.parse_args()

    session = get_session()
    seeds = [s for s in ar.AGENCY_SEEDS if s["key"] != "innovative_artists"]  # no Wikidata item found
    edges = ar.extract_agency_representation(session, seeds)

    agency_titles = {s["title"] for s in seeds}
    agency_qids = wapi.resolve_qids_for_titles(session, sorted(agency_titles))

    # resolve_qids_for_titles can return both the queried title and its redirect target for the
    # same QID (e.g. "Gersh Agency" and "The Gersh Agency" -> same QID) -> dedupe by QID, keeping
    # the exact title we originally seeded with when available.
    qid_to_name = {}
    for title in agency_titles:
        qid = agency_qids.get(title)
        if qid and qid not in qid_to_name:
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

    print(f"\nWrote {len(agency_qids)} agency nodes to {args.out_dir}/nodes_agencies.csv")
    print(f"Wrote {len(edges)} REPRESENTED_BY edges to {args.out_dir}/represented_by_edges.csv")
    print(f"Wrote evidence sentences to {evidence_path}")


if __name__ == "__main__":
    main()
