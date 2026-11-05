> ⚠️ **Đã bị thay thế bởi [PLAN_DE5.md](PLAN_DE5.md)** — tài liệu này viết trước khi đọc được
> [SUBJECT.md](SUBJECT.md) (đề bài thật), nên giả định sai số liệu mục tiêu (5.000 mẫu gộp,
> không phải ≥2.000 node/≥5.000 cạnh/≥10 loại quan hệ) và chưa có kỹ thuật NLP/Neo4j đề bài yêu cầu.
> Phần thu thập Wikidata/SPARQL/scrape vẫn hữu ích làm nền, nhưng **làm theo PLAN_DE5.md**.

# Kế hoạch thu thập dữ liệu: Mạng lưới phim điện ảnh, phim truyền hình & đạo diễn quốc tế

**Môn học:** Phân tích phương tiện mạng xã hội (Social Media/Network Analysis)
**Mục tiêu:** Thu thập 5.000 mẫu từ Wikipedia (API + Wikidata + wiki dumps + quét trang danh sách) gồm văn bản, quan hệ giữa các tác nhân, và sự kiện, phục vụ xây dựng mạng lưới (network) để phân tích.

**Các lựa chọn đã chốt với người dùng:**
- Đơn vị "mẫu" = hỗn hợp 3 loại: **thực thể** (node) + **quan hệ** (edge) + **sự kiện** (event-node), cộng gộp thành 5.000.
- Nguồn: **Wikipedia tiếng Anh + Wikidata** (không dùng bản tiếng Việt vì dữ liệu điện ảnh quốc tế quá mỏng).
- Phạm vi chủ đề: **toàn cầu, đa nền điện ảnh** (không giới hạn 1-2 khu vực) để vừa đủ dữ liệu vừa đúng tinh thần "quốc tế".
- Loại quan hệ: **đầy đủ** — đạo diễn-phim, diễn viên-phim, đồng diễn, hãng sản xuất-phim, hợp tác đạo diễn-diễn viên, giải thưởng/đề cử.
- Đầu ra: **CSV/JSONL dạng nodes + edges + events**, dùng được ngay với pandas/NetworkX/Gephi/Neo4j.
- Giai đoạn hiện tại: **chỉ giao văn bản kế hoạch này để duyệt**, chưa dựng code. Timeline: linh hoạt theo mốc công việc, không gắn deadline cứng.

---

## 1. Mô hình dữ liệu (data schema)

### 1.1 Thực thể (nodes)
| Loại | Thuộc tính chính | Nguồn |
|---|---|---|
| `Film` | id (Wikidata QID), tiêu đề, năm phát hành, quốc gia, ngôn ngữ, thể loại, thời lượng, tóm tắt cốt truyện (text) | Infobox phim, Wikidata |
| `Director` | id, tên, năm sinh, quốc tịch, đoạn mở đầu tiểu sử (text) | Infobox người, Wikidata |
| `Actor` | id, tên, năm sinh, quốc tịch, đoạn mở đầu tiểu sử (text) | Infobox người, Wikidata |
| `Studio` (hãng sản xuất/phát hành) | id, tên, quốc gia, năm thành lập | Infobox phim, Wikidata |
| `AwardEvent` | id, tên giải/LHP, năm/kỳ tổ chức, hạng mục | Trang "List of … award winners" |

### 1.2 Quan hệ (edges)
- `DIRECTED(director → film)`
- `ACTED_IN(actor → film, thứ tự vai diễn)`
- `CO_STARRED_WITH(actor ↔ actor, qua film)` — suy ra từ `ACTED_IN`
- `PRODUCED_BY(film → studio)`
- `COLLABORATED_WITH(director ↔ actor, trọng số = số phim chung)` — suy ra
- `WON / NOMINATED(film|director|actor → AwardEvent, hạng mục)`

### 1.3 Văn bản
Mỗi node phim/đạo diễn/diễn viên giữ lại đoạn tóm tắt đầu bài (lead section) để phục vụ phân tích văn bản (topic modeling, NER, so sánh mô tả giữa các vùng điện ảnh) — đáp ứng yêu cầu "thu thập văn bản" song song với quan hệ và sự kiện.

