# Dataset: Mạng lưới phim điện ảnh & đạo diễn quốc tế — run1

Sinh ra bởi `python -m src.pipeline --target-films 165 --out data/output/run1`.

## Thống kê tổng quan

| Loại | Số lượng |
|---|---|
| Film (node) | 165 |
| Director (node) | 146 |
| Actor (node, top-5 billed/phim) | 676 |
| Studio (node) | 143 |
| AwardEvent (node) | 262 |
| DIRECTED (edge) | 176 |
| ACTED_IN (edge) | 747 |
| PRODUCED_BY (edge) | 233 |
| WON_OR_NOMINATED (edge) | 285 |
| CO_STARRED_WITH (edge, suy ra) | 1,436 |
| COLLABORATED_WITH (edge, suy ra) | 785 |
| **Tổng node** | **1,392** |
| **Tổng edge** | **3,662** |
| **Tổng mẫu (node+edge)** | **5,054** |

## Nguồn hạt giống (10 nguồn, qua 3 kỹ thuật)

| Nguồn | Kỹ thuật | Số dòng có phim/685 tổng |
|---|---|---|
| Oscar – Best Picture | SPARQL (Wikidata P166) | 98 |
| Oscar – Best Director | SPARQL (P166 + qualifier P1686 "for work") | 100 |
| Oscar – Best International Feature | SPARQL | 71 |
| BAFTA – Best Film | SPARQL | 32 |
| Golden Lion (Venice) | SPARQL | 67 |
| Golden Bear (Berlin) | SPARQL | 90 |
| Golden Horse – Best Feature Film (Đài Loan/Hoa ngữ) | SPARQL | 53 |
| Asian Film Award – Best Film | SPARQL | 3 (Wikidata thiếu dữ liệu) |
| Blue Dragon Film Award (Hàn Quốc) | SPARQL | 3 (Wikidata thiếu dữ liệu) |
| National Film Award – Best Feature Film (Ấn Độ) | SPARQL | 62 |
| Palme d'Or (Cannes) | **Quét HTML** bảng "List of winners" trên Wikipedia | 103 |

Text (tóm tắt mở đầu mỗi phim/đạo diễn/diễn viên) lấy qua **MediaWiki Action API** (`prop=extracts`).

## Thuật toán chọn 165/562 phim

1. Giữ toàn bộ phim được ≥2 nguồn giải thưởng khác nhau ghi nhận (phim "hub", quan trọng cho kết nối mạng lưới).
2. Lấp đầy phần còn lại bằng round-robin qua từng nguồn, để không nguồn nào lấn át — đây là cách hiện thực hoá "quota cân bằng khu vực" nêu trong PLAN.md.

## Kiểm tra chất lượng (QA)

- Không trùng lặp QID ở bất kỳ bảng node nào.
- 161/165 phim (97.6%) có đoạn text mở đầu; 165/165 có năm phát hành & quốc gia.
- Trải dài 1920s–2020s (xem phân bố thập niên bên dưới) — hơi dồn vào các năm 2000s do mật độ giải thưởng/dữ liệu Wikidata cao hơn ở phim hiện đại.
- 15+ quốc gia xuất hiện; Hoa Kỳ chiếm ~60% (99/165) do 3/10 nguồn là giải Oscar — **đây là hạn chế cần lưu ý**, xem mục Giới hạn bên dưới.

Phân bố thập niên:
```
1920: 3   1930: 9   1940: 17  1950: 16  1960: 22
1970: 14  1980: 17  1990: 15  2000: 22  2010: 20  2020: 10
```

## Schema file

- `nodes_films.csv`: qid, title, year, country, genre, lead_text
- `nodes_directors.csv` / `nodes_actors.csv`: qid, name, birth_year, nationality, lead_text
- `nodes_studios.csv`: qid, name
- `nodes_events.csv`: event_id, award_key, award_label, year
- `edges.csv`: source, target, relation, weight, context
  - `relation` ∈ {DIRECTED, ACTED_IN, PRODUCED_BY, WON_OR_NOMINATED, CO_STARRED_WITH, COLLABORATED_WITH}
  - `context`: với WON_OR_NOMINATED = film_qid liên quan (nếu subject là người); với CO_STARRED_WITH/COLLABORATED_WITH = danh sách film_qid chung (phân cách `|`)

## Giới hạn đã biết & hướng cải thiện tiếp theo

1. **Thiên lệch Hoa Kỳ (~60%)** — nên bổ sung thêm nguồn giải thưởng ngoài phương Tây (vd San Sebastián, Havana, FESPACO châu Phi, giải điện ảnh Nollywood) để đa dạng hoá khu vực hơn nữa.
2. **Asian Film Award / Blue Dragon** chỉ lấy được 3 dòng mỗi nguồn do Wikidata thiếu statement P166 đầy đủ cho các giải này — cần bổ sung bằng cách quét trực tiếp trang "List of Asian Film Award winners" (kỹ thuật scrape) thay vì chỉ dựa SPARQL.
3. **Thứ tự diễn viên (billing order)** hiện lấy theo thứ tự SPARQL trả về (không đảm bảo đúng thứ tự vai chính thật trên poster) — có thể cải thiện bằng qualifier `P1545` (series ordinal) nếu Wikidata có.
4. **Thời lượng phim (runtime)** chưa được thu thập — plan ban đầu có đề cập, có thể bổ sung dễ dàng qua `P2047`.
5. Dataset hiện ~5.054 mẫu (sát mục tiêu 5.000) với 165 phim; vẫn còn **397 phim khác** chưa dùng (562 tổng - 165 đã chọn) nếu muốn mở rộng thêm.

## Giấy phép & trích dẫn

- Văn bản từ Wikipedia: CC BY-SA 4.0.
- Quan hệ/thuộc tính từ Wikidata: CC0.
- Khi nộp bài, ghi rõ: "Dữ liệu thu thập từ Wikipedia (en.wikipedia.org) và Wikidata (wikidata.org) qua MediaWiki API, Wikidata Query Service, và quét trang danh sách Wikipedia, tháng 10/2026."
