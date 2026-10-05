# Ubiquitous Domain Glossary — Paper Translation

**Tầng tài liệu**: Business Layer  
**Dự án**: Paper Translation  
**Phiên bản**: 1.0  
**Ngày cập nhật**: 2026-10-05  
**Trạng thái**: Approved  

---

## 1. Mục đích

Tài liệu này định nghĩa ngôn ngữ chung (Ubiquitous Language) của dự án **Paper Translation**, thống nhất cách hiểu giữa Product Owner, Business Analyst, Kỹ sư phần mềm và Người dùng cuối, ngăn ngừa sự nhầm lẫn giữa các khái niệm kỹ thuật và nghiệp vụ.

---

## 2. Danh mục thuật ngữ nghiệp vụ cốt lõi

| Thuật ngữ | Tên tiếng Anh | Định nghĩa nghiệp vụ |
|---|---|---|
| **Bài báo khoa học** | *Scientific Paper / Academic Article* | Tài liệu nghiên cứu có cấu trúc chuẩn mực bao gồm tiêu đề, tóm tắt (Abstract), các phân đoạn nội dung, công thức toán học, bảng biểu, hình vẽ và danh mục tài liệu tham khảo. |
| **Giao diện đọc song ngữ** | *Dual-Pane Reader* | Bố cục giao diện hiển thị 2 cột song song cạnh nhau: Cột bên trái hiển thị văn bản gốc tiếng Anh, cột bên phải hiển thị bản dịch tiếng Việt, hỗ trợ cuộn đồng thời. |
| **Cuộn đồng bộ** | *Synchronized Scrolling* | Cơ chế khi người dùng cuộn xem nội dung ở một cột, cột còn lại sẽ tự động căn chỉnh vị trí tương ứng dựa trên phân đoạn đang đọc. |
| **Bảo toàn công thức toán** | *LaTeX Preservation* | Kỹ thuật cô lập các biểu thức toán học (dạng inline `$ ... $` hoặc block display `$$ ... $$`) trong quá trình xử lý ngôn ngữ tự nhiên để ngăn chặn bộ máy dịch làm biến dạng hoặc dịch đè lên công thức. |
| **Phân đoạn** | *Segment / Chunk* | Khối nội dung văn bản logic nhỏ nhất (thường là một câu hoặc một đoạn văn ngắn) có liên kết ánh xạ 1-1 giữa văn bản nguồn và văn bản đích. |
| **Bộ từ điển thuật ngữ** | *Glossary* | Bảng ánh xạ các cặp thuật ngữ chuyên ngành (Source Term $\rightarrow$ Target Term). Khi phát hiện thuật ngữ trong văn bản nguồn, bản dịch bắt buộc phải tuân theo định nghĩa trong Glossary. |
| **Thu thập từ arXiv** | *arXiv Ingestion* | Quy trình tiếp nhận đường dẫn bài báo (arXiv URL) hoặc mã số định danh (arXiv ID), tự động tải về tệp bài báo gốc và trích xuất siêu dữ liệu (Metadata: Title, Authors, Abstract). |
| **Khớp nối song ngữ** | *Bilingual Alignment* | Mối liên kết logic giữa một phân đoạn văn bản gốc và phân đoạn văn bản dịch tương ứng, cho phép người dùng click chọn để làm nổi bật (highlight) cả 2 bên. |
| **Biên tập phân đoạn** | *Segment Editing* | Khả năng người dùng có thể nhấp chuột trực tiếp vào một phân đoạn bản dịch tiếng Việt để chỉnh sửa lại câu chữ cho mượt mà hoặc chuẩn xác hơn. |
| **Xuất kết quả** | *Export Deliverable* | Chức năng kết xuất toàn bộ bài viết đã dịch hoàn chỉnh kèm công thức toán và hình ảnh thành tệp lưu trữ (Markdown, PDF). |
