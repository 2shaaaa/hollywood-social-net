"""Sensitivity check for the report: do the GDS results change if the person-person projection is
weighted by the number of shared films (`films`, the larger of the two collaboration weights)
instead of unweighted (what src/gds_stats.py uses)?

Compares, on the same projection as gds_stats.py:
  - degree vs weighted degree (total shared films),
  - PageRank vs weighted PageRank: top-10 overlap + Spearman rank correlation over all people,
  - Louvain vs weighted Louvain: community count, modularity, and NMI between the two partitions,
    next to a baseline NMI between unweighted runs (Louvain's own run-to-run variation).
Betweenness is not compared: GDS reads a relationship weight as a path *cost*, so "more films
together" would make two people *farther* apart — the opposite of the intended meaning.

Usage:
    python -m src.gds_weight_check --dir data/output/run3 --uri bolt://localhost:7688 --password password123
"""
import argparse
import csv
import math
from collections import Counter
from pathlib import Path

from neo4j import GraphDatabase

GRAPH = "people_weight_check"
BASELINE_RUNS = 5


def stream(session, proc: str, weighted: bool, field: str = "score") -> dict:
    config = ", {relationshipWeightProperty: 'films'}" if weighted else ""
    rows = session.run(
        f"CALL gds.{proc}.stream($g{config}) YIELD nodeId, {field} "
        f"RETURN gds.util.asNode(nodeId).id AS id, {field} AS value",
        g=GRAPH,
    )
    return {r["id"]: r["value"] for r in rows}


def louvain(session, prop: str, weighted: bool, concurrency: int = 1):
    """One Louvain run (mutate), so the partition and its count/modularity come from the same run.
    concurrency 1 is reproducible; higher concurrency varies from run to run."""
    config = {"mutateProperty": prop, "concurrency": concurrency}
    if weighted:
        config["relationshipWeightProperty"] = "films"
    stats = session.run(
        "CALL gds.louvain.mutate($g, $config) YIELD modularity, communityCount RETURN *",
        g=GRAPH, config=config).single()
    partition = {r["id"]: r["c"] for r in session.run(
        "CALL gds.graph.nodeProperty.stream($g, $p) YIELD nodeId, propertyValue "
        "RETURN gds.util.asNode(nodeId).id AS id, propertyValue AS c", g=GRAPH, p=prop)}
    return stats, partition


def ranks(values: dict) -> dict:
    """Average ranks (ties share the mean rank), for Spearman."""
    ordered = sorted(values, key=values.get)
    out, i = {}, 0
    while i < len(ordered):
        j = i
        while j + 1 < len(ordered) and values[ordered[j + 1]] == values[ordered[i]]:
            j += 1
        for k in range(i, j + 1):
            out[ordered[k]] = (i + j) / 2
        i = j + 1
    return out


def spearman(a: dict, b: dict) -> float:
    ra, rb = ranks(a), ranks(b)
    ids = list(a)
    ma, mb = sum(ra[i] for i in ids) / len(ids), sum(rb[i] for i in ids) / len(ids)
    cov = sum((ra[i] - ma) * (rb[i] - mb) for i in ids)
    return cov / math.sqrt(sum((ra[i] - ma) ** 2 for i in ids) * sum((rb[i] - mb) ** 2 for i in ids))


def nmi(a: dict, b: dict) -> float:
    """Normalized mutual information (arithmetic-mean normalization) of two partitions."""
    n = len(a)
    ca, cb, joint = Counter(a.values()), Counter(b.values()), Counter((a[i], b[i]) for i in a)
    mi = sum(c / n * math.log((c / n) / ((ca[x] / n) * (cb[y] / n))) for (x, y), c in joint.items())
    ha = -sum(c / n * math.log(c / n) for c in ca.values())
    hb = -sum(c / n * math.log(c / n) for c in cb.values())
    return 2 * mi / (ha + hb) if ha + hb else 1.0


