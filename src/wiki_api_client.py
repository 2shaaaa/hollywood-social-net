"""MediaWiki Action API client (English Wikipedia): fetches the lead (intro) text by title."""
from .http_utils import get_json

API_URL = "https://en.wikipedia.org/w/api.php"


def _chunks(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def resolve_qids_for_titles(session, titles: list[str], batch_size: int = 50) -> dict[str, str]:
    """Look up the Wikidata QID for an English Wikipedia page title, transparently handling
    redirect pages via pageprops.wikibase_item — avoids failures when a title scraped from a
    wikilink is itself a redirect (e.g. 'Bong Joon-ho' redirects to 'Bong Joon Ho')."""
    out = {}
    for batch in _chunks(titles, batch_size):
        data = get_json(
            session,
            API_URL,
            params={
                "action": "query",
                "prop": "pageprops",
                "ppprop": "wikibase_item",
                "titles": "|".join(batch),
                "redirects": 1,
                "format": "json",
            },
        )
        query = data.get("query", {})
        redirect_map = {r["to"]: r["from"] for r in query.get("redirects", [])}
        for page in query.get("pages", {}).values():
            title = page.get("title")
            qid = page.get("pageprops", {}).get("wikibase_item")
            if not qid or not title:
                continue
            out[title] = qid
            original = redirect_map.get(title)
            if original:
                out[original] = qid
    return out


def fetch_lead_extracts(session, titles: list[str], batch_size: int = 20, max_chars: int = 600) -> dict[str, str]:
    """Return {title: lead/intro text}. Uses redirects=1 to transparently follow redirect pages."""
    out = {}
    for batch in _chunks(titles, batch_size):
        data = get_json(
            session,
            API_URL,
            params={
                "action": "query",
                "prop": "extracts",
                "exintro": 1,
                "explaintext": 1,
                "exchars": max_chars,
                "redirects": 1,
                "titles": "|".join(batch),
                "format": "json",
            },
        )
        pages = data.get("query", {}).get("pages", {})
        # map original (redirect) title -> resolved title, so we don't lose the lookup
        redirect_map = {r["from"]: r["to"] for r in data.get("query", {}).get("redirects", [])}
        title_to_extract = {}
        for page in pages.values():
            t = page.get("title")
            extract = page.get("extract", "")
            if t:
                title_to_extract[t] = extract
        for original in batch:
            resolved = redirect_map.get(original, original)
            out[original] = title_to_extract.get(resolved, "")
    return out
