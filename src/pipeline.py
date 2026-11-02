"""Pipeline tổng hợp: seed giải thưởng (SPARQL + scrape) -> enrich quan hệ (SPARQL) ->
text (MediaWiki API) -> xuất nodes/edges/events CSV.

Chạy pilot nhỏ:
    python -m src.pipeline --pilot --film-limit 50 --out data/output/pilot
"""
import argparse
import csv
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
        subs = wd.fetch_award_subjects(session, seed["qid"], subject_type=subject_type)
        n_with_film = 0
        for r in subs:
            if subject_type == "film":
                film_qid, film_label = r["subject_qid"], r["subject_label"]
                person_qid, person_label = None, None
            else:
                if not r["film_qid"]:
                    continue  # thiếu qualifier "for work" trên Wikidata -> bỏ qua, không đoán bừa
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
                    "source": "sparql",
                }
            )
        if verbose:
            print(f"  [sparql] {seed['key']}: {n_with_film} dòng có phim / {len(subs)} tổng")

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
                    "source": "scrape",
                }
            )
        if verbose:
            print(f"  [scrape] {seed['key']}: {n_with_film} dòng có phim / {len(records)} tổng")
    return rows


def select_balanced_films(award_rows: list[dict], target_films: int) -> set[str]:
    """Chọn tập phim cuối cùng theo 2 nguyên tắc:
    1) Giữ lại mọi phim được >=2 giải/LHP khác nhau ghi nhận (phim "hub", quan trọng cho mạng lưới).
    2) Lấp đầy phần còn lại bằng round-robin qua từng nguồn giải thưởng, để không bị lệch về
       một khu vực/giải nào (áp dụng quota cân bằng khu vực nêu trong PLAN.md một cách thực tế).
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


def run_pipeline(pilot: bool, film_limit: int | None, out_dir: Path, target_films: int | None = None):
    session = get_session()
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[1/6] Thu thập hạt giống từ các giải thưởng (SPARQL + scrape)...")
    award_rows = collect_award_rows(session)

    all_film_qids = sorted({r["film_qid"] for r in award_rows})
    print(f"    -> {len(all_film_qids)} phim duy nhất trước khi chọn lọc, {len(award_rows)} dòng giải thưởng")

    if pilot and film_limit:
        film_qids = all_film_qids[:film_limit]
    elif target_films:
        film_qids = sorted(select_balanced_films(award_rows, target_films))
    else:
        film_qids = all_film_qids
    film_qid_set = set(film_qids)
    award_rows = [r for r in award_rows if r["film_qid"] in film_qid_set]
    print(f"    -> Chọn {len(film_qids)} phim cho lần chạy này, {len(award_rows)} dòng giải thưởng liên quan")

    print("[2/6] Lấy quan hệ phim -> đạo diễn / diễn viên / hãng sản xuất (Wikidata)...")
    director_edges = wd.fetch_relation(session, film_qids, "P57")
    cast_edges_raw = wd.fetch_relation(session, film_qids, "P161")
    studio_edges = wd.fetch_relation(session, film_qids, "P272")
    genre_edges = wd.fetch_relation(session, film_qids, "P136")
    country_edges = wd.fetch_relation(session, film_qids, "P495")

    cast_by_film = defaultdict(list)
    for film_qid, actor_qid, label in cast_edges_raw:
        cast_by_film[film_qid].append((actor_qid, label))
    cast_edges = []
    for film_qid, lst in cast_by_film.items():
        for actor_qid, label in lst[: config.MAX_CAST_PER_FILM]:
            cast_edges.append((film_qid, actor_qid, label))

    print(
        f"    -> DIRECTED: {len(director_edges)} | ACTED_IN (sau khi cắt top-{config.MAX_CAST_PER_FILM}): "
        f"{len(cast_edges)} | PRODUCED_BY: {len(studio_edges)}"
    )

    award_person_qids = {r["person_qid"] for r in award_rows if r["person_qid"]}
    director_qids = sorted({d for _, d, _ in director_edges} | award_person_qids)
    actor_qids = sorted({a for _, a, _ in cast_edges})
    studio_qids = sorted({s for _, s, _ in studio_edges})

    print("[3/6] Lấy thuộc tính thực thể (năm, quốc tịch, năm sinh)...")
    film_years = wd.fetch_min_year(session, film_qids, "P577")
    all_person_qids = sorted(set(director_qids) | set(actor_qids))
    person_birth_years = wd.fetch_min_year(session, all_person_qids, "P569") if all_person_qids else {}
    person_nat_edges = wd.fetch_relation(session, all_person_qids, "P27") if all_person_qids else []
    nationality_by_person = {}
    for p, _, label in person_nat_edges:
        nationality_by_person.setdefault(p, label)

    genre_by_film = defaultdict(list)
    for f, _, label in genre_edges:
        if label:
            genre_by_film[f].append(label)
    country_by_film = defaultdict(list)
    for f, _, label in country_edges:
        if label:
            country_by_film[f].append(label)

    print("[4/6] Lấy tiêu đề bài Wikipedia tiếng Anh + đoạn text mở đầu...")
    all_entity_qids = sorted(set(film_qids) | set(all_person_qids) | set(studio_qids))
    titles_map = wd.fetch_enwiki_titles(session, all_entity_qids)
    unique_titles = sorted(set(titles_map.values()))
    extracts_by_title = wapi.fetch_lead_extracts(session, unique_titles)

    def extract_for(qid):
        t = titles_map.get(qid)
        return extracts_by_title.get(t, "") if t else ""

    print("[5/6] Dựng node sự kiện giải thưởng (events) + cạnh WON/NOMINATED...")
    events = {}
    won_edges = []
    for r in award_rows:
        event_id = f"{r['award_key']}_{r['year'] or 'unknown'}"
        if event_id not in events:
            events[event_id] = {
                "event_id": event_id,
                "award_key": r["award_key"],
                "award_label": r["award_label"],
                "year": r["year"],
            }
        subject_qid = r["person_qid"] or r["film_qid"]
        won_edges.append((subject_qid, event_id, r["film_qid"]))

    print("[6/6] Tính cạnh suy ra: CO_STARRED_WITH, COLLABORATED_WITH (director-actor)...")
    costar_weight = defaultdict(lambda: {"weight": 0, "films": set()})
    for film_qid, lst in cast_by_film.items():
        top_cast = [a for a, _ in lst[: config.MAX_CAST_PER_FILM]]
        for a1, a2 in combinations(sorted(top_cast), 2):
            key = (a1, a2)
            costar_weight[key]["weight"] += 1
            costar_weight[key]["films"].add(film_qid)

    directors_by_film = defaultdict(list)
    for f, d, _ in director_edges:
        directors_by_film[f].append(d)
    collab_weight = defaultdict(lambda: {"weight": 0, "films": set()})
    for film_qid in film_qids:
        for d in directors_by_film.get(film_qid, []):
            for a, _ in cast_by_film.get(film_qid, [])[: config.MAX_CAST_PER_FILM]:
                key = (d, a)
                collab_weight[key]["weight"] += 1
                collab_weight[key]["films"].add(film_qid)

    # ---------------- Xuất CSV ----------------
    def label_map_from_edges(edges):
        m = {}
        for _, qid, label in edges:
            if label:
                m[qid] = label
        return m

    director_labels = label_map_from_edges(director_edges)
    actor_labels = label_map_from_edges(cast_edges)
    studio_labels = label_map_from_edges(studio_edges)
    award_person_labels = {r["person_qid"]: r["person_label"] for r in award_rows if r["person_qid"]}
    film_labels = {r["film_qid"]: r["film_label"] for r in award_rows}

    with open(out_dir / "nodes_films.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["qid", "title", "year", "country", "genre", "lead_text"])
        for qid in film_qids:
            w.writerow(
                [
                    qid,
                    film_labels.get(qid, ""),
                    film_years.get(qid, ""),
                    "; ".join(sorted(set(country_by_film.get(qid, [])))),
                    "; ".join(sorted(set(genre_by_film.get(qid, [])))),
                    extract_for(qid),
                ]
            )

    def write_people_csv(path, qids):
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["qid", "name", "birth_year", "nationality", "lead_text"])
            for qid in qids:
                name = director_labels.get(qid) or actor_labels.get(qid) or award_person_labels.get(qid, "")
                w.writerow([qid, name, person_birth_years.get(qid, ""), nationality_by_person.get(qid, ""), extract_for(qid)])

    write_people_csv(out_dir / "nodes_directors.csv", director_qids)
    write_people_csv(out_dir / "nodes_actors.csv", actor_qids)

    with open(out_dir / "nodes_studios.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["qid", "name"])
        for qid in studio_qids:
            w.writerow([qid, studio_labels.get(qid, "")])

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
        for subject_qid, event_id, film_qid in won_edges:
            w.writerow([subject_qid, event_id, "WON_OR_NOMINATED", 1, film_qid or ""])
        for (a1, a2), info in costar_weight.items():
            w.writerow([a1, a2, "CO_STARRED_WITH", info["weight"], "|".join(sorted(info["films"]))])
        for (d, a), info in collab_weight.items():
            w.writerow([d, a, "COLLABORATED_WITH", info["weight"], "|".join(sorted(info["films"]))])

    n_nodes = len(film_qids) + len(director_qids) + len(actor_qids) + len(studio_qids) + len(events)
    n_edges = (
        len(director_edges)
        + len(cast_edges)
        + len(studio_edges)
        + len(won_edges)
        + len(costar_weight)
        + len(collab_weight)
    )
    print("\n=== TỔNG KẾT ===")
    print(f"Films: {len(film_qids)} | Directors: {len(director_qids)} | Actors: {len(actor_qids)} | Studios: {len(studio_qids)} | Events: {len(events)}")
    print(f"DIRECTED: {len(director_edges)} | ACTED_IN: {len(cast_edges)} | PRODUCED_BY: {len(studio_edges)} | WON_OR_NOMINATED: {len(won_edges)}")
    print(f"CO_STARRED_WITH: {len(costar_weight)} | COLLABORATED_WITH: {len(collab_weight)}")
    print(f"TỔNG NODE: {n_nodes} | TỔNG EDGE: {n_edges} | TỔNG MẪU (node+edge): {n_nodes + n_edges}")
    print(f"Đã ghi CSV vào: {out_dir}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pilot", action="store_true")
    parser.add_argument("--film-limit", type=int, default=None)
    parser.add_argument("--target-films", type=int, default=None)
    parser.add_argument("--out", type=str, default=str(config.DATA_OUTPUT_DIR / "pilot"))
    args = parser.parse_args()
    run_pipeline(pilot=args.pilot, film_limit=args.film_limit, out_dir=Path(args.out), target_films=args.target_films)


if __name__ == "__main__":
    main()