def top10(values: dict) -> list:
    return sorted(values, key=lambda i: -values[i])[:10]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True, help="dataset directory to write gds_weight_check.csv into")
    parser.add_argument("--uri", default="bolt://localhost:7687")
    parser.add_argument("--user", default="neo4j")
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    driver = GraphDatabase.driver(args.uri, auth=(args.user, args.password))
    with driver.session() as s:
        s.run("CALL gds.graph.drop($g, false) YIELD graphName RETURN graphName", g=GRAPH).consume()
        s.run(
            "MATCH (a:Entity)-[r:COLLABORATED_WITH|CO_STARRED_WITH]-(b:Entity) "
            "WHERE elementId(a) < elementId(b) "
            "WITH a, b, max(r.weight) AS films "
            "WITH gds.graph.project($g, a, b, {relationshipProperties: {films: films}}, "
            "     {undirectedRelationshipTypes: ['*']}) AS g RETURN g.nodeCount",
            g=GRAPH,
        ).consume()
        names = {r["id"]: r["name"] for r in s.run(
            "MATCH (n:Entity) WHERE n:Actor OR n:Director RETURN n.id AS id, n.name AS name")}

        deg, wdeg = stream(s, "degree", False), stream(s, "degree", True)
        pr, wpr = stream(s, "pageRank", False), stream(s, "pageRank", True)
        lv_stats, lv = louvain(s, "lv", weighted=False)
        wlv_stats, wlv = louvain(s, "wlv", weighted=True)
        # Baseline for the NMI: how much Louvain itself varies between runs on the unweighted graph
        # (parallel runs visit nodes in a different order each time).
        baseline = [nmi(lv, louvain(s, f"lv_par{i}", weighted=False, concurrency=4)[1]) for i in range(BASELINE_RUNS)]
        s.run("CALL gds.graph.drop($g) YIELD graphName RETURN graphName", g=GRAPH).consume()
    driver.close()

    summary = {
        "degree_top10_overlap": len(set(top10(deg)) & set(top10(wdeg))),
        "degree_spearman": round(spearman(deg, wdeg), 4),
        "pagerank_top10_overlap": len(set(top10(pr)) & set(top10(wpr))),
        "pagerank_spearman": round(spearman(pr, wpr), 4),
        "louvain_communities_unweighted": lv_stats["communityCount"],
        "louvain_modularity_unweighted": round(lv_stats["modularity"], 4),
        "louvain_communities_weighted": wlv_stats["communityCount"],
        "louvain_modularity_weighted": round(wlv_stats["modularity"], 4),
        "louvain_nmi": round(nmi(lv, wlv), 4),
        "louvain_nmi_baseline_min": round(min(baseline), 4),
        "louvain_nmi_baseline_mean": round(sum(baseline) / len(baseline), 4),
    }
    for k, v in summary.items():
        print(f"{k}: {v}")
    for label, a, b in (("degree", deg, wdeg), ("pagerank", pr, wpr)):
        print(f"\n{label} top 10 — unweighted | weighted")
        for x, y in zip(top10(a), top10(b)):
            print(f"  {names.get(x, x):28s} {a[x]:9.2f} | {names.get(y, y):28s} {b[y]:9.2f}")

    with open(Path(args.dir) / "gds_weight_check.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["metric", "variant", "rank", "id", "name", "value"])
        for k, v in summary.items():
            w.writerow([k, "", "", "", "", v])
        for label, a, b in (("degree", deg, wdeg), ("pagerank", pr, wpr)):
            for variant, vals in (("unweighted", a), ("weighted", b)):
                for rank, i in enumerate(top10(vals), 1):
                    w.writerow([label, variant, rank, i, names.get(i, ""), round(vals[i], 6)])
    print(f"\nWrote {Path(args.dir) / 'gds_weight_check.csv'}")


if __name__ == "__main__":
    main()
