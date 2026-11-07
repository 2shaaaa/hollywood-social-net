"""Scrapes Wikipedia award-list pages — the 3rd collection technique required by the plan.

Used for the Palme d'Or: this page doesn't have clean year/won qualifiers on Wikidata like the
Oscars do, so we pull directly from the "List of winners" HTML table on the Wikipedia article
itself.
"""
from bs4 import BeautifulSoup

from .html_table_utils import flatten_table_rows
from .http_utils import get_json

API_URL = "https://en.wikipedia.org/w/api.php"


def _fetch_page_html(session, page_title: str) -> str:
    data = get_json(
        session,
        API_URL,
        params={"action": "parse", "page": page_title, "prop": "text", "format": "json"},
    )
    return data["parse"]["text"]["*"]


def scrape_palme_dor(session) -> list[dict]:
    html = _fetch_page_html(session, "Palme d'Or")
    soup = BeautifulSoup(html, "lxml")
    tables = soup.find_all("table", class_="wikitable")

    records = []
    for table in tables:
        header_cells = table.find("tr").find_all(["th", "td"])
        headers = [c.get_text(" ", strip=True) for c in header_cells]
        if len(headers) < 5 or headers[0] != "Year" or "Title" not in headers[1]:
            continue  # skip the other stats tables (Wins by country, Multiple winners...)

        for row in flatten_table_rows(table, skip_header_rows=1):
            if len(row) < 5:
                continue
            year_text = row[0]["text"]
            film_cell, recipient_cell, country_cell = row[1], row[3], row[4]
            if "cancelled" in (year_text + film_cell["text"]).lower():
                continue
            if not year_text[:4].isdigit():
                continue

            film_title = film_cell["hrefs"][0]["title"] if film_cell["hrefs"] else film_cell["text"]
            directors = [h["title"] for h in recipient_cell["hrefs"] if h.get("title")]
            if not film_title:
                continue

            records.append(
                {
                    "year": year_text[:4],
                    "film_title": film_title,
                    "director_titles": directors,
                    "country": country_cell["text"],
                }
            )
    return records
