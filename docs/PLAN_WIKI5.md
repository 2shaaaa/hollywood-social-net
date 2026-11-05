# Kế hoạch triển khai Đề 5 — Mạng lưới diễn viên & đạo diễn Hollywood

Thay thế định hướng cũ ở [PLAN.md](../PLAN.md) (viết trước khi đọc được [SUBJECT.md](SUBJECT.md)).
Tài liệu này đối chiếu đúng yêu cầu đề bài thật và vạch lộ trình 8 ngày (hạn nộp **23:59 11/11/2026**,
hôm nay 03/11/2026).

## 0. Các quyết định đã chốt

| Vấn đề | Quyết định |
|---|---|
| Phạm vi | **Hollywood/Mỹ** (tận dụng ngoại lệ "đề quốc tế được thu hẹp phạm vi") |
| Hệ quản trị CSDL đồ thị | **Neo4j** — có GDS library tính centrality/community detection sẵn cho bài cuối kỳ, Cypher dễ học, driver Python tốt |
| Vai trò | Làm một mình toàn bộ pipeline (thu thập → NLP → nạp Neo4j → báo cáo) |
| Kỹ thuật NLP cho 2 cạnh mới | **spaCy** (NER + dependency parsing), không dùng LLM để tránh rủi ro "không tính là NLP tự làm" |

## 1. Vì sao dữ liệu hiện tại (run1) chưa đạt

| Yêu cầu đề bài | run1 hiện tại | Khoảng cách |
|---|---|---|
| ≥1.000 node (phạm vi thu hẹp) | 1.392 node, nhưng chỉ **99/165 phim là Mỹ (60%)** | Cần thu thập thêm phim/người Mỹ, lọc bỏ phần quốc tế không cần nữa |
| ≥5.000 cạnh | 3.662 cạnh | Thiếu ~1.400+ cạnh |
| ≥10 loại quan hệ chi tiết | 6 loại | Thiếu ≥4 loại |
| Đúng 3 cạnh đề 5 nêu tên | Chỉ có `COLLABORATED_WITH` ≈ "Hợp tác thường xuyên"; **chưa có** "Đại diện thương mại", "Xung đột/Thay thế vai diễn" | Thiếu 2/3, và đây là phần **NLP thật** đề bài muốn thấy |
| Kỹ thuật NLP trên văn bản | 0% — toàn bộ lấy từ Wikidata SPARQL (structured) | Lệch hướng kỹ thuật cốt lõi của đề |
| Neo4j/ArangoDB/... | Chưa có, chỉ có CSV phẳng | Chưa làm |
| Báo cáo ≥10 trang | Chưa có | Chưa làm |

**Điểm mấu chốt cần nhớ**: ghi chú cuối SUBJECT.md nói "chất lượng mạng ≥90% **chưa** đánh giá ở bước nộp 11/11, sẽ đánh giá ở bài cuối kỳ". Vậy mục tiêu lần nộp này là: **đạt đủ số lượng + đủ 10 loại quan hệ + nạp được vào Neo4j + viết báo cáo** — độ chính xác NLP có thể chưa hoàn hảo, miễn minh bạch nêu rõ trong báo cáo (mục "chưa đạt được").

## 2. Schema mới cho Đề 5

### Node
| Loại | Nguồn | Ghi chú |
|---|---|---|
| `Film` | Wikidata (country=US) | Mở rộng từ 99 → mục tiêu ~1.200-1.500 phim Mỹ |
| `Director` | Wikidata | |
| `Actor` | Wikidata | |
| `Studio` (hãng sản xuất) | Wikidata P272 | |
| `Agency` (hãng quản lý tài năng) | **MỚI** — danh sách cố định (CAA, WME, UTA, ICM Partners, Paradigm, Gersh, APA, Independent Artist Group, Verve...) + NLP phát hiện trong text | |
| `AwardEvent` | Wikidata + giải Mỹ | Đổi seed sang giải mang tính Hollywood |

### Edge — đủ 10+ loại, chia 2 nhóm

