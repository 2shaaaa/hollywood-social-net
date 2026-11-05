"""Cấu hình chung cho pipeline thu thập mạng lưới phim/đạo diễn quốc tế."""
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_RAW_DIR = ROOT_DIR / "data" / "raw"
DATA_PROCESSED_DIR = ROOT_DIR / "data" / "processed"
DATA_OUTPUT_DIR = ROOT_DIR / "data" / "output"

USER_AGENT = "PTMXH-FilmNetworkResearch/0.1 (educational data collection project; social media analysis course)"
REQUEST_DELAY_SEC = 0.25  # giãn cách giữa các request để tôn trọng rate limit
SPARQL_BATCH_SIZE = 50    # số QID tối đa mỗi batch trong mệnh đề VALUES
EXTRACT_BATCH_SIZE = 20   # số title tối đa mỗi batch khi lấy lead text
MAX_CAST_PER_FILM = 5     # số diễn viên top-billed lấy mỗi phim

WIKIDATA_FILM_QID = "Q11424"  # "film" trong Wikidata
WIKIDATA_US_QID = "Q30"       # "United States of America" trong Wikidata — dùng để lọc phạm vi Hollywood

# Các giải thưởng lấy qua Wikidata SPARQL. Mỗi seed được truy vấn 2 lần trong pipeline:
# P166 "award received" (đã THẮNG) và P1411 "nominated for" (được ĐỀ CỬ) -> 2 loại cạnh riêng
# WON_AWARD / NOMINATED_FOR. Với giải trao cho cá nhân (vd Best Director), mệnh đề P1686
# "for work" cho biết phim liên quan.
SPARQL_AWARD_SEEDS = [
    {"key": "oscar_best_picture", "label": "Academy Award for Best Picture", "qid": "Q102427", "subject_type": "film"},
    {"key": "oscar_best_director", "label": "Academy Award for Best Director", "qid": "Q103360", "subject_type": "person"},
    {"key": "oscar_best_intl_feature", "label": "Academy Award for Best International Feature Film", "qid": "Q105304", "subject_type": "film"},
    {"key": "bafta_best_film", "label": "BAFTA Award for Best Film", "qid": "Q139184", "subject_type": "film"},
    {"key": "golden_lion", "label": "Golden Lion (Venice)", "qid": "Q209459", "subject_type": "film"},
    {"key": "golden_bear", "label": "Golden Bear (Berlin)", "qid": "Q154590", "subject_type": "film"},
    {"key": "golden_horse_best_film", "label": "Golden Horse Award for Best Feature Film", "qid": "Q5579574", "subject_type": "film"},
    {"key": "asian_film_award_best_film", "label": "Asian Film Award for Best Film", "qid": "Q4806632", "subject_type": "film"},
    {"key": "blue_dragon_best_film", "label": "Blue Dragon Film Award for Best Film", "qid": "Q28758354", "subject_type": "film"},
    {"key": "national_film_award_india", "label": "National Film Award for Best Feature Film (India)", "qid": "Q1435633", "subject_type": "film"},
    # --- Giải mang tính Hollywood, thêm để tăng tỉ lệ phim Mỹ (đề 5 thu hẹp phạm vi) ---
    {"key": "golden_globe_drama", "label": "Golden Globe Award for Best Motion Picture – Drama", "qid": "Q1011509", "subject_type": "film"},
    {"key": "golden_globe_comedy", "label": "Golden Globe Award for Best Motion Picture – Musical or Comedy", "qid": "Q670282", "subject_type": "film"},
    {"key": "sag_outstanding_cast", "label": "SAG Award for Outstanding Performance by a Cast in a Motion Picture", "qid": "Q518675", "subject_type": "film"},
    {"key": "dga_outstanding_directing", "label": "DGA Award for Outstanding Directing – Feature Film", "qid": "Q5280675", "subject_type": "person"},
    {"key": "pga_best_theatrical", "label": "PGA Award for Best Theatrical Motion Picture", "qid": "Q5569374", "subject_type": "film"},
]

# Giải thưởng lấy qua kỹ thuật "quét" (scrape trang danh sách Wikipedia) thay vì SPARQL,
# để minh hoạ đúng 3 kỹ thuật thu thập theo kế hoạch.
SCRAPE_AWARD_SEEDS = [
    {"key": "palme_dor", "label": "Palme d'Or (Cannes)", "page": "Palme d'Or"},
]
