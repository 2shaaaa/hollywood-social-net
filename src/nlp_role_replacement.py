"""NLP extraction of the REPLACED_IN_ROLE relation ("Conflict/Role replacement") required by
Topic 5 — uses spaCy NER + dependency parsing on each film's full Wikipedia article text.

Technique: for every film, fetch the full plaintext (not just the lead), drop the sections that
are not about making the film (plot, release/reception, later adaptations...), scan the rest for
a trigger verb ("replace"/"recast") in either active or passive voice, pull out the two PERSON
entities involved, and apply a light same-document coreference heuristic (surname-only mentions
resolved to the full name seen earlier in the article). An edge is kept only if:
  1. both names resolve to a Wikidata QID that is instance-of-human (P31=Q5) — drops NER false
     positives, disambiguation pages, bare family-name entities, organizations tagged PERSON;
  2. the replacing person is a cast member of that film (Wikidata P161) — the one who
     took over a part must end up in the cast. This drops replacements of a director
     (Peter Weir taking over Dead Poets Society) or a cinematographer, and names that resolved to
     the wrong person (a cinematographer "Arthur Miller" matched to the playwright).
"""
import re

import spacy

from . import wiki_api_client as wapi
from . import wikidata_client as wd
from .http_utils import get_json

API_URL = "https://en.wikipedia.org/w/api.php"
REPLACE_LEMMAS = {"replace", "recast"}

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


MAX_SCAN_CHARS = 30000  # bounds spaCy processing time on long Featured-Article-length pages

# Sections about something other than making the film: its story, what happened after release,
# and later versions — e.g. Stage Door's 1950s radio adaptation recasting Hepburn's part is not a
# replacement during filmmaking. Matched as substrings of the lowercased heading.
EXCLUDED_SECTION_WORDS = (
    "plot", "synopsis", "adaptation", "remake", "sequel", "version", "radio", "legacy",
    "popular culture", "home media", "release", "reception", "box office", "critical",
    "accolade", "award", "honor", "honour",
)
# Back matter, matched as the whole heading (a substring match would also drop "Production notes").
EXCLUDED_SECTION_TITLES = {
    "see also", "notes", "references", "sources", "citations", "footnotes", "bibliography",
    "further reading", "external links",
}
_HEADING_RE = re.compile(r"^(=+) (.+?) \1$", re.M)


def _is_excluded_section(title: str) -> bool:
    title = title.lower()
    return title in EXCLUDED_SECTION_TITLES or any(w in title for w in EXCLUDED_SECTION_WORDS)


def _filmmaking_text(text: str) -> str:
    """The article minus excluded sections. A sub-section inherits its parent's exclusion
    ("=== Radio ===" under "== Adaptations =="). Headings themselves are left out."""
    kept, stack, pos, excluded = [], [], 0, False
    for m in _HEADING_RE.finditer(text):
        if not excluded:
            kept.append(text[pos : m.start()])
        level = len(m.group(1))
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, _is_excluded_section(m.group(2).strip())))
        excluded = any(ex for _, ex in stack)
        pos = m.end()
    if not excluded:
        kept.append(text[pos:])
    return "\n".join(kept)[:MAX_SCAN_CHARS]


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
    for i, (qid, title) in enumerate(film_titles.items(), 1):
        text = fetch_full_plaintext(session, title)
        for m in extract_replacement_mentions(_filmmaking_text(text)) if text else []:
            m["film_qid"] = qid
            raw_mentions.append(m)
        if verbose and i % 50 == 0:
            print(f"  [nlp:replaced_in_role] scanned {i}/{len(film_titles)} films, {len(raw_mentions)} candidate mentions so far")

    if verbose:
        print(f"  [nlp:replaced_in_role] {len(raw_mentions)} candidate mentions before QID resolution")

    names = sorted({m["old_actor_name"] for m in raw_mentions} | {m["new_actor_name"] for m in raw_mentions})
    name_to_qid = wapi.resolve_qids_for_titles(session, names) if names else {}

    # Precision filter: a resolved QID isn't necessarily a specific human — common surnames
    # ("Downey", "Day-Lewis") can resolve to a Wikimedia disambiguation page or a bare family-name
    # entity, and spaCy's NER can mistag an organization span (e.g. a production company) as
    # PERSON. Require instance-of-human (Q5), same check nlp_agency_representation.py already
    # does for REPRESENTED_BY.
    candidate_qids = sorted(set(name_to_qid.values()))
    instance_of_edges = wd.fetch_relation(session, candidate_qids, "P31") if candidate_qids else []
    human_qids = {qid for qid, value_qid, _ in instance_of_edges if value_qid == "Q5"}

    resolved, n_resolved = [], 0
    for m in raw_mentions:
        old_qid = name_to_qid.get(m["old_actor_name"])
        new_qid = name_to_qid.get(m["new_actor_name"])
        if not old_qid or not new_qid or old_qid == new_qid:
            continue  # name didn't resolve to a real Wikipedia/Wikidata entity -> drop (precision filter)
        n_resolved += 1
        if old_qid not in human_qids or new_qid not in human_qids:
            continue  # resolved to a non-human entity (disambiguation page, family name, company...) -> drop
        resolved.append((m, old_qid, new_qid))

    # Role filter: the replacing person must be in the film's Wikidata cast (P161, which also lists
    # supporting and uncredited parts, unlike the infobox "Starring" field used for ACTED_IN).
    film_ids = sorted({m["film_qid"] for m, _, _ in resolved})
    cast_by_film = {}
    for film_qid, person_qid, _ in (wd.fetch_relation(session, film_ids, "P161") if film_ids else []):
        cast_by_film.setdefault(film_qid, set()).add(person_qid)

    out, seen = [], set()
    for m, old_qid, new_qid in resolved:
        if new_qid not in cast_by_film.get(m["film_qid"], set()):
            continue  # took over a non-acting job (director, cinematographer...) or a mis-resolved name
        key = (m["film_qid"], old_qid, new_qid)
        if key in seen:
            continue  # the same replacement told twice in one article (e.g. Cast and Production)
        seen.add(key)
        out.append({"film_qid": m["film_qid"], "old_actor_qid": old_qid, "new_actor_qid": new_qid, "sentence": m["sentence"]})
    if verbose:
        print(
            f"  [nlp:replaced_in_role] {n_resolved} resolved to QIDs -> {len(resolved)} both human"
            f" -> {len(out)} edges where the replacing person is in the film's cast (P161), deduplicated"
        )
    return out
