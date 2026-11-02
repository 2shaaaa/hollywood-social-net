# Đề bài tập cuối kỳ

**Xây dựng mạng xã hội dựa trên kỹ thuật phân tích xử lý ngôn ngữ tự nhiên theo danh sách các đề tài được phân công theo nhóm ở dưới.**

## Yêu cầu chung

- Mạng tối thiểu 2000 nghìn nút, 5000 cạnh và 10 loại quan hệ chi tiết giữa các cạnh, độ chính xác trên 90%.
- Các đề tài liên quan Quốc tế có thể lựa chọn một phạm vi nhỏ hơn (ví dụ cầu thủ có thể chọn chỉ ngoại hạng Anh); các phạm vi nhỏ tối thiểu 1000 nút.
- Ưu tiên tạo ra mạng chất lượng (node và cạnh có ý nghĩa cụ thể, rõ ràng, ví dụ mối quan hệ giữa các diễn viên thông qua các bộ phim hay mối quan hệ giữa các cầu thủ thông qua danh sách đội bóng hoặc mối quan hệ HLV).
- Dữ liệu sử dụng là Wikipedia tiếng Anh/Việt, các bài báo tiếng Anh/Việt, dữ liệu bài báo khoa học tại các trang như Google Scholar, PubMed, arXiv.

## Yêu cầu kỹ thuật

Các nhóm lưu trữ dữ liệu graph vào một trong các hệ quản trị CSDL sau:

- Neo4j
- ElasticSearch/OpenSearch
- ArrangoDB
- Dgraph

Các nhóm có thể đề xuất riêng một hệ quản trị CSDL phù hợp; việc lựa chọn cần đánh giá khả năng chạy các thuật toán cho bài tập cuối kỳ.

## Kết quả báo cáo

Một báo cáo tối thiểu 10 trang bao gồm các nội dung:

- Phân công công việc trong nhóm.
- Giới thiệu về mạng đã xây dựng được, lựa chọn node thế nào và lựa chọn cạnh ra sao.
- Giới thiệu stack công nghệ sử dụng để thu thập, xử lý dữ liệu Wikipedia.
- Các bước tiền xử lý dữ liệu.
- Các thống kê về mạng đã xây dựng được.
- Kết luận về các vấn đề đạt được và chưa đạt được.
- Link GitHub code xử lý.

## Thời hạn nộp

Thời gian nộp bài trước **23h59p 11/11/2026** (chất lượng của mạng >=90% chưa đánh giá tại bước này mà sẽ đánh giá vào bài tập cuối kỳ).

## Danh sách đề tài

Dưới đây là 35 đề tài được đánh số liên tục từ 1 đến 35 (Phần 1: 16 đề tài, Phần 2: 10 đề tài, Phần 3: 9 đề tài).

## PHẦN 1: DỮ LIỆU WIKIPEDIA

