"""CLI: run the REPLACED_IN_ROLE NLP extractor over every film in a collected dataset and
write the resulting edges to a standalone CSV (merged into the main edges.csv separately).

Usage:
    python -m src.run_role_replacement --films data/output/run3/nodes_films.csv --out data/output/run3/replaced_in_role_edges.csv
"""
import argparse
import csv

from . import wikidata_client as wd
from . import nlp_role_replacement as rr
from .http_utils import get_session


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--films", required=True, help="path to a nodes_films.csv from a pipeline run")
    parser.add_argument("--out", required=True, help="output CSV path for REPLACED_IN_ROLE edges")
    args = parser.parse_args()

    with open(args.films) as f:
        film_qids = [row["qid"] for row in csv.DictReader(f)]
    print(f"Loaded {len(film_qids)} films from {args.films}")

    session = get_session()
    titles_map = wd.fetch_enwiki_titles(session, film_qids)
    print(f"Resolved {len(titles_map)}/{len(film_qids)} enwiki titles")

    edges = rr.extract_role_replacements_for_films(session, titles_map)

    # Edge schema matches the main edges.csv convention: source -(relation)-> target, with
    # `context` carrying the film QID this replacement happened on (like WON_AWARD/NOMINATED_FOR
    # do). Modeled person-to-person (new actor -> old actor), consistent with COLLABORATED_WITH.
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["source", "target", "relation", "weight", "context"])
        for e in edges:
            w.writerow([e["new_actor_qid"], e["old_actor_qid"], "REPLACED_IN_ROLE", 1, e["film_qid"]])

    evidence_path = args.out.replace(".csv", "_evidence.csv")
    with open(evidence_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["film_qid", "old_actor_qid", "new_actor_qid", "sentence"])
        for e in edges:
            w.writerow([e["film_qid"], e["old_actor_qid"], e["new_actor_qid"], e["sentence"]])

    print(f"\nWrote {len(edges)} REPLACED_IN_ROLE edges to {args.out}")
    print(f"Wrote evidence sentences to {evidence_path} (for manual QA / the report)")


if __name__ == "__main__":
    main()
