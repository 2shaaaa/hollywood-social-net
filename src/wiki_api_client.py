"""MediaWiki Action API client (English Wikipedia): fetches the lead (intro) text by title."""
import mwparserfromhell

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


def fetch_infobox_starring(session, titles: list[str], batch_size: int = 20) -> dict[str, list[str]]:
    """{film page title: [page titles linked in its `Infobox film` `starring` field, in order]}.
    That field lists the credited leads in poster billing order — what Wikidata's P161 can't give
    (no billing order, and it also lists uncredited extras)."""
    out = {}
    for batch in _chunks(titles, batch_size):
        params = {
            "action": "query",
            "prop": "revisions",
            "rvprop": "content",
            "rvslots": "main",
            "redirects": 1,
            "titles": "|".join(batch),
            "format": "json",
            "formatversion": 2,
        }
        while True:  # large pages can spill into a continuation response
            data = get_json(session, API_URL, params=params)
            query = data.get("query", {})
            redirect_map = {r["to"]: r["from"] for r in query.get("redirects", [])}
            for page in query.get("pages", []):
                revisions = page.get("revisions")
                if not revisions:
                    continue
                starring = []
                for tpl in mwparserfromhell.parse(revisions[0]["slots"]["main"]["content"]).filter_templates():
                    if tpl.name.strip().lower().startswith("infobox film") and tpl.has("starring"):
                        for link in tpl.get("starring").value.filter_wikilinks():
                            t = str(link.title).split("#")[0].strip()
                            if t and t not in starring:
                                starring.append(t)
                        break
                out[redirect_map.get(page["title"], page["title"])] = starring
            if "continue" not in data:
                break
            params = {**params, **data["continue"]}
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