1. **Mạng lưới các nhà khoa học Quốc tế:** Khai thác Infobox và phân tích nội dung mục "Scientific Career" và "Controversies" trên Wikipedia tiếng Anh để xây dựng đồ thị đa quan hệ: Kế thừa học thuật (phát triển dựa trên lý thuyết của ai), Tranh luận/Phản biện khoa học (bác bỏ công trình của nhà khoa học nào), và Cố vấn tại các viện nghiên cứu quốc tế.
2. **Mạng lưới các nhạc sĩ và ca sĩ Việt Nam:** Sử dụng Infobox (dòng nhạc, hãng đĩa) kết hợp phân tích văn bản mục "Sự nghiệp âm nhạc" để phân loại các cạnh: Sáng tác độc quyền (nhạc sĩ A viết riêng cho ca sĩ B), Hợp tác biểu diễn (song ca, lập nhóm nhạc), Trực thuộc quản lý (ký/chấm dứt hợp đồng với công ty giải trí), và Thầy - Trò trong các cuộc thi âm nhạc.
3. **Mạng lưới các nhạc sĩ và ca sĩ Quốc tế:** Phân tích văn bản mục "Musical style and influences" và "Career" kết hợp Infobox để xây dựng đồ thị: Truyền cảm hứng (nghệ sĩ A chịu ảnh hưởng phong cách từ nghệ sĩ B), Hợp tác sản xuất (Producer - Ca sĩ), Tranh chấp bản quyền với hãng thu âm, hoặc Tách nhóm hoạt động solo.
4. **Mạng lưới các diễn viên và đạo diễn Việt Nam:** Khai thác Infobox và đọc hiểu văn bản mục "Sự nghiệp điện ảnh/Sân khấu" để trích xuất quan hệ giữa Diễn viên, Đạo diễn, Nhà sản xuất và Hãng phim/Nhà hát: phân biệt rõ cạnh Đạo diễn chỉ đạo, Diễn viên đóng cặp ăn ý, hay Người nâng đỡ/Phát hiện tài năng.
5. **Mạng lưới các diễn viên và đạo diễn Quốc tế:** Phân tích nội dung các bài viết về nghệ sĩ, đạo diễn và hãng phim Hollywood/Quốc tế để phân loại cạnh: Hợp tác thường xuyên (đạo diễn A luôn chọn diễn viên B), Đại diện thương mại (ký hợp đồng với các công ty quản lý tài năng như CAA, WME), hoặc Xung đột/Thay thế vai diễn trong quá trình làm phim.
6. **Mạng lưới các cầu thủ và huấn luyện viên Việt Nam:** Kết hợp lịch sử câu lạc bộ trong Infobox với việc phân tích văn bản mục "Sự nghiệp câu lạc bộ & Quốc gia" để xác định loại cạnh: Phát hiện/Đào tạo trẻ (HLV nào đôn cầu thủ lên đội 1), Chuyển nhượng/Cho mượn giữa các CLB V-League, và Triệu tập/Trọng dụng dưới các thời kỳ HLV trưởng đội tuyển.
7. **Mạng lưới các cầu thủ và huấn luyện viên Quốc tế:** Phân tích sâu văn bản tiểu sử cầu thủ/HLV bóng đá thế giới để trích xuất các cạnh mang ý nghĩa chiến thuật và thương mại: Kế thừa chiến thuật (HLV A từng làm trợ lý cho HLV B), Môi giới chuyển nhượng (quan hệ với các Siêu cò/Đại diện), và Mâu thuẫn nội bộ dẫn đến việc rời câu lạc bộ.
8. **Mạng lưới các chính trị gia Việt Nam:** Khai thác Infobox (chức vụ, nhiệm kỳ) kết hợp phân tích văn bản mục "Quá trình công tác" để xây dựng đồ thị luân chuyển cán bộ: kết nối chính khách với các cơ quan trung ương/địa phương theo các cạnh Tiền nhiệm - Kế nhiệm, Cùng ban lãnh đạo nhiệm kỳ, hoặc Trưởng thành từ cơ sở.
9. **Mạng lưới các chính trị gia Quốc tế:** Phân tích nội dung mục "Political career" và "Foreign policy" để xây dựng đồ thị có dấu (Signed Graph) giữa các chính khách, đảng phái và chính phủ: phân loại cạnh thành Liên minh chính trị/Ủng hộ, Đối lập/Tranh cử trực tiếp, hoặc Chuyển đảng.
10. **Mạng lưới lãnh đạo các công ty Việt Nam:** Kết hợp Infobox doanh nghiệp với việc phân tích văn bản mục "Lịch sử hình thành" và "Cơ cấu tổ chức" để trích xuất mạng lưới giữa Doanh nhân và Tập đoàn: Sáng lập, Thâu tóm/Sáp nhập (M&A) công ty khác, Thoái vốn, hoặc Bổ nhiệm/Miễn nhiệm điều hành.
11. **Mạng lưới lãnh đạo các công ty Quốc tế:** Phân tích văn bản tiểu sử các tỷ phú, CEO và lịch sử các tập đoàn công nghệ/tài chính toàn cầu để phân loại cạnh: Rời bỏ để khởi nghiệp (cựu lãnh đạo công ty A lập ra công ty B), Đầu tư thiên thần, Cạnh tranh thị phần trực tiếp, hoặc Kiện tụng thương mại.
12. **Mạng lưới trường đại học và cựu sinh viên Việt Nam:** Không chỉ lấy trường `Đại học Công nghệ` trong Infobox, mà phân tích văn bản mục "Giáo dục" và "Sự nghiệp" để phân biệt rõ vai trò kết nối giữa cá nhân và nhà trường: Cựu sinh viên học tập, Giảng viên thỉnh giảng, Thành lập quỹ học bổng, hoặc Lãnh đạo nhà trường qua các thời kỳ.
13. **Mạng lưới trường đại học và cựu sinh viên Quốc tế:** Phân tích nội dung bài viết về các trường đại học thế giới và danh nhân để trích xuất các cạnh: Đào tạo chuyên môn, Trao bằng Tiến sĩ danh dự, Tài trợ hiến tặng (Endowment) từ các cựu sinh viên tỷ phú, hoặc Hợp tác thành lập viện nghiên cứu.
14. **Mạng lưới các nhân vật lịch sử Việt Nam và các phe phái/tổ chức:** Phân tích sâu văn bản tự sự lịch sử để phân loại vai trò nhân vật (Vua, Tướng lĩnh, Mưu sĩ, Nghĩa quân) và gán nhãn loại cạnh giữa các nhân vật/triều đại: Đồng minh kháng chiến, Phò tá/Trung thần, Đối đầu quân sự, hoặc Đảo chính/Phản bội.
15. **Mạng lưới các nhân vật lịch sử Quốc tế và các phe phái/tổ chức:** Khai thác văn bản lịch sử thế giới để xây dựng đồ thị quan hệ giữa các hoàng tộc, đế chế và tướng lĩnh: phân loại cạnh thành Hôn nhân chính trị, Ký hiệp ước đồng minh, Tuyên chiến/Xâm lược, hoặc Lật đổ chế độ.
16. **Mạng lưới các tổ chức trao giải thưởng và người đoạt giải:** Kết hợp danh sách giải thưởng trong Infobox với việc phân tích văn bản bài viết để trích xuất mối quan hệ đa chiều giữa Tổ chức trao giải, Ban giám khảo và Cá nhân: Đề cử, Trao giải vinh danh, Từ chối nhận giải (như trong giải Nobel/Oscar), hoặc Tước giải thưởng do vi phạm.

