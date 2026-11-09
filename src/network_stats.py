"""Quick network statistics on the collected dataset, using NetworkX directly on the CSVs —
no Neo4j required. Meant as a fast first pass to spot data-quality issues (disconnected
components, isolated nodes, centrality dominated by a handful of hubs) before the official
Neo4j GDS run for the report.

Usage:
    python -m src.network_stats --dir data/output/run2
"""
import argparse
import csv
from collections import Counter
from pathlib import Path

import networkx as nx

NODE_FILES = {
    "Film": "nodes_films.csv",
    "Director": "nodes_directors.csv",
    "Actor": "nodes_actors.csv",
    "Studio": "nodes_studios.csv",
    "AwardEvent": "nodes_events.csv",
    "Agency": "nodes_agencies.csv",
}


def load_nodes(data_dir: Path) -> dict[str, dict]:
    """Returns {qid: {"type": ..., "name": ...}}."""
    nodes = {}
    for node_type, fname in NODE_FILES.items():
        path = data_dir / fname
        if not path.exists():
            continue
        with open(path, newline="", encoding="utf-8") as f:
            r = csv.reader(f)
            header = next(r)
            name_col = 1 if len(header) > 1 else 0
            for row in r:
                if not row:
                    continue
                qid = row[0]
                name = row[name_col] if len(row) > name_col else qid
                nodes[qid] = {"type": node_type, "name": name}
    return nodes


def build_graph(data_dir: Path, nodes: dict[str, dict]) -> nx.Graph:
    g = nx.Graph()
    for qid, attrs in nodes.items():
        g.add_node(qid, **attrs)

    with open(data_dir / "edges.csv", newline="", encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        for row in r:
            src, tgt, relation, weight = row[0], row[1], row[2], float(row[3])
            if src not in nodes or tgt not in nodes:
                continue  # shouldn't happen, but don't let a dangling edge create a bare node
            if g.has_edge(src, tgt):
                g[src][tgt]["weight"] += weight
                g[src][tgt]["relations"].add(relation)
            else:
                g.add_edge(src, tgt, weight=weight, relations={relation})
    return g


def label(nodes: dict[str, dict], qid: str) -> str:
    n = nodes.get(qid, {})
    return f"{n.get('name', qid)} ({n.get('type', '?')})"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True, help="dataset directory (e.g. data/output/run2)")
    parser.add_argument("--betweenness-k", type=int, default=500, help="sample size for approximate betweenness centrality (speed vs. exactness)")
    args = parser.parse_args()
    data_dir = Path(args.dir)

    print("Loading nodes + edges...")
    nodes = load_nodes(data_dir)
    g = build_graph(data_dir, nodes)
    print(f"Graph: {g.number_of_nodes()} nodes, {g.number_of_edges()} unique (undirected, weight-summed) edges")

    print("\n=== CONNECTIVITY ===")
    components = sorted(nx.connected_components(g), key=len, reverse=True)
    isolated = [c for c in components if len(c) == 1]
    print(f"Connected components: {len(components)}")
    print(f"Largest component: {len(components[0])} nodes ({100 * len(components[0]) / g.number_of_nodes():.1f}% of all nodes)")
    print(f"Isolated nodes (0 edges): {len(isolated)}")
    if isolated:
        sample = [label(nodes, next(iter(c))) for c in isolated[:10]]
        print("  sample:", sample)
    if len(components) > 1:
        print("Next 5 largest components:", [len(c) for c in components[1:6]])

    largest = g.subgraph(components[0]).copy()

    print("\n=== DEGREE CENTRALITY (top 10, whole graph) ===")
    degree = sorted(g.degree(weight=None), key=lambda x: x[1], reverse=True)[:10]
    for qid, d in degree:
        print(f"  {d:>5}  {label(nodes, qid)}")

    print(f"\n=== BETWEENNESS CENTRALITY (approx, k={args.betweenness_k} samples, on largest component) ===")
    betweenness = nx.betweenness_centrality(largest, k=min(args.betweenness_k, largest.number_of_nodes()), weight=None, seed=42)
    top_between = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)[:10]
    for qid, score in top_between:
        print(f"  {score:.4f}  {label(nodes, qid)}")

    print("\n=== COMMUNITY DETECTION (Louvain, on largest component) ===")
    communities = nx.algorithms.community.louvain_communities(largest, weight="weight", seed=42)
    communities = sorted(communities, key=len, reverse=True)
    print(f"Communities found: {len(communities)}")
    print(f"Size distribution (top 10): {[len(c) for c in communities[:10]]}")
    for i, comm in enumerate(communities[:5]):
        type_counts = Counter(nodes[q]["type"] for q in comm)
        sample_names = [nodes[q]["name"] for q in list(comm)[:5]]
        print(f"  Community {i} ({len(comm)} nodes, {dict(type_counts)}): e.g. {sample_names}")

    out_path = data_dir / "network_stats_summary.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["metric", "qid", "name", "type", "value"])
        for qid, d in degree:
            w.writerow(["degree_top10", qid, nodes[qid]["name"], nodes[qid]["type"], d])
        for qid, score in top_between:
            w.writerow(["betweenness_top10", qid, nodes[qid]["name"], nodes[qid]["type"], round(score, 6)])
        for i, comm in enumerate(communities):
            for q in comm:
                w.writerow([f"community_{i}", q, nodes[q]["name"], nodes[q]["type"], len(comm)])
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
