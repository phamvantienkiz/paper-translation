# Ubiquitous Domain Glossary — Paper Translation

**Tầng tài liệu**: Business Layer  
**Dự án**: Paper Translation (Personal & Open-Source Edition)  
**Phiên bản**: 2.0 (Scaled Down & Focused)  
**Ngày cập nhật**: 2026-10-05  
**Trạng thái**: Approved  

---

## 1. Mục đích

Tài liệu này thống nhất các khái niệm nghiệp vụ cốt lõi của công cụ **Paper Translation**, đặc biệt chú trọng vào các thuật ngữ xử lý tài liệu đa định dạng, bảo toàn toán học/hình/bảng và miền kiến thức **Công nghệ thông tin & Trí tuệ nhân tạo (IT & AI)**.

---

## 2. Danh mục Thuật ngữ Nghiệp vụ & Kỹ thuật Học thuật

| Thuật ngữ | Tên tiếng Anh | Định nghĩa nghiệp vụ trong hệ thống |
|---|---|---|
| **Đa định dạng đầu vào** | *Multi-format Ingestion* | Khả năng tiếp nhận các tệp bài báo học thuật ở nhiều định dạng tệp khác nhau, trong đó ưu tiên hàng đầu là **PDF** và **DOCX**. |
| **Giao diện đọc song ngữ** | *Dual-Pane Web UI* | Màn hình giao diện Web hiển thị 2 cột song song (cột trái: văn bản gốc tiếng Anh, cột phải: bản dịch tiếng Việt) hỗ trợ đọc đối chiếu trực quan. |
| **Bảo toàn công thức toán** | *LaTeX Preservation* | Cơ chế cô lập các biểu thức toán học dạng inline (`$ ... $`) và display (`$$ ... $$` hoặc môi trường `\begin{equation}...\end{equation}`) để tránh bị bộ máy dịch AI can thiệp làm sai lệch cú pháp. |
| **Bảo toàn bảng & hình ảnh** | *Table & Figure Preservation* | Cơ chế trích xuất và giữ nguyên vị trí, nội dung của các bảng số liệu thực nghiệm (Benchmark Tables) và hình ảnh sơ đồ kiến trúc mô hình trong bài viết. |
| **PDF bản dịch hoàn chỉnh** | *Translated PDF Deliverable* | Tệp PDF kết xuất chỉ chứa nội dung tiếng Việt đã được dịch thuật và dàn trang hoàn chỉnh, trong đó nhúng lại toàn bộ công thức toán LaTeX, hình ảnh và bảng biểu gốc. |
| **Ngữ cảnh chuyên ngành CNTT & AI** | *IT & AI Domain Context* | Tập hợp các chỉ dẫn prompt và quy tắc thuật ngữ chuyên môn sâu (Machine Learning, Deep Learning, Transformer, NLP, Computer Vision) để đảm bảo câu dịch tự nhiên, chuẩn mực khoa học. |
| **Triển khai tự vận hành** | *Self-Hosted / Local Web* | Mô hình ứng dụng cá nhân chạy trực tiếp trên máy tính người dùng hoặc máy chủ nội bộ thông qua Docker, không phụ thuộc vào dịch vụ đám mây tập trung. |
| **Mã nguồn mở cộng đồng** | *Open-Source Community* | Định hướng dự án công khai mã nguồn, cho phép cộng đồng nghiên cứu tự do sử dụng, tùy biến và đóng góp thêm tính năng. |
