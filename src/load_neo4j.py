"""Load the collected dataset into Neo4j via the official Python driver.

A node's unique key is always called `id` regardless of its source CSV column name
(`qid` for Film/Director/Actor/Studio/Agency, `event_id` for AwardEvent — AwardEvent rows
aren't real Wikidata entities, they're synthetic "award+year" combinations). Every node also
gets a base `:Entity` label alongside its specific type label(s) — this is what lets 56 people
who are BOTH a Director and an Actor (e.g. Spielberg, Scorsese — real dual-role people found by
src/network_stats.py) collapse into a single node with 2 labels instead of 2 separate nodes:
MERGE always matches on `:Entity {id: ...}` first, then layers on the specific labels.

Usage:
    python -m src.load_neo4j --dir data/output/run2 --uri bolt://localhost:7687 \
        --user neo4j --password password123 --wipe
"""
import argparse
import csv
from collections import defaultdict
from pathlib import Path

from neo4j import GraphDatabase

NODE_FILES = {
    "Film": ("nodes_films.csv", "qid"),
    "Director": ("nodes_directors.csv", "qid"),
    "Actor": ("nodes_actors.csv", "qid"),
    "Studio": ("nodes_studios.csv", "qid"),
    "Agency": ("nodes_agencies.csv", "qid"),
    "AwardEvent": ("nodes_events.csv", "event_id"),
}

BATCH_SIZE = 500


def load_nodes(data_dir: Path) -> dict[str, dict]:
    """Returns {id: {"labels": {...}, "props": {...}}}, merging rows that share the same id
    across different node files (the Director/Actor overlap)."""
    nodes: dict[str, dict] = {}
    for label, (fname, id_col) in NODE_FILES.items():
        path = data_dir / fname
        if not path.exists():
            continue
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                node_id = row[id_col]
                entry = nodes.setdefault(node_id, {"labels": set(), "props": {}})
                entry["labels"].add(label)
                for k, v in row.items():
                    if k == id_col:
                        continue
                    if v and not entry["props"].get(k):
                        entry["props"][k] = v
    return nodes


def chunked(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def load_edges(data_dir: Path) -> dict[str, list[dict]]:
    by_relation: dict[str, list[dict]] = defaultdict(list)
    with open(data_dir / "edges.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            by_relation[row["relation"]].append(
                {"src": row["source"], "tgt": row["target"], "weight": float(row["weight"]), "context": row.get("context", "")}
            )
    return by_relation


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True, help="dataset directory (e.g. data/output/run2)")
    parser.add_argument("--uri", default="bolt://localhost:7687")
    parser.add_argument("--user", default="neo4j")
    parser.add_argument("--password", required=True)
    parser.add_argument("--wipe", action="store_true", help="delete everything first (MERGE alone never removes edges dropped from the CSVs)")
    args = parser.parse_args()
    data_dir = Path(args.dir)

    print("Loading CSVs...")
    nodes = load_nodes(data_dir)
    edges_by_relation = load_edges(data_dir)
    print(f"  {len(nodes)} distinct node ids, {sum(len(v) for v in edges_by_relation.values())} edges across {len(edges_by_relation)} relation types")

    driver = GraphDatabase.driver(args.uri, auth=(args.user, args.password))
    with driver.session() as session:
        if args.wipe:
            print("Wiping existing graph...")
            session.run("MATCH (n) CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 1000 ROWS")
        print("Creating constraints...")
        session.run("CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (n:Entity) REQUIRE n.id IS UNIQUE")

        print("Loading nodes (grouped by label combination, so dual-role nodes get both labels in one write)...")
        by_label_combo: dict[tuple, list[dict]] = defaultdict(list)
        for node_id, entry in nodes.items():
            combo = tuple(sorted(entry["labels"]))
            by_label_combo[combo].append({"id": node_id, "props": entry["props"]})

        for combo, rows in by_label_combo.items():
            label_clause = ":" + ":".join(("Entity",) + combo)
            query = f"UNWIND $rows AS row MERGE (n{label_clause} {{id: row.id}}) SET n += row.props"
            for batch in chunked(rows, BATCH_SIZE):
                session.run(query, rows=batch)
            print(f"  {label_clause}: {len(rows)} nodes")

        print("Loading edges (grouped by relation type, Cypher relationship types can't be parameterized)...")
        for relation, rows in edges_by_relation.items():
            query = (
                "UNWIND $rows AS row "
                "MATCH (a:Entity {id: row.src}), (b:Entity {id: row.tgt}) "
                f"MERGE (a)-[r:{relation}]->(b) SET r.weight = row.weight, r.context = row.context"
            )
            for batch in chunked(rows, BATCH_SIZE):
                session.run(query, rows=batch)
            print(f"  {relation}: {len(rows)} edges")

        result = session.run("MATCH (n) RETURN count(n) AS n")
        node_count = result.single()["n"]
        result = session.run("MATCH ()-[r]->() RETURN count(r) AS r")
        edge_count = result.single()["r"]
        print(f"\nDone. Neo4j now has {node_count} nodes and {edge_count} relationships.")

    driver.close()


if __name__ == "__main__":
    main()
