"""Client gọi MediaWiki Action API (Wikipedia tiếng Anh): lấy đoạn text mở đầu (lead) theo tiêu đề."""
from .http_utils import get_json

API_URL = "https://en.wikipedia.org/w/api.php"


def _chunks(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def resolve_qids_for_titles(session, titles: list[str], batch_size: int = 50) -> dict[str, str]:
    """Tra QID Wikidata theo tiêu đề bài Wikipedia tiếng Anh, tự xử lý trang đổi hướng (redirect)
    qua pageprops.wikibase_item — tránh lỗi khi tiêu đề lấy từ wikilink là một redirect
    (vd 'Bong Joon-ho' redirect sang 'Bong Joon Ho')."""
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
    """Trả về {title: đoạn text mở đầu bài}. Dùng redirects=1 để xử lý trang đổi hướng."""
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
        # map redirect gốc -> tiêu đề đích để không mất liên kết
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
