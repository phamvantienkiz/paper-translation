# Business Requirement Document (BRD) — Paper Translation

**Tầng tài liệu**: Business Layer  
**Dự án**: Paper Translation  
**Phiên bản**: 1.0  
**Ngày cập nhật**: 2026-10-05  
**Trạng thái**: Approved  

---

## 1. Bối cảnh & Vấn đề nghiệp vụ (Problem Statement)

Trong kỷ nguyên bùng nổ tri thức khoa học và công nghệ, số lượng bài báo khoa học xuất sắc được công bố hàng ngày trên các nền tảng học thuật quốc tế (arXiv, IEEE, ACM, Nature, Science...) là vô cùng lớn. Tuy nhiên, rào cản ngôn ngữ và tính chất chuyên sâu của tài liệu học thuật đặt ra những thách thức nghiêm trọng:

1. **Sai lệch công thức và định dạng khi dịch:** Các công cụ dịch thuật phổ quát hiện nay (Google Translate, DeepL bản thông thường) thường phá hỏng các ký hiệu toán học LaTeX/MathJax, cấu trúc bảng biểu và vị trí hình ảnh, khiến bài báo trở nên không thể đọc hoặc hiểu sai bản chất.
2. **Thiếu chuẩn hóa thuật ngữ chuyên ngành:** Các khái niệm học thuật trong các ngành như Trí tuệ nhân tạo (AI), Khoa học máy tính (CS), Y sinh, Vật lý lượng tử thường bị dịch thô cứng, nghĩa vụn vặt hoặc thiếu nhất quán xuyên suốt bài viết.
3. **Trải nghiệm đọc đứt gãy:** Việc phải chuyển đổi liên tục giữa tệp PDF tiếng Anh gốc và các công cụ tra từ điển rời rạc làm giảm đáng kể tốc độ hấp thụ tri thức của người nghiên cứu.

---

## 2. Tầm nhìn sản phẩm (Product Vision)

Xây dựng **Paper Translation** thành nền tảng hỗ trợ dịch thuật và đọc bài báo khoa học chuyên sâu hàng đầu dành cho cộng đồng nghiên cứu, kỹ sư và sinh viên Việt Nam:
- **Bảo toàn nguyên vẹn 100%** các cấu trúc học thuật: Công thức toán học (LaTeX/MathJax), bảng biểu dữ liệu và hình minh họa.
- **Dịch thuật ngữ cảnh chuyên môn cao:** Kết hợp mô hình ngôn ngữ tiên tiến với bộ từ điển thuật ngữ (Glossary) chuyên ngành có thể tùy biến và chuẩn hóa.
- **Trải nghiệm đọc song ngữ tối ưu (Dual-pane):** Cung cấp không gian đối chiếu song song giữa bản gốc và bản dịch, giúp người đọc vừa nắm bắt nhanh nội dung tiếng Việt vừa đối chiếu chính xác thuật ngữ học thuật gốc tiếng Anh.

---

## 3. Chỉ số thành công & KPIs (Success Metrics)

| Nhóm chỉ số | Chỉ số cụ thể (KPI) | Mục tiêu kỳ vọng | Phương pháp đo lường |
|---|---|---|---|
| **Chất lượng học thuật** | Tỷ lệ bảo toàn công thức toán học | 100% công thức LaTeX không bị lỗi cú pháp | Automated validation & kiểm tra ngẫu nhiên |
| **Độ chuẩn thuật ngữ** | Tính nhất quán của thuật ngữ chuyên ngành | $\ge 95\%$ khớp đúng với Glossary | Kiểm tra tự động đối chiếu Glossary |
| **Hiệu năng & Tốc độ** | Thời gian xử lý dịch bài báo (20 trang) | $\le 60$ giây cho toàn bộ quy trình | Đo lường độ trễ từ tiếp nhận đến hiển thị |
| **Trải nghiệm người dùng** | Mức độ hài lòng của độc giả (CSAT) | $\ge 4.5 / 5.0$ | Khảo sát định kỳ người dùng |
| **Mức độ gắn kết** | Tỷ lệ phiên đọc hoàn thành $\ge 70\%$ bài viết | $\ge 60\%$ tổng số phiên đọc | Tracking tương tác cuộn đọc song ngữ |

---

## 4. Phân khúc người dùng mục tiêu (User Personas)

### Persona 1: Nhà nghiên cứu khoa học / Nghiên cứu sinh (PhD / Master)
- **Bối cảnh:** Cần đọc khối lượng lớn bài báo mỗi tuần để làm tổng quan nghiên cứu (Literature Review) và tìm ý tưởng mới.
- **Nỗi đau:** Tốn hàng giờ cho mỗi bài báo; công thức toán bị lỗi khi dùng các tiện ích dịch thông thường.
- **Mục tiêu:** Đọc nhanh bằng tiếng Việt nhưng vẫn đối chiếu được ngay công thức gốc và thuật ngữ học thuật chuẩn.

### Persona 2: Kỹ sư R&D / Chuyên gia công nghệ ứng dụng
- **Bối cảnh:** Cần nắm bắt nhanh các giải pháp công nghệ mới, kiến trúc mô hình từ các bài báo arXiv để áp dụng vào sản phẩm thực tế.
- **Nỗi đau:** Thuật ngữ kỹ thuật bị dịch sai ngữ cảnh gây hiểu nhầm logic thuật toán.
- **Mục tiêu:** Dịch nhanh từ arXiv URL, tra cứu và đóng góp vào bộ từ điển thuật ngữ riêng của dự án.

### Persona 3: Giảng viên & Sinh viên đại học
- **Bối cảnh:** Nghiên cứu bài tập lớn, đồ án tốt nghiệp hoặc chuẩn bị bài giảng chuyên ngành.
- **Nỗi đau:** Vốn tiếng Anh học thuật chưa thành thạo, gặp khó khăn khi tiếp cận các bài báo kinh điển.
- **Mục tiêu:** Bản dịch song ngữ mượt mà, dễ hiểu, có thể xuất ra tài liệu để lưu trữ và học tập.

---

## 5. Ranh giới giải pháp tổng thể (High-level Scope)

### In-Scope (Thuộc phạm vi hệ thống):
- Tiếp nhận tài liệu qua tệp PDF tải lên hoặc liên kết trực tuyến (arXiv URL, DOI).
- Bóc tách cấu trúc tài liệu học thuật (Abstract, Sections, Math equations, Tables, Figures).
- Cô lập và bảo toàn biểu thức toán học LaTeX inline và block.
- Dịch thuật tự động ngữ cảnh chuyên sâu tiếng Anh sang tiếng Việt.
- Áp dụng bộ từ điển thuật ngữ chuyên ngành (Glossary) trong quá trình dịch.
- Giao diện đọc song ngữ Dual-pane với tính năng cuộn đồng bộ và biên tập từng đoạn (Segment editing).
- Xuất bản dịch ra định dạng tài liệu học thuật (Markdown, PDF).

### Out-of-Scope (Nằm ngoài phạm vi hệ thống):
- Xử lý các tài liệu scan cũ chất lượng kém không có lớp văn bản (OCR chữ viết tay, văn bản trước thế kỷ 20).
- Hệ thống mạng xã hội học thuật, diễn đàn trao đổi hoặc bình duyệt đồng cấp (Peer-review system).
- Công cụ tự động sinh hoặc viết lại bài báo khoa học mới (Paper generation).