---

## 2. Phạm vi lựa chọn dữ liệu (để vừa đủ phong phú, vừa khả thi)

Thay vì duyệt toàn bộ danh mục phim (quá lớn, nhiễu), **hạt giống (seed)** được lấy từ các **danh sách giải thưởng/liên hoan phim quốc tế lớn**, giai đoạn **1950–2025**, trải đều các khu vực:

- Giải Oscar (Best Picture, Best Director, Best International Feature)
- Cannes (Palme d'Or + danh sách tranh giải một số năm)
- Venice (Golden Lion), Berlin (Golden Bear)
- BAFTA, Césars (Pháp), Goya (Tây Ban Nha)
- Giải điện ảnh châu Á: Giải Điện ảnh châu Á, Rồng Xanh (Hàn Quốc), Kim Mã (Đài Loan/Hoa ngữ), Viện Hàn lâm Nhật Bản
- (Tuỳ bổ sung) Sundance, giải truyền hình quốc tế (Emmy quốc tế, International Emmy) để có thêm phim truyền hình đúng tên chủ đề

**Quota cân bằng khu vực** (tránh thiên lệch Hollywood): Bắc Mỹ ~35%, Châu Âu ~25%, Châu Á ~25%, còn lại (Mỹ Latinh/Trung Đông/Châu Phi/Châu Đại Dương) ~15%.

### Ước tính số lượng (sẽ hiệu chỉnh sau pilot — xem mục 4)

| Thành phần | Ước tính | Loại |
|---|---|---|
| Phim | 900 – 1.200 | node |
| Đạo diễn | 400 – 600 | node |
| Diễn viên (top-billed, tối đa 3-5/phim) | 900 – 1.200 | node |
| Hãng sản xuất | 150 – 250 | node |
| Sự kiện giải thưởng/LHP (theo kỳ) | 150 – 250 | event-node |
| DIRECTED | 900 – 1.200 | edge |
| PRODUCED_BY | 900 – 1.200 | edge |
| WON/NOMINATED | 1.500 – 2.500 | edge |
| ACTED_IN | 2.500 – 3.500 | edge |

→ Tổng ước tính **vượt 5.000 khá nhiều** (dư địa an toàn). Ở bước chốt dataset cuối (giai đoạn 4), sẽ **ưu tiên giữ toàn bộ thực thể + quan hệ cốt lõi** (DIRECTED, PRODUCED_BY, WON/NOMINATED) rồi **lấy mẫu có kiểm soát** phần `ACTED_IN` để đúng 5.000 — đảm bảo mỗi node có ít nhất 1 cạnh (không cắt ngẫu nhiên làm rã mạng lưới).

---

## 3. Phương pháp thu thập — đúng 3 kỹ thuật yêu cầu (quét / API / wiki dumps)

| Kỹ thuật | Dùng để làm gì | Công cụ |
|---|---|---|
| **API** (MediaWiki Action API + Wikidata Query Service/SPARQL) | Tạo seed list có cấu trúc (vd: SPARQL lấy toàn bộ người có occupation = đạo diễn phim, có ≥1 phim trên Wikidata); lấy tóm tắt, extract text, categories cho từng trang theo QID | `requests`, `SPARQLWrapper`, thư viện `wikipedia`/`pywikibot` |
| **Wiki dumps** | Trích xuất hàng loạt infobox phim/người (đạo diễn, diễn viên, hãng phim, giải thưởng) ở quy mô lớn, không bị giới hạn tốc độ của API; hoặc dùng Wikidata JSON dump để lấy quan hệ dạng triple có sẵn, đáng tin cậy hơn tự parse | `mwxml`, `mwparserfromhell`, `WikiExtractor`, hoặc Wikidata dump (JSON/TTL) lọc theo entity type |
| **Quét (crawl có kiểm soát)** | Lấy các trang "danh sách" (List of Academy Award for Best Director winners, List of Cannes Palme d'Or winners…) mà API/dump không có sẵn dưới dạng gọn — đây là nguồn chính cho **sự kiện** | `requests` + `BeautifulSoup`/`pandas.read_html`, tuân thủ `robots.txt`, rate limit, User-Agent định danh rõ ràng (mục đích học thuật) |

Ba kỹ thuật bổ trợ nhau: **API/Wikidata** dựng seed & quan hệ chuẩn; **dump** quét hàng loạt infobox; **crawl** lấy bảng sự kiện/giải thưởng.

---

## 4. Quy trình thực hiện (các giai đoạn)

0. **Pilot (kiểm chứng khả thi)** — chạy thử toàn bộ pipeline trên quy mô nhỏ (~100–150 mẫu, ví dụ chỉ Oscar Best Picture 2015–2024) để xác nhận API/dump/crawl hoạt động đúng, đo tốc độ và tỷ lệ thiếu dữ liệu thực tế → **hiệu chỉnh lại ước tính ở mục 2** trước khi scale lên 5.000.
1. **Seed & thiết kế cuối** — chốt danh sách giải thưởng/LHP cần lấy, chốt schema cuối.
2. **Thu thập hàng loạt** — chạy song song API + dump + crawl theo từng nguồn giải thưởng, lưu dữ liệu thô.
3. **Trích xuất & chuẩn hoá quan hệ** — parse infobox, dựng bảng edges, khử trùng lặp theo Wikidata QID (hợp nhất dữ liệu từ 3 nguồn).
4. **Làm sạch & cân bằng** — loại phim thiếu thông tin tối thiểu, kiểm tra quota vùng/thời gian, cắt về đúng 5.000 mẫu theo nguyên tắc ưu tiên ở mục 2.
5. **Xuất dataset** — `nodes.csv`, `edges.csv`, `events.csv` + `README.md` (data dictionary, nguồn, giấy phép).
6. **(Tuỳ chọn) Phân tích minh hoạ nhanh** — load vào NetworkX, tính thử degree/betweenness/community để chứng minh dataset dùng được, phục vụ phần đánh giá hữu dụng trong báo cáo.

*(Theo yêu cầu hiện tại, chỉ dừng ở việc lập kế hoạch — các giai đoạn trên sẽ triển khai bằng code sau khi plan được duyệt.)*

---

## 5. Rủi ro & lưu ý

- **Dump tiếng Anh đầy đủ rất nặng** (~20GB nén). Giải pháp: dùng Wikidata Query Service để lấy danh sách trang liên quan trước, chỉ fetch đúng tập đó qua API; dump chỉ cần cho phần "trích xuất hàng loạt" theo yêu cầu kỹ thuật, có thể dùng dump Wikidata (nhỏ, có thể lọc theo entity type) thay vì dump Wikipedia đầy đủ.
- **Rate limit khi crawl**: tuân thủ robots.txt, đặt delay, ưu tiên API/dump hơn crawl trực tiếp từng trang phim.
- **Giấy phép**: nội dung Wikipedia theo CC BY-SA 4.0, Wikidata theo CC0 — cần ghi nguồn & license rõ trong README khi nộp bài.
- **Nếu sau pilot vẫn không đủ 5.000 mẫu chất lượng**, xem phương án dự phòng ở mục 7.

---

## 6. Đánh giá tính hữu dụng của chủ đề

**Trong bối cảnh môn Phân tích phương tiện mạng xã hội:**
- Đây là một **mạng lưới hợp tác/affiliation network** (không phải dữ liệu tương tác người dùng thật như like/share/follow), nhưng rất phù hợp để minh hoạ các khái niệm cốt lõi của phân tích mạng: xây mạng từ dữ liệu phi cấu trúc, phép chiếu bipartite (diễn viên–phim → mạng diễn viên–diễn viên), các độ đo trung tâm (degree/betweenness/eigenvector centrality để tìm "ngôi sao kết nối"), phát hiện cộng đồng (cụm hợp tác theo quốc gia/trường phái điện ảnh), hiệu ứng "thế giới nhỏ" (tương tự bài toán Bacon Number nổi tiếng, mở rộng ở quy mô quốc tế), phân tích mạng theo thời gian (1950–2025), tính đồng dạng/homophily (đạo diễn có xu hướng hợp tác lại với cùng ê-kíp/quốc gia).
- **Hạn chế cần lưu ý**: không chứa dữ liệu hành vi mạng xã hội thực (post, bình luận, tương tác người dùng). Nên làm rõ trong báo cáo đây là "social network" theo nghĩa khoa học mạng (graph quan hệ xã hội), không phải "social media" theo nghĩa nền tảng — nên đối chiếu lại với rubric/yêu cầu cụ thể của giảng viên để chắc chắn phù hợp.

**Trong thực tiễn nói chung:** loại mạng lưới hợp tác này được dùng thật trong hệ gợi ý phim (recommendation), phân tích ngành công nghiệp giải trí (dự đoán thành công dựa trên mạng lưới ê-kíp), phân tích ảnh hưởng/danh tiếng, và nghiên cứu bất bình đẳng mạng lưới (ai luôn ở trung tâm, thiên lệch giới tính/quốc gia trong điện ảnh quốc tế).

---

## 7. Phương án dự phòng (nếu chủ đề chính thiếu dữ liệu)

1. **Mạng lưới giải Nobel** — người đoạt giải, đề cử, viện/trường liên kết; Wikidata có SPARQL rất mạnh, cực kỳ structured.
2. **Mạng lưới chuyển nhượng cầu thủ bóng đá quốc tế** — dữ liệu rất lớn, sự kiện chuyển nhượng rõ theo mùa giải.
3. **Mạng lưới nghệ sĩ âm nhạc quốc tế** — hợp tác, hãng đĩa, giải Grammy; cấu trúc tương tự chủ đề điện ảnh.
4. **Mạng lưới đồng tác giả khoa học** (co-authorship, qua Wikidata "educated at"/"doctoral advisor") — kinh điển trong SNA học thuật.

---

## 8. Ý tưởng đột phá / mở rộng (tuỳ chọn, không bắt buộc)

1. **Đối chiếu hai loại mạng**: bổ sung dữ liệu thật từ Twitter/X hoặc Reddit về các phim/đạo diễn trong tập dữ liệu, so sánh "mạng tri thức" (Wikipedia) với "mạng dư luận" (social media buzz thật).
2. **Phân tích động theo thời gian**: dựng mạng theo từng thập niên để quan sát dịch chuyển trung tâm quyền lực điện ảnh (Hollywood → toàn cầu hoá, làn sóng điện ảnh châu Á hậu *Parasite* 2020, ảnh hưởng của streaming).
3. **Phân tích thiên lệch/công bằng (bias & fairness)**: đo mức đại diện giới tính/quốc gia ở vị trí trung tâm mạng lưới — góc tiếp cận xã hội học, thời sự, tạo điểm nhấn khác biệt.
4. **Dự đoán liên kết (link prediction) bằng Graph ML**: huấn luyện mô hình dự đoán hợp tác tương lai hoặc khả năng đoạt giải dựa trên vị trí mạng lưới của ê-kíp.
5. **Knowledge graph + LLM (Graph RAG)**: xây chatbot tra cứu mạng lưới điện ảnh, trả lời kiểu "đạo diễn nào nối Scorsese và Bong Joon-ho qua ít bước nhất" — minh hoạ ứng dụng network + AI hiện đại.

---

## 9. Việc cần duyệt

Xin phản hồi về:
- Ước tính số lượng ở mục 2 (có cần điều chỉnh tỷ lệ loại nào không?).
- Danh sách giải thưởng/LHP nguồn ở mục 2 (thêm/bớt nguồn nào?).
- Có muốn thêm hẳn phim truyền hình (series) làm một loại node riêng, hay chỉ coi phim điện ảnh là trọng tâm, truyền hình là phụ?
- Sau khi duyệt, triển khai: viết code thu thập theo đúng 4 giai đoạn ở mục 4.