**A. Structured (từ Wikidata, mở rộng từ 6 loại hiện có, lấy nhanh)**
1. `DIRECTED` (đã có)
2. `ACTED_IN` (đã có)
3. `PRODUCED_BY` (đã có)
4. `WON_AWARD` — tách từ `WON_OR_NOMINATED` cũ (P166)
5. `NOMINATED_FOR` — tách riêng, lấy thêm qua P1411 "nominated for" (trước đây bỏ qua)
6. `CO_STARRED_WITH` (đã có, suy ra)
7. `COLLABORATED_WITH` — **chính là "Hợp tác thường xuyên"** đề 5 yêu cầu (đạo diễn hay chọn diễn viên nào) — đã có, giữ nguyên nhưng áp ngưỡng weight≥2 để đúng nghĩa "thường xuyên"
8. `DISTRIBUTED_BY` — hãng phát hành (P750), khác hãng sản xuất
9. `BASED_ON` — phim dựa trên tác phẩm khác (P144), bổ sung ý nghĩa mạng

**B. NLP-derived (trích xuất từ văn bản bằng spaCy — đúng trọng tâm đề bài)**
10. `REPRESENTED_BY` — **"Đại diện thương mại"**: NER nhận diện ORG trùng danh sách agency + dependency parse tìm cụm động từ "sign/represent/client of" gần tên agency trong bio diễn viên/đạo diễn
11. `REPLACED_IN_ROLE` — **"Xung đột/Thay thế vai diễn"**: quét mục "Production"/"Casting" của bài phim, tìm pattern "replaced by / recast / dropped out / fired from / departed" + 2 thực thể PERSON (người bị thay, người thay thế), gắn vào film liên quan

→ Đủ **11 loại quan hệ chi tiết**, dư so với yêu cầu 10.

## 3. Chiến lược mở rộng dữ liệu Hollywood (để bù phần "60% Mỹ")

Đổi seed giải thưởng từ các giải quốc tế/châu Âu/châu Á (Cannes, Venice, Berlin, Golden Horse...)
sang **giải mang tính Hollywood**, dùng Wikidata SPARQL như cũ (đã có hạ tầng `fetch_award_subjects`):

- Golden Globe Awards (phim + truyền hình)
- Screen Actors Guild (SAG) Awards
- Critics' Choice Awards
- Directors Guild of America (DGA) Award
- Producers Guild of America (PGA) Award
- Primetime Emmy Award (mở rộng sang **phim truyền hình** — đúng tên đề bài gốc "diễn viên/đạo diễn" không giới hạn điện ảnh)
- Giữ lại Oscar/BAFTA (BAFTA vẫn trao nhiều cho phim Mỹ)

Nếu vẫn chưa đủ ~1.200-1.500 phim Mỹ: nới thêm bằng truy vấn Wikidata "phim Mỹ có ngân sách phòng vé
(P2142) ghi nhận" (proxy cho độ nổi tiếng) thay vì chỉ dựa giải thưởng.

## 4. Thiết lập Neo4j

1. Cài Neo4j Desktop (hoặc Docker: `docker run -p7474:7474 -p7687:7687 neo4j:5`) — có GDS + APOC plugin.
2. Viết script `src/load_neo4j.py` dùng driver `neo4j` (Python) để:
   - Tạo constraint unique theo `qid`/`event_id`/`agency_id` cho từng label.
   - Nạp node theo batch (`UNWIND $rows AS row MERGE (n:Film {qid: row.qid}) SET n += row`).
   - Nạp edge theo batch tương tự với `MATCH ... MERGE ... -[r:RELATION]->...`.
3. Query mẫu cho báo cáo: top-10 đạo diễn theo degree, số thành phần liên thông
   (`CALL gds.wcc.stream(...)`), vài node trung tâm nhất (`CALL gds.betweenness.stream(...)`).

## 4b. Giai đoạn phân tích mạng (sau khi nạp Neo4j)

Dùng **thư viện** cho cả 2 bước, không tự viết thuật toán, không dùng LLM:

1. **NetworkX** (Python, đọc trực tiếp từ CSV) — dùng để kiểm tra nhanh trong lúc phát triển:
   degree distribution, số thành phần liên thông, vài centrality cơ bản — không cần chờ Neo4j dựng xong.
2. **Neo4j Graph Data Science (GDS)** — bản chính thức đưa vào báo cáo, chạy ngay trên DB đã nạp:
   - `CALL gds.graph.project(...)` tạo in-memory graph projection
   - `CALL gds.degree.stream(...)` / `CALL gds.betweenness.stream(...)` — tìm node trung tâm (đạo diễn/diễn viên "hub")
   - `CALL gds.louvain.stream(...)` hoặc `gds.wcc.stream(...)` — community detection / connected components (đạo diễn-diễn viên tụ theo studio/thập niên nào)
   - Kết quả này đi thẳng vào mục "Các thống kê về mạng đã xây dựng được" của báo cáo.