## PHẦN 2: DỮ LIỆU BÁO CHÍ

17. **Mạng lưới Lãnh đạo Doanh nghiệp, Tập đoàn và Ngân hàng Việt Nam (Báo Kinh tế - Tài chính):**
    - **Nguồn dữ liệu phổ biến:** CafeF, VnEconomy, Báo Đầu Tư, Vietstock (hàng trăm tin bài mỗi ngày về doanh nghiệp đại chúng).
    - **Phân tích nội dung & Phân loại cạnh:** Trích xuất mối quan hệ giữa Chủ tịch/CEO, Công ty niêm yết, Công ty con và Ngân hàng theo các cạnh: Sở hữu cổ phần/Thâu tóm, Cấp tín dụng/Phát hành trái phiếu, Ký kết liên doanh, hoặc Bị xử phạt/Khởi tố.
18. **Mạng lưới Tập đoàn Đa quốc gia, Tỷ phú và Quỹ Đầu tư Quốc tế (Báo Kinh tế Thế giới):**
    - **Nguồn dữ liệu phổ biến:** Chuyên mục Kinh doanh quốc tế (VnExpress, Tuổi Trẻ) hoặc Reuters, Bloomberg, TechCrunch.
    - **Phân tích nội dung & Phân loại cạnh:** Kết nối các CEO công nghệ/tài chính, Startup, Quỹ đầu tư mạo hiểm (VC) và Chính phủ các nước qua các cạnh: Rót vốn đầu tư, Sáp nhập (M&A), Kiện chống độc quyền, hoặc Đứt gãy/Hợp tác chuỗi cung ứng.
19. **Mạng lưới Chính trị gia và Cơ quan Quản lý Nhà nước Việt Nam (Báo Thời sự - Nội chính):**
    - **Nguồn dữ liệu phổ biến:** Chuyên mục Thời sự trên VnExpress, Thanh Niên, Tuổi Trẻ, Báo Chính Phủ.
    - **Phân tích nội dung & Phân loại cạnh:** Phân tích tin tức hoạt động chỉ đạo, điều hành để kết nối các Lãnh đạo bộ ngành/địa phương với các Cơ quan nhà nước và Tập đoàn trọng điểm qua các cạnh: Chủ trì/Chỉ đạo trực tiếp, Điều động/Bổ nhiệm nhân sự, hoặc Thanh tra/Kiểm tra.
20. **Mạng lưới Nguyên thủ Quốc gia và Tổ chức Quốc tế qua Bản tin Ngoại giao (Báo Thế giới):**
    - **Nguồn dữ liệu phổ biến:** Chuyên mục Thế giới / Quốc tế trên tất cả các báo điện tử hàng ngày.
    - **Phân tích nội dung & Phân loại cạnh:** Trích xuất thái độ và hành động ngoại giao giữa các Tổng thống/Thủ tướng, Chính phủ và Tổ chức quốc tế (LHQ, NATO, EU, ASEAN) thành các cạnh: Hội đàm/Ký kết chiến lược, Viện trợ quân sự/Kinh tế, hoặc Trừng phạt/Trục xuất ngoại giao.
