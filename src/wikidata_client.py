"""Client gọi Wikidata: SPARQL (quan hệ có cấu trúc) + Action API (tra QID theo tên trang enwiki)."""
from . import config
from .http_utils import get_json

SPARQL_URL = "https://query.wikidata.org/sparql"
WIKIDATA_API_URL = "https://www.wikidata.org/w/api.php"


def _chunks(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def _run_sparql(session, query: str) -> list:
    data = get_json(
        session,
        SPARQL_URL,
        params={"query": query, "format": "json"},
        timeout=90,
    )
    return data["results"]["bindings"]


def _qid_of(uri: str) -> str:
    return uri.rsplit("/", 1)[-1]


def fetch_award_subjects(session, award_qid: str, subject_type: str = "film", prop: str = "P166") -> list[dict]:
    """Trả về danh sách {subject_qid, subject_label, film_qid, film_label, year} cho 1 giải thưởng.

    - prop="P166" (award received = đã THẮNG) hoặc prop="P1411" (nominated for = được ĐỀ CỬ).
    - subject_type="film": giải trao cho phim (Best Picture, Golden Lion...) -> subject BẮT BUỘC
      là instance-of film (lọc bỏ trường hợp cùng giải cũng được gắn cho nhà sản xuất/cá nhân khác
      trong Wikidata).
    - subject_type="person": giải trao cho cá nhân (Best Director...) -> subject BẮT BUỘC là
      instance-of human, film lấy qua qualifier P1686 "for work" (có thể rỗng nếu Wikidata thiếu).
    """
    type_filter = (
        "?subject wdt:P31/wdt:P279* wd:Q11424 ."
        if subject_type == "film"
        else "?subject wdt:P31 wd:Q5 ."
    )
    query = f"""
    SELECT DISTINCT ?subject ?subjectLabel ?film ?filmLabel ?year WHERE {{
      ?subject p:{prop} ?stmt .
      ?stmt ps:{prop} wd:{award_qid} .
      {type_filter}
      OPTIONAL {{ ?stmt pq:P585 ?date . BIND(YEAR(?date) AS ?year) }}
      OPTIONAL {{ ?stmt pq:P1686 ?film . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    """
    rows = _run_sparql(session, query)
    out = []
    for row in rows:
        out.append(
            {
                "subject_qid": _qid_of(row["subject"]["value"]),
                "subject_label": row.get("subjectLabel", {}).get("value"),
                "film_qid": _qid_of(row["film"]["value"]) if "film" in row else None,
                "film_label": row.get("filmLabel", {}).get("value") if "film" in row else None,
                "year": row.get("year", {}).get("value"),
            }
        )
    return out


def fetch_relation(session, qids: list[str], prop: str, value_is_entity: bool = True) -> list[tuple]:
    """Lấy quan hệ film -(prop)-> value theo lô, trả về [(film_qid, value_qid_or_literal, value_label)]."""
    out = []
    for batch in _chunks(qids, config.SPARQL_BATCH_SIZE):
        values = " ".join(f"wd:{q}" for q in batch)
        if value_is_entity:
            query = f"""
            SELECT ?film ?value ?valueLabel WHERE {{
              VALUES ?film {{ {values} }}
              ?film wdt:{prop} ?value .
              SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
            }}
            """
        else:
            query = f"""
            SELECT ?film ?value WHERE {{
              VALUES ?film {{ {values} }}
              ?film wdt:{prop} ?value .
            }}
            """
        rows = _run_sparql(session, query)
        for row in rows:
            film_qid = _qid_of(row["film"]["value"])
            if value_is_entity:
                value_qid = _qid_of(row["value"]["value"])
                value_label = row.get("valueLabel", {}).get("value")
                out.append((film_qid, value_qid, value_label))
            else:
                out.append((film_qid, row["value"]["value"], None))
    return out


def fetch_min_year(session, qids: list[str], prop: str = "P577") -> dict[str, str]:
    """Năm sớm nhất của một mốc thời gian (vd P577 publication date) cho mỗi entity."""
    out = {}
    for batch in _chunks(qids, config.SPARQL_BATCH_SIZE):
        values = " ".join(f"wd:{q}" for q in batch)
        query = f"""
        SELECT ?item (MIN(YEAR(?date)) AS ?year) WHERE {{
          VALUES ?item {{ {values} }}
          ?item wdt:{prop} ?date .
        }}
        GROUP BY ?item
        """
        rows = _run_sparql(session, query)
        for row in rows:
            out[_qid_of(row["item"]["value"])] = row["year"]["value"]
    return out


def fetch_enwiki_titles(session, qids: list[str]) -> dict[str, str]:
    """Tên bài Wikipedia tiếng Anh tương ứng mỗi QID (để lấy lead text qua MediaWiki API)."""
    out = {}
    for batch in _chunks(qids, config.SPARQL_BATCH_SIZE):
        values = " ".join(f"wd:{q}" for q in batch)
        query = f"""
        SELECT ?item ?title WHERE {{
          VALUES ?item {{ {values} }}
          ?sitelink schema:about ?item ;
                    schema:isPartOf <https://en.wikipedia.org/> ;
                    schema:name ?title .
        }}
        """
        rows = _run_sparql(session, query)
        for row in rows:
            out[_qid_of(row["item"]["value"])] = row["title"]["value"]
    return out


