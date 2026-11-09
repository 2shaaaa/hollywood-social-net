"""Wikidata client: SPARQL (structured relations) + Action API (QID lookup by enwiki page title)."""
from collections import defaultdict

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
    """Return a list of {subject_qid, subject_label, film_qid, film_label, year} for one award.

    - prop="P166" (award received = WON) or prop="P1411" (nominated for = NOMINATED).
    - subject_type="film": awards given to a film (Best Picture, Golden Lion...) -> the subject
      MUST be instance-of film (filters out cases where the same award is also attached to a
      producer or other individual on Wikidata).
    - subject_type="person": awards given to an individual (Best Director...) -> the subject
      MUST be instance-of human; the film is read from the P1686 "for work" qualifier (can be
      empty if Wikidata is missing it).
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
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,mul". }}
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
    """Fetch the film -(prop)-> value relation in batches, returning [(film_qid, value_qid_or_literal, value_label)]."""
    out = []
    for batch in _chunks(qids, config.SPARQL_BATCH_SIZE):
        values = " ".join(f"wd:{q}" for q in batch)
        if value_is_entity:
            query = f"""
            SELECT ?film ?value ?valueLabel WHERE {{
              VALUES ?film {{ {values} }}
              ?film wdt:{prop} ?value .
              SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,mul". }}
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
    """Earliest year of a date property (e.g. P577 publication date) for each entity."""
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


def fetch_labels(session, qids: list[str]) -> dict[str, str]:
    """Display name per QID: the English label, else the language-neutral `mul` label — many person
    items (e.g. Christopher Nolan, James Cameron) now carry their name only as `mul`."""
    by_lang = defaultdict(dict)
    for batch in _chunks(qids, config.SPARQL_BATCH_SIZE):
        values = " ".join(f"wd:{q}" for q in batch)
        query = f"""
        SELECT ?item ?label WHERE {{
          VALUES ?item {{ {values} }}
          ?item rdfs:label ?label . FILTER(LANG(?label) IN ("en", "mul"))
        }}
        """
        for row in _run_sparql(session, query):
            by_lang[_qid_of(row["item"]["value"])][row["label"]["xml:lang"]] = row["label"]["value"]
    return {q: langs.get("en") or langs["mul"] for q, langs in by_lang.items()}


def fetch_works_by_person(session, person_qids: list[str], prop: str) -> dict[str, set[str]]:
    """{person_qid: {work_qid, ...}} for every work whose `prop` (P57 director / P161 cast member)
    points to the person — their whole career on Wikidata, not just the sampled films."""
    out = defaultdict(set)
    for batch in _chunks(person_qids, config.SPARQL_BATCH_SIZE):
        values = " ".join(f"wd:{q}" for q in batch)
        query = f"SELECT ?work ?person WHERE {{ VALUES ?person {{ {values} }} ?work wdt:{prop} ?person . }}"
        for row in _run_sparql(session, query):
            out[_qid_of(row["person"]["value"])].add(_qid_of(row["work"]["value"]))
    return out


def filter_feature_films(session, work_qids: set[str], batch_size: int = 200) -> set[str]:
    """Subset of work_qids that are films (P31 subclass of Q11424), minus documentaries (P31 or P136
    subclass of Q93204): a shared TV series or a documentary appearance isn't a film collaboration."""
    keep = set()
    for batch in _chunks(sorted(work_qids), batch_size):
        values = " ".join(f"wd:{q}" for q in batch)
        query = f"""
        SELECT DISTINCT ?work WHERE {{
          VALUES ?work {{ {values} }}
          ?work wdt:P31/wdt:P279* wd:Q11424 .
          FILTER NOT EXISTS {{ ?work (wdt:P31|wdt:P136)/wdt:P279* wd:Q93204 . }}
        }}
        """
        keep.update(_qid_of(row["work"]["value"]) for row in _run_sparql(session, query))
    return keep


def fetch_enwiki_titles(session, qids: list[str]) -> dict[str, str]:
    """English Wikipedia page title for each QID (used to fetch lead text via the MediaWiki API)."""
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