21. **Mạng lưới Cầu thủ, Huấn luyện viên và Câu lạc bộ Bóng đá Quốc tế (Báo Thể thao Quốc tế):**
    - **Nguồn dữ liệu phổ biến:** Chuyên mục Thể thao bóng đá Anh, TBN, Cúp C1 (Bongdaplus, 24h, VnExpress Thể thao - nguồn tin cực kỳ khổng lồ).
    - **Phân tích nội dung & Phân loại cạnh:** Kết nối Cầu thủ, HLV, Người đại diện và các CLB qua các cạnh: Chuyển nhượng/Đàm phán mua bán, Sa thải/Bổ nhiệm HLV, Gia hạn hợp đồng, hoặc Chỉ trích/Xung đột phòng thay đồ.
22. **Mạng lưới Cầu thủ, Huấn luyện viên và CLB Bóng đá Việt Nam (Báo Thể thao Trong nước):**
    - **Nguồn dữ liệu phổ biến:** Tin tức giải V-League, Hạng Nhất và Đội tuyển Quốc gia Việt Nam trên các báo thể thao hàng ngày.
    - **Phân tích nội dung & Phân loại cạnh:** Kết nối Cầu thủ nội/ngoại binh, HLV, Ông bầu, CLB và VFF qua các cạnh: Ký hợp đồng/Thanh lý, Triệu tập lên tuyển, Kỷ luật/Treo giò, hoặc Tài trợ đội bóng.
23. **Mạng lưới Ca sĩ, Nhạc sĩ và Công ty Giải trí Việt Nam (Báo Văn hóa - Giải trí):**
    - **Nguồn dữ liệu phổ biến:** Kênh14, SaoStar, Znews, chuyên mục Giải trí VnExpress/Tuổi Trẻ.
    - **Phân tích nội dung & Phân loại cạnh:** Phân tích tin tức âm nhạc, gameshow thực tế (như Anh Trai Say Hi, Anh Trai Vượt Ngàn Chông Gai...) để kết nối Ca sĩ, Nhạc sĩ, Producer và Công ty quản lý/Nhãn hàng qua các cạnh: Hợp tác ra MV/Biểu diễn, Đại sứ thương hiệu, hoặc Tranh chấp bản quyền/Scandal.
24. **Mạng lưới Ngôi sao Âm nhạc, Thần tượng K-Pop/US-UK và Tập đoàn Giải trí Quốc tế:**
    - **Nguồn dữ liệu phổ biến:** Chuyên mục Nhạc quốc tế / K-Pop trên các trang tin giới trẻ và báo điện tử.
    - **Phân tích nội dung & Phân loại cạnh:** Kết nối các Idol, Ca sĩ Âu Mỹ với các Tập đoàn giải trí (HYBE, SM, YG, Universal Music...) và Nhãn hàng xa xỉ qua các cạnh: Ra mắt (Debut)/Tái ký hợp đồng, Kiện chấm dứt hợp đồng, Hợp tác toàn cầu (Collab), hoặc Đại diện thời trang.
25. **Mạng lưới Diễn viên, Đạo diễn và Nhà sản xuất Phim Việt Nam (Báo Điện ảnh - Giải trí):**
    - **Nguồn dữ liệu phổ biến:** Tin tức phim truyền hình giờ vàng (VTV) và phim điện ảnh chiếu rạp Việt Nam trên báo chí.
    - **Phân tích nội dung & Phân loại cạnh:** Kết nối Đạo diễn, Diễn viên chính/phụ, Nhà sản xuất và Nhà phát hành phim qua các cạnh: Tuyển chọn vai diễn (Casting), Hợp tác sản xuất, Đóng cặp màn ảnh, hoặc Tranh cãi/Chê bai tác phẩm.
26. **Mạng lưới Diễn viên, Đạo diễn Hollywood/Châu Á và các Hãng Phim Quốc tế:**
    - **Nguồn dữ liệu phổ biến:** Chuyên mục Phim ảnh quốc tế trên báo chí (tin tức Marvel, DC, Netflix, phim Hàn/Trung).
    - **Phân tích nội dung & Phân loại cạnh:** Kết nối Ngôi sao điện ảnh, Đạo diễn với các Studio lớn và Nền tảng Streaming qua các cạnh: Ký hợp đồng bom tấn, Thay thế diễn viên do bê bối, Cạnh tranh phòng vé, hoặc Trao giải tại các Liên hoan phim.

