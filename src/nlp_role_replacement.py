"""NLP extraction of the REPLACED_IN_ROLE relation ("Conflict/Role replacement") required by
Topic 5 — uses spaCy NER + dependency parsing on each film's full Wikipedia article text.

Technique: for every film, fetch the full plaintext (not just the lead), scan the sentences
from the "Production"/"Casting" section onward for a trigger verb ("replace"/"recast") in
either active or passive voice, pull out the two PERSON entities involved, apply a light
same-document coreference heuristic (surname-only mentions resolved to the full name seen
earlier in the article), then verify each name resolves to a real Wikidata QID before keeping
the edge — this acts as a precision filter against NER false positives.
"""
import re

import spacy

from . import wiki_api_client as wapi
from .http_utils import get_json

API_URL = "https://en.wikipedia.org/w/api.php"
REPLACE_LEMMAS = {"replace", "recast"}
SECTION_HEADINGS = ("== Production ==", "== Casting ==", "== Development ==")

_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp


def fetch_full_plaintext(session, title: str) -> str:
    """Full article plaintext (not just the lead) — needed because the replacement story is
    usually in the 'Production'/'Casting' section, not the intro.

    IMPORTANT: do NOT pass `exchars` here — the MediaWiki API silently clamps it to ~1,200
    characters for normal API access, which would cut the article off before reaching the
    Production section. Omitting it returns the full article extract instead.
    """
    data = get_json(
        session,
        API_URL,
        params={
            "action": "query",
            "prop": "extracts",
            "explaintext": 1,
            "redirects": 1,
            "titles": title,
            "format": "json",
        },
    )
    for page in data.get("query", {}).get("pages", {}).values():
        return page.get("extract", "")
    return ""


MAX_SCAN_CHARS = 20000  # bounds spaCy processing time on long Featured-Article-length pages


def _production_onward(text: str) -> str:
    idx = None
    for heading in SECTION_HEADINGS:
        i = text.find(heading)
        if i != -1 and (idx is None or i < idx):
            idx = i
    scanned = text[idx:] if idx is not None else text
    return scanned[:MAX_SCAN_CHARS]


def _build_surname_registry(doc) -> dict[str, str]:
    """Map a PERSON entity's last token text (usually the surname) to the longest full-name
    span seen for it earlier in the document, so a later bare-surname mention (e.g. 'Spacey')
    can be resolved back to 'Kevin Spacey'."""
    registry: dict[str, str] = {}
    for ent in doc.ents:
        if ent.label_ != "PERSON":
            continue
        surname = ent[-1].text
        if len(ent) >= 2 and (surname not in registry or len(ent.text) > len(registry[surname])):
            registry[surname] = ent.text
    return registry


def _resolve_person(ent, registry: dict[str, str]) -> str | None:
    if ent is None:
        return None
    if len(ent) == 1:
        return registry.get(ent[0].text, ent.text)
    return ent.text


def _person_entity_for_token(token):
    for ent in token.doc.ents:
        if ent.label_ == "PERSON" and ent.start <= token.i < ent.end:
            return ent
    return None


def extract_replacement_mentions(text: str) -> list[dict]:
    """Returns [{old_actor_name, new_actor_name, sentence}] found in `text`."""
    nlp = _get_nlp()
    doc = nlp(text)
    registry = _build_surname_registry(doc)
    out = []
    for sent in doc.sents:
        for token in sent:
            if token.pos_ != "VERB" or token.lemma_.lower() not in REPLACE_LEMMAS:
                continue
            new_ent, old_ent = None, None
            for child in token.children:
                if child.dep_ == "nsubj":  # active voice: "X replaced Y" -> X is new
                    new_ent = _person_entity_for_token(child)
                elif child.dep_ == "dobj":  # active voice object -> Y is old
                    old_ent = _person_entity_for_token(child)
                elif child.dep_ == "nsubjpass":  # passive: "Y was replaced by X" -> Y is old
                    old_ent = _person_entity_for_token(child)
                elif child.dep_ == "agent":  # passive "by X" -> X is new
                    for gc in child.children:
                        if gc.dep_ == "pobj":
                            new_ent = _person_entity_for_token(gc)
            if new_ent is None and token.dep_ == "xcomp":
                # control-verb construction: "X was hired/brought in to replace Y" -> the
                # subject lives on the governing verb ("hired"), not on "replace" itself.
                for gc in token.head.children:
                    if gc.dep_ in ("nsubj", "nsubjpass"):
                        new_ent = _person_entity_for_token(gc)
            new_name = _resolve_person(new_ent, registry)
            old_name = _resolve_person(old_ent, registry)
            if new_name and old_name and new_name != old_name:
                out.append({"old_actor_name": old_name, "new_actor_name": new_name, "sentence": sent.text.strip()})
    return out


def extract_role_replacements_for_films(session, film_titles: dict[str, str], verbose: bool = True) -> list[dict]:
    """film_titles: {film_qid: enwiki_title}. Fetches text, extracts mentions, resolves names
    to Wikidata QIDs, and returns [{film_qid, old_actor_qid, new_actor_qid, sentence}]."""
    raw_mentions = []
    for qid, title in film_titles.items():
        text = fetch_full_plaintext(session, title)
        if not text:
            continue
        scan_text = _production_onward(text)
        for m in extract_replacement_mentions(scan_text):
            m["film_qid"] = qid
            raw_mentions.append(m)

    if verbose:
        print(f"  [nlp:replaced_in_role] {len(raw_mentions)} candidate mentions before QID resolution")

    names = sorted({m["old_actor_name"] for m in raw_mentions} | {m["new_actor_name"] for m in raw_mentions})
    name_to_qid = wapi.resolve_qids_for_titles(session, names) if names else {}

    out = []
    for m in raw_mentions:
        old_qid = name_to_qid.get(m["old_actor_name"])
        new_qid = name_to_qid.get(m["new_actor_name"])
        if not old_qid or not new_qid:
            continue  # name didn't resolve to a real Wikipedia/Wikidata entity -> drop (precision filter)
        out.append(
            {
                "film_qid": m["film_qid"],
                "old_actor_qid": old_qid,
                "new_actor_qid": new_qid,
                "sentence": m["sentence"],
            }
        )
    if verbose:
        print(f"  [nlp:replaced_in_role] {len(out)} edges confirmed after QID resolution")
    return out
