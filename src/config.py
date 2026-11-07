"""Shared configuration for the film/director network collection pipeline."""
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_RAW_DIR = ROOT_DIR / "data" / "raw"
DATA_PROCESSED_DIR = ROOT_DIR / "data" / "processed"
DATA_OUTPUT_DIR = ROOT_DIR / "data" / "output"

USER_AGENT = "PTMXH-FilmNetworkResearch/0.1 (educational data collection project; social media analysis course)"
REQUEST_DELAY_SEC = 0.25  # delay between requests to respect rate limits
SPARQL_BATCH_SIZE = 50    # max number of QIDs per batch in a VALUES clause
EXTRACT_BATCH_SIZE = 20   # max number of titles per batch when fetching lead text
MAX_CAST_PER_FILM = 5     # number of top-billed cast members to keep per film

WIKIDATA_FILM_QID = "Q11424"  # "film" on Wikidata
WIKIDATA_US_QID = "Q30"       # "United States of America" on Wikidata — used to filter to Hollywood scope

# Awards collected via Wikidata SPARQL. Each seed is queried twice in the pipeline:
# P166 "award received" (WON) and P1411 "nominated for" (NOMINATED) -> 2 separate edge types
# WON_AWARD / NOMINATED_FOR. For awards given to an individual (e.g. Best Director), the
# P1686 "for work" qualifier gives the related film.
SPARQL_AWARD_SEEDS = [
    {"key": "oscar_best_picture", "label": "Academy Award for Best Picture", "qid": "Q102427", "subject_type": "film"},
    {"key": "oscar_best_director", "label": "Academy Award for Best Director", "qid": "Q103360", "subject_type": "person"},
    {"key": "bafta_best_film", "label": "BAFTA Award for Best Film", "qid": "Q139184", "subject_type": "film"},
    {"key": "golden_lion", "label": "Golden Lion (Venice)", "qid": "Q209459", "subject_type": "film"},
    {"key": "golden_bear", "label": "Golden Bear (Berlin)", "qid": "Q154590", "subject_type": "film"},
    # NOTE: oscar_best_intl_feature, golden_horse_best_film, asian_film_award_best_film,
    # blue_dragon_best_film, and national_film_award_india were removed here. They were kept
    # over from the earlier international-scope plan; by their own eligibility rules none of
    # them can realistically surface a US-produced film, so querying them under the current
    # Hollywood scope is pure wasted SPARQL traffic (confirmed: ~540 candidate rows, ~0 survive
    # the US country filter in pipeline.py step [2/8]).
    # --- Hollywood-centric awards, added to raise the share of US films ---
    {"key": "golden_globe_drama", "label": "Golden Globe Award for Best Motion Picture – Drama", "qid": "Q1011509", "subject_type": "film"},
    {"key": "golden_globe_comedy", "label": "Golden Globe Award for Best Motion Picture – Musical or Comedy", "qid": "Q670282", "subject_type": "film"},
    {"key": "sag_outstanding_cast", "label": "SAG Award for Outstanding Performance by a Cast in a Motion Picture", "qid": "Q518675", "subject_type": "film"},
    {"key": "dga_outstanding_directing", "label": "DGA Award for Outstanding Directing – Feature Film", "qid": "Q5280675", "subject_type": "person"},
    {"key": "pga_best_theatrical", "label": "PGA Award for Best Theatrical Motion Picture", "qid": "Q5569374", "subject_type": "film"},
]

# Awards collected via the "scrape" technique (scraping a Wikipedia list page) instead of
# SPARQL, to demonstrate the plan's 3 collection techniques properly.
SCRAPE_AWARD_SEEDS = [
    {"key": "palme_dor", "label": "Palme d'Or (Cannes)", "page": "Palme d'Or"},
]
