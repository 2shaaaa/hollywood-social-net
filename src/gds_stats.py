"""Official network statistics for the report, via Neo4j Graph Data Science, on the person-person
(1-mode) projection: Actor/Director nodes joined by COLLABORATED_WITH / CO_STARRED_WITH.

Centrality is computed on this projection rather than on the full loaded graph because Film,
Studio and AwardEvent nodes sit on every path between two people and get artificially high
betweenness (NetworkX quick pass: 9/10 top-betweenness nodes were studios). A pair linked by both
relation types becomes one edge, weighted by its larger film count. All algorithms run unweighted:
edges are already filtered to >=2 films together, and raw weights are dominated by studio-era
and silent-era output (up to 45 films for one pair in run3); src/gds_weight_check.py measures
how much weighting would change the results.

Usage:
    python -m src.gds_stats --dir data/output/run3 --uri bolt://localhost:7688 --password password123
"""
import argparse
import csv
from collections import Counter
from pathlib import Path
from statistics import median

from neo4j import GraphDatabase

GRAPH = "people"
PERSON = "(n:Actor OR n:Director)"


def top(session, proc: str, k: int = 10) -> list[dict]:
    return session.run(
        f"CALL gds.{proc}.stream($g) YIELD nodeId, score "
        "WITH gds.util.asNode(nodeId) AS n, score ORDER BY score DESC LIMIT $k "
        "RETURN n.id AS id, n.name AS name, labels(n) AS labels, score",
        g=GRAPH, k=k,
    ).data()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True, help="dataset directory to write the summary CSVs into")
    parser.add_argument("--uri", default="bolt://localhost:7687")
    parser.add_argument("--user", default="neo4j")
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    out_dir = Path(args.dir)

    driver = GraphDatabase.driver(args.uri, auth=(args.user, args.password))
    with driver.session() as s:
        s.run("CALL gds.graph.drop($g, false) YIELD graphName RETURN graphName", g=GRAPH).consume()
        proj = s.run(
            "MATCH (a:Entity)-[r:COLLABORATED_WITH|CO_STARRED_WITH]-(b:Entity) "
            "WHERE elementId(a) < elementId(b) "
            "WITH a, b, max(r.weight) AS films "
            "WITH gds.graph.project($g, a, b, {relationshipProperties: {films: films}}, "
            "     {undirectedRelationshipTypes: ['*']}) AS g "
            "RETURN g.nodeCount AS nodes, g.relationshipCount AS rels",
            g=GRAPH,
        ).single()
        people_total = s.run(f"MATCH (n) WHERE {PERSON} RETURN count(n) AS c").single()["c"]
        n_nodes, n_edges = proj["nodes"], proj["rels"] // 2  # undirected stored both ways
        print(f"Person-person projection: {n_nodes} people with >=1 collaboration edge "
              f"(of {people_total} people; {people_total - n_nodes} have none), {n_edges} undirected edges")

        wcc = s.run("CALL gds.wcc.stream($g) YIELD componentId RETURN componentId, count(*) AS size ORDER BY size DESC", g=GRAPH).data()
        print(f"\n=== CONNECTED COMPONENTS (WCC) ===\n{len(wcc)} components, largest {wcc[0]['size']} "
              f"({100 * wcc[0]['size'] / n_nodes:.1f}% of projected people); next sizes: {[c['size'] for c in wcc[1:8]]}")

        results = {}
        for metric, proc in (("degree", "degree"), ("pagerank", "pageRank"), ("betweenness", "betweenness")):
            results[metric] = top(s, proc)
            print(f"\n=== {metric.upper()} (top 10) ===")
            for r in results[metric]:
                print(f"  {r['score']:>10.4f}  {r['name']} ({'/'.join(l for l in r['labels'] if l != 'Entity')})")

        # One Louvain run (mutate) supplies both the partition and its count/modularity; separate
        # stream + stats calls are two runs and can disagree. concurrency 1 makes it reproducible.
        modularity = s.run(
            "CALL gds.louvain.mutate($g, {mutateProperty: 'community', concurrency: 1}) "
            "YIELD modularity, communityCount RETURN modularity, communityCount", g=GRAPH).single()
        louvain = s.run(
            "CALL gds.graph.nodeProperty.stream($g, 'community') YIELD nodeId, propertyValue "
            "WITH gds.util.asNode(nodeId) AS n, propertyValue AS communityId "
            "RETURN communityId, n.id AS id, n.name AS name, n.birth_year AS birth_year",
            g=GRAPH,
        ).data()
        degree_of = {r["id"]: r["score"] for r in s.run(
            "CALL gds.degree.stream($g) YIELD nodeId, score RETURN gds.util.asNode(nodeId).id AS id, score", g=GRAPH).data()}
        sizes = Counter(r["communityId"] for r in louvain)
        print(f"\n=== COMMUNITIES (Louvain) ===\n{modularity['communityCount']} communities, modularity {modularity['modularity']:.3f}")
        print(f"Largest 10 sizes: {[c for _, c in sizes.most_common(10)]}")
        community_rows = []
        for rank, (cid, size) in enumerate(sizes.most_common()):
            members = [r for r in louvain if r["communityId"] == cid]
            births = [int(r["birth_year"]) for r in members if (r["birth_year"] or "").isdigit()]
            hubs = sorted(members, key=lambda r: -degree_of.get(r["id"], 0))[:5]
            if rank < 8:
                born = f"median birth year {int(median(births))}" if births else "no birth years"
                print(f"  #{rank} ({size} people, {born}): {', '.join(h['name'] for h in hubs)}")
            for r in members:
                community_rows.append([rank, r["id"], r["name"], size])

        s.run("CALL gds.graph.drop($g) YIELD graphName RETURN graphName", g=GRAPH).consume()
    driver.close()

    with open(out_dir / "gds_stats_summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["metric", "id", "name", "labels", "value"])
        w.writerow(["projection_people", "", "", "", n_nodes])
        w.writerow(["projection_edges", "", "", "", n_edges])
        w.writerow(["people_without_collab_edges", "", "", "", people_total - n_nodes])
        w.writerow(["wcc_components", "", "", "", len(wcc)])
        w.writerow(["wcc_largest_size", "", "", "", wcc[0]["size"]])
        w.writerow(["louvain_communities", "", "", "", modularity["communityCount"]])
        w.writerow(["louvain_modularity", "", "", "", round(modularity["modularity"], 4)])
        for metric, rows in results.items():
            for r in rows:
                w.writerow([f"{metric}_top10", r["id"], r["name"], "/".join(l for l in r["labels"] if l != "Entity"), round(r["score"], 6)])
    with open(out_dir / "gds_communities.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["community_rank", "id", "name", "community_size"])
        w.writerows(community_rows)
    print(f"\nWrote {out_dir / 'gds_stats_summary.csv'} and {out_dir / 'gds_communities.csv'}")


if __name__ == "__main__":
    main()
