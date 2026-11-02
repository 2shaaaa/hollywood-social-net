"""Tiện ích làm phẳng bảng HTML wikitable có rowspan/colspan (để quét các trang 'List of ...')."""


def flatten_table_rows(table_soup, skip_header_rows: int = 1) -> list[list[dict]]:
    """Trả về list các dòng, mỗi dòng là list ô {text, hrefs} đã căn đúng cột (xử lý rowspan/colspan)."""
    trs = table_soup.find_all("tr")[skip_header_rows:]
    active: dict[int, list] = {}  # col_idx -> [cell_dict, remaining_rowspan]
    rows_out = []
    for tr in trs:
        raw_cells = tr.find_all(["td", "th"])
        cell_queue = list(raw_cells)
        row_out = []
        col_idx = 0
        while cell_queue or any(v[1] > 0 for v in active.values() if True):
            if col_idx in active and active[col_idx][1] > 0:
                row_out.append(active[col_idx][0])
                active[col_idx][1] -= 1
                if active[col_idx][1] == 0:
                    del active[col_idx]
                col_idx += 1
                continue
            if not cell_queue:
                break
            cell = cell_queue.pop(0)
            text = cell.get_text(" ", strip=True)
            hrefs = [
                {"href": a.get("href"), "title": a.get("title"), "text": a.get_text(strip=True)}
                for a in cell.find_all("a")
                if a.get("href", "").startswith("/wiki/")
            ]
            cell_data = {"text": text, "hrefs": hrefs}
            colspan = int(cell.get("colspan", 1) or 1)
            rowspan = int(cell.get("rowspan", 1) or 1)
            for _ in range(colspan):
                row_out.append(cell_data)
                if rowspan > 1:
                    active[col_idx] = [cell_data, rowspan - 1]
                col_idx += 1
        rows_out.append(row_out)
    return rows_out
