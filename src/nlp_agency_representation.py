"""NLP extraction of the REPRESENTED_BY relation ("Commercial representation") required by
Topic 5 — uses spaCy NER on each talent agency's OWN Wikipedia article, not the actors' bios.

Why this direction and not the other way around: scanning every actor/director's own bio for
an agency name was tested empirically and found near-zero real hits (Wikipedia bios almost
never state "signed with CAA"). Scanning the ~10 agency articles themselves for their
"clients" mentions is far more targeted and was confirmed to work (e.g. the United Talent
Agency article literally says "representing clients such as Don Cheadle, Johnny Depp, and
M. Night Shyamalan").

Technique: for each agency, fetch the full article text, keep only sentences whose lemmas
include "client", run spaCy NER on those sentences, and take every PERSON entity found as a
represented individual.
"""
import spacy

from . import wiki_api_client as wapi
from . import wikidata_client as wd
from .nlp_role_replacement import fetch_full_plaintext

CLIENT_LEMMAS = {"client"}

AGENCY_SEEDS = [
    {"key": "caa", "title": "Creative Artists Agency"},
    {"key": "wme", "title": "William Morris Endeavor"},
    {"key": "uta", "title": "United Talent Agency"},
    {"key": "icm_partners", "title": "ICM Partners"},
    {"key": "paradigm", "title": "Paradigm Talent Agency"},
    {"key": "gersh", "title": "Gersh Agency"},
    {"key": "innovative_artists", "title": "Innovative Artists"},
    {"key": "apa", "title": "Agency for the Performing Arts"},
]

_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp


def extract_client_mentions(text: str) -> list[dict]:
    """Returns [{person_name, sentence}] for every PERSON entity found in a sentence that
    mentions 'client(s)'."""
    nlp = _get_nlp()
    doc = nlp(text)
    out = []
    for sent in doc.sents:
        if not any(tok.lemma_.lower() in CLIENT_LEMMAS for tok in sent):
            continue
        for ent in sent.ents:
            if ent.label_ == "PERSON":
                out.append({"person_name": ent.text, "sentence": sent.text.strip()})
    return out


def extract_agency_representation(session, agency_seeds: list[dict] = AGENCY_SEEDS, verbose: bool = True) -> list[dict]:
    """Returns [{agency_key, agency_title, person_qid, sentence}]."""
    raw_mentions = []
    for seed in agency_seeds:
        text = fetch_full_plaintext(session, seed["title"])
        if not text:
            continue
        mentions = extract_client_mentions(text)
        for m in mentions:
            m["agency_key"] = seed["key"]
            m["agency_title"] = seed["title"]
            raw_mentions.append(m)
        if verbose:
            print(f"  [nlp:represented_by] {seed['key']}: {len(mentions)} client mentions")

    names = sorted({m["person_name"] for m in raw_mentions})
    name_to_qid = wapi.resolve_qids_for_titles(session, names) if names else {}
    agency_qids = wapi.resolve_qids_for_titles(session, [s["title"] for s in agency_seeds])

    # Precision filter: spaCy's NER occasionally mislabels a band/company/other agency as
    # PERSON (e.g. "The Doors", or the agency's own name) -> require instance-of human (Q5).
    candidate_qids = sorted(set(name_to_qid.values()))
    instance_of_edges = wd.fetch_relation(session, candidate_qids, "P31") if candidate_qids else []
    human_qids = {qid for qid, value_qid, _ in instance_of_edges if value_qid == "Q5"}

    out = []
    seen = set()
    for m in raw_mentions:
        person_qid = name_to_qid.get(m["person_name"])
        agency_qid = agency_qids.get(m["agency_title"])
        if not person_qid or not agency_qid or person_qid not in human_qids:
            continue
        key = (person_qid, agency_qid)
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "agency_key": m["agency_key"],
                "agency_qid": agency_qid,
                "agency_title": m["agency_title"],
                "person_qid": person_qid,
                "sentence": m["sentence"],
            }
        )
    if verbose:
        print(f"  [nlp:represented_by] {len(out)} unique person-agency edges after QID resolution")
    return out