## 5. Lịch 8 ngày (03/11 → 11/11)

| Ngày | Việc |
|---|---|
| T3 03/11 (hôm nay) | Duyệt kế hoạch này; đổi seed sang giải Hollywood; chạy lại pipeline mở rộng phim Mỹ |
| T4 04/11 | Hoàn tất thu thập structured (đủ node/edge mục tiêu), tách WON/NOMINATED, thêm DISTRIBUTED_BY/BASED_ON |
| T5 05/11 | Cài spaCy, viết + test extractor `REPLACED_IN_ROLE` trên vài case nổi tiếng đã biết (Justice League, All the Money in the World...) |
| T6 06/11 | Viết + test extractor `REPRESENTED_BY` (NER + gazetteer agency), bổ sung thủ công nếu yield quá thấp |
| T7 07/11 | Gộp toàn bộ, chạy full pipeline, QA số lượng (≥1.000 node/≥5.000 cạnh/≥10 loại) |
| CN 08/11 | Cài Neo4j, viết `load_neo4j.py`, nạp dữ liệu, chạy thử query |
| T2 09/11 | Tính thống kê mạng (degree, component, community) cho báo cáo + vẽ biểu đồ |
| T3 10/11 | Viết báo cáo 10 trang (đủ mục theo SUBJECT.md), dọn GitHub repo, push |
| T4 11/11 sáng | Buffer rà soát trước 23:59 |

Nếu bị trễ tiến độ, **ưu tiên cắt giảm theo thứ tự**: (1) giảm độ phức tạp `REPRESENTED_BY` (chỉ cần
vài chục cạnh, bổ sung thủ công cũng được), (2) bỏ qua community detection trong báo cáo (chỉ cần
thống kê cơ bản), (3) không cắt số node/edge/loại quan hệ bắt buộc — đây là điều kiện cứng của đề.

## 6. Rủi ro

- **`REPRESENTED_BY` từ Wikipedia có thể cho yield rất thấp** vì bài tiểu sử ít khi ghi rõ "ký hợp đồng với CAA" — xử lý bằng cách bổ sung một bảng nhỏ thủ công (có trích dẫn nguồn báo chí công khai) nếu NLP tự động không đủ, nêu rõ trong báo cáo đây là hybrid NLP + curation.
- **Ranh giới "cắt cạnh có cần giảm theo tỷ lệ node không"** khi thu hẹp phạm vi — đề bài không nói rõ; quyết định an toàn: vẫn nhắm ≥5.000 cạnh đầy đủ để không bị trừ điểm nếu giám khảo chấm theo yêu cầu chung.
- **spaCy model tiếng Anh** (`en_core_web_sm` hoặc `en_core_web_trf` cho độ chính xác cao hơn nhưng chậm hơn) — cần cài thêm, chưa có trong `requirements.txt`.

## 7. Quyết định cuối (đã chốt để bắt đầu code — 05/11)

1. Schema 11 loại quan hệ ở mục 2: **giữ nguyên**, không mở rộng thêm node `Distributor`/`Role`/`Franchise`/`Genre-node`
   đã thảo luận — để tránh phình phạm vi khi chỉ còn ~6 ngày; ghi lại ở đây như hướng mở rộng cho bài
   cuối kỳ sau này nếu còn thời gian.
2. Danh sách giải thưởng Hollywood ở mục 3: **giữ nguyên**, không thêm Tony (sân khấu ngoài phạm vi
   điện ảnh/truyền hình của đề 5).
3. Neo4j: **Docker** (`docker run -p7474:7474 -p7687:7687 ... neo4j:5-enterprise` hoặc community +
   GDS plugin) — kiểm tra máy có Docker trước khi chạy bước 4.

### Lịch thực tế đã trễ 2 ngày so với kế hoạch gốc — dồn lại từ hôm nay (05/11, còn 6 ngày)

| Hôm nay 05/11 | Đổi seed Hollywood + mở rộng relation type (gộp việc của 03-04/11 cũ) |
|---|---|
| 06/11 | spaCy: extractor `REPLACED_IN_ROLE` |
| 07/11 | spaCy: extractor `REPRESENTED_BY` |
| 08/11 | Gộp, chạy full pipeline, QA số lượng |
| 09/11 | Neo4j (Docker) + load script + NetworkX/GDS stats |
| 10/11 | Viết báo cáo 10 trang, dọn GitHub, push |
| 11/11 sáng | Buffer |
