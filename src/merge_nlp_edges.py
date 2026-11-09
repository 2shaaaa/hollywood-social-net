"""CLI: merge the NLP edge files (REPLACED_IN_ROLE, REPRESENTED_BY) into a pipeline run's
edges.csv, adding as Actor nodes any person they reference that the pipeline didn't collect
(e.g. an actor replaced during casting, so never credited in the film's infobox).

edges.csv is always rebuilt from edges_structured_only.csv (written by the pipeline), so
re-running this is safe.

Usage:
    python -m src.merge_nlp_edges --dir data/output/run3
"""
import argparse
import csv
from pathlib import Path

from . import wiki_api_client as wapi
from . import wikidata_client as wd
from .http_utils import get_session

NLP_EDGE_FILES = ("replaced_in_role_edges.csv", "represented_by_edges.csv")
NODE_FILES = {
    "nodes_films.csv": "qid", "nodes_directors.csv": "qid", "nodes_actors.csv": "qid",
    "nodes_studios.csv": "qid", "nodes_agencies.csv": "qid", "nodes_events.csv": "event_id",
}


def read_rows(path: Path) -> list[list[str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.reader(f))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True)
    data_dir = Path(parser.parse_args().dir)

    header, *edges = read_rows(data_dir / "edges_structured_only.csv")
    for fn in NLP_EDGE_FILES:
        if (data_dir / fn).exists():
            nlp_rows = read_rows(data_dir / fn)[1:]
            edges.extend(nlp_rows)
            print(f"  + {len(nlp_rows)} edges from {fn}")

    node_ids = set()
    for fn, id_col in NODE_FILES.items():
        if (data_dir / fn).exists():
            with open(data_dir / fn, newline="", encoding="utf-8") as f:
                node_ids |= {r[id_col] for r in csv.DictReader(f)}
    missing = sorted({q for e in edges for q in (e[0], e[1])} - node_ids)

    if missing:
        session = get_session()
        names = wd.fetch_labels(session, missing)
        births = wd.fetch_min_year(session, missing, "P569")
        nationality = {}
        for q, _, label in wd.fetch_relation(session, missing, "P27"):
            nationality.setdefault(q, label)
        titles = wd.fetch_enwiki_titles(session, missing)
        leads = wapi.fetch_lead_extracts(session, sorted(set(titles.values())))
        with open(data_dir / "nodes_actors.csv", "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            for q in missing:
                w.writerow([q, names.get(q, ""), births.get(q, ""), nationality.get(q, ""), leads.get(titles.get(q), "")])
        print(f"  + {len(missing)} people referenced only by NLP edges, added as Actor nodes")

    with open(data_dir / "edges.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(edges)
    print(f"Wrote {len(edges)} edges to {data_dir / 'edges.csv'}")


if __name__ == "__main__":
    main()