## PHẦN 3: DỮ LIỆU BÀI BÁO KHOA HỌC

### 9 đề tài - chia theo chủ đề nghiên cứu

27. **Mạng lưới các tác giả và tổ chức nghiên cứu về Xử lý ngôn ngữ tự nhiên (NLP) Quốc tế:** Xây dựng mạng lưới các nhà khoa học và tổ chức công nghệ toàn cầu thông qua các bài báo thuộc chủ đề NLP và Mô hình ngôn ngữ lớn (LLM) trên ACL/arXiv, sử dụng thông tin đồng tác giả, cơ quan công tác và mối quan hệ trích dẫn qua lại.
28. **Mạng lưới các tác giả và tổ chức nghiên cứu về Trí tuệ nhân tạo (AI) Việt Nam:** Xây dựng mạng lưới các chuyên gia AI trong nước thông qua các công bố khoa học thuộc chủ đề Học máy (Machine Learning) và Học sâu (Deep Learning), kết nối dựa trên quan hệ đồng tác giả, đơn vị công tác (trường đại học, phòng lab doanh nghiệp) và trích dẫn học thuật.
29. **Mạng lưới các tác giả và tổ chức nghiên cứu về Trí tuệ nhân tạo (AI) Quốc tế:** Xây dựng mạng lưới các nhà nghiên cứu và tập đoàn/viện nghiên cứu quốc tế thông qua các bài báo tại các hội nghị AI hàng đầu (NeurIPS, ICML), sử dụng thông tin người viết, nơi làm việc, nhánh chủ đề AI và mạng lưới bài báo trích dẫn nhau.
30. **Mạng lưới các tác giả và tổ chức nghiên cứu về Thị giác máy tính (Computer Vision):** Xây dựng mạng lưới các nhà khoa học thông qua các bài báo thuộc chủ đề xử lý ảnh và nhận diện thị giác (như hội nghị CVPR, ICCV), khai thác mối quan hệ đồng tác giả, trường đại học/viện nghiên cứu chủ quản và liên kết trích dẫn giữa các nhóm tác giả.
31. **Mạng lưới các tác giả và tổ chức nghiên cứu về Khoa học dữ liệu và Dữ liệu lớn (Data Science & Big Data):** Xây dựng mạng lưới các nhà nghiên cứu thông qua các bài báo thuộc chủ đề khai phá dữ liệu (Data Mining), phân tích dữ liệu lớn (KDD, IEEE BigData), dựa trên liên kết giữa người viết bài, cơ quan làm việc, từ khóa chủ đề và trích dẫn.
32. **Mạng lưới các tác giả và tổ chức nghiên cứu về Hệ thống gợi ý và Khai phá đồ thị (Recommender Systems & Graph Mining):** Xây dựng mạng lưới các nhà khoa học thông qua các bài báo chuyên về mạng xã hội, đồ thị tri thức và hệ thống gợi ý, sử dụng thông tin tác giả, nơi công tác và quan hệ trích dẫn giữa các công trình.
33. **Mạng lưới các tác giả và tổ chức nghiên cứu về Y sinh và Dược học (Biomedicine) Việt Nam:** Xây dựng mạng lưới các bác sĩ, nhà nghiên cứu y học tại Việt Nam thông qua các bài báo công bố về dịch tễ, dược học và lâm sàng, kết nối qua quan hệ đồng tác giả, nơi làm việc (bệnh viện, trường đại học y) và trích dẫn tài liệu.
34. **Mạng lưới các tác giả và tổ chức nghiên cứu về Y sinh và Dược học (Biomedicine) Quốc tế:** Xây dựng mạng lưới các nhà khoa học y sinh toàn cầu thông qua dữ liệu bài báo trên PubMed (chủ đề gen, vắc-xin, điều trị bệnh), sử dụng thông tin người viết, viện nghiên cứu/bệnh viện/hãng dược và mạng lưới trích dẫn khoa học.
35. **Mạng lưới các tác giả và tổ chức nghiên cứu liên ngành AI trong Y tế và Tin sinh học (Bioinformatics & MedAI):** Xây dựng mạng lưới kết nối giữa các nhà nghiên cứu CNTT và chuyên gia Y khoa thông qua các bài báo ứng dụng AI/Dữ liệu vào chẩn đoán y tế và giải mã gen, dựa trên thông tin đồng tác giả, nơi làm việc (viện công nghệ - bệnh viện) và trích dẫn chéo giữa hai lĩnh vực.