# Thu thập mạng lưới phim điện ảnh, phim truyền hình & đạo diễn quốc tế (Wikipedia/Wikidata)

Dự án cho môn Phân tích phương tiện mạng xã hội — xem kế hoạch gốc tại [PLAN.md](PLAN.md).

## Cài đặt

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Chạy thu thập dữ liệu

```bash
# Pilot nhanh (kiểm chứng pipeline, ~50 phim)
python3 -m src.pipeline --pilot --film-limit 50 --out data/output/pilot

# Chạy đầy đủ, tự chọn N phim theo thuật toán cân bằng nguồn/khu vực
python3 -m src.pipeline --target-films 165 --out data/output/run1
```

Kết quả nằm trong `data/output/<tên>/`: `nodes_films.csv`, `nodes_directors.csv`,
`nodes_actors.csv`, `nodes_studios.csv`, `nodes_events.csv`, `edges.csv`.
Xem [data/output/run1/README.md](data/output/run1/README.md) để biết schema chi tiết,
thống kê chất lượng (QA) và giới hạn đã biết của lần chạy hiện tại (~5.054 mẫu, sát mục tiêu 5.000).

## Cấu trúc mã nguồn

- `src/config.py` — danh sách giải thưởng/liên hoan phim dùng làm hạt giống, tham số chung.
- `src/http_utils.py` — session HTTP có retry + giãn cách lịch sự (rate limit).
- `src/wikidata_client.py` — truy vấn SPARQL tới Wikidata (giải thưởng, đạo diễn, diễn viên, hãng phim...).
- `src/wiki_api_client.py` — gọi MediaWiki Action API (đoạn text mở đầu bài, tra QID theo tiêu đề có xử lý redirect).
- `src/scrape_awardlists.py` + `src/html_table_utils.py` — quét bảng HTML trang "List of ..." (vd Palme d'Or) khi Wikidata không có sẵn đủ cấu trúc.
- `src/pipeline.py` — orchestrator: thu thập hạt giống → enrich quan hệ → xuất CSV.

Ba kỹ thuật thu thập theo yêu cầu đề bài (API, quét, wiki dump) được dùng đúng vai trò:
**SPARQL/API** cho quan hệ có cấu trúc, **quét HTML** cho các danh sách giải thưởng Wikidata
chưa phủ đủ, còn **wiki dump** (offline, quy mô lớn) là hướng mở rộng tiếp theo khi cần vượt
giới hạn tốc độ của API — xem mục "Bước tiếp theo" trong PLAN.md.
