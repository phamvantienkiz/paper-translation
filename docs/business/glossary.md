# Ubiquitous Domain Glossary — Paper Translation

**Tầng tài liệu**: Business Layer  
**Dự án**: Paper Translation (Personal & Open-Source Edition)  
**Phiên bản**: 3.1 (Indra OCR, Single-Call Gemini & 3-Layer HTML Canvas Edition)  
**Ngày cập nhật**: 2026-10-22  
**Trạng thái**: Approved  

---

## 1. Mục đích

Tài liệu này thống nhất các khái niệm nghiệp vụ và kỹ thuật cốt lõi của hệ thống **Paper Translation v3.1**, bao gồm phân tích bố cục bằng Indra OCR, chuẩn hóa hệ tọa độ, dịch toàn văn 1 lần gọi qua Google Gemini và tái hiện nguyên bản trên HTML Canvas 3 lớp.

---

## 2. Danh mục Thuật ngữ Nghiệp vụ & Kỹ thuật Học thuật

| Thuật ngữ | Tên tiếng Anh | Định nghĩa nghiệp vụ trong hệ thống |
|---|---|---|
| **Phân tích bố cục Indra OCR** | *Indra OCR Layout Analysis* | Quy trình sử dụng mô hình nhẹ `indra_ocr` trên ONNX Runtime (CPU) để nhận diện cấu trúc 2 cột, thứ tự đọc (`reading_order`), phân loại nhãn khối (`label`) và trích xuất tọa độ hộp (`bbox`). |
| **Tọa độ chuẩn hóa bất biến** | *Normalized Bounding Box (`[0..1]`)* | Hệ tọa độ tỷ lệ `[x0_norm, y0_norm, x1_norm, y1_norm]` trong đoạn `[0.0, 1.0]` theo kích thước trang, giúp đồng bộ chính xác 100% vị trí giữa Indra OCR, PyMuPDF và HTML Canvas ở mọi mức DPI/Zoom. |
| **Dịch toàn văn 1 lần gọi** | *Gemini Single-Call Translation* | Chiến lược đóng gói toàn bộ các khối văn bản cần dịch của bài báo kèm thẻ định danh `[[BLK_XXXX]]` và gửi tới Google Gemini API (`max_tokens=65536`) trong 1 request duy nhất để bảo toàn tuyệt đối ngữ cảnh học thuật liên trang. |
| **Bộ lọc thông minh trước dịch** | *Smart Translatable Pre-Filter* | Cơ chế tự động đánh dấu `is_translatable = False` đối với phần `References / Bibliography`, tiêu đề đầu/cuối trang (`page header/footer`) và khối hình ảnh/công thức thuần túy để giữ nguyên bản gốc và tiết kiệm 25–35% output tokens. |
| **Kiến trúc HTML Canvas 3 lớp** | *3-Layer Erase-and-Redraw Canvas* | Cơ chế tái hiện trang bài báo gồm: **Layer 0** (Ảnh nền trang PDF gốc độ nét cao bảo toàn 100% sơ đồ vector TikZ, biểu đồ, đường kẻ), **Layer 1** (Phủ trắng `#FFFFFF` xóa vùng chữ gốc của các khối đã dịch) và **Layer 2** (Vẽ chữ tiếng Việt tự co giãn cỡ chữ kèm công thức KaTeX SVG). |
| **Tự động co giãn cỡ chữ** | *Binary-Search Font Auto-Scaling* | Thuật toán tự động tìm kích thước font chữ tiếng Việt tối ưu để toàn bộ nội dung dịch nằm vừa khít trong diện tích Bounding Box của khối văn bản tiếng Anh gốc mà không tràn lề. |
| **Xuất PDF nguyên bản** | *Same-Origin Canvas PDF Export* | Tính năng kết xuất toàn bộ các trang từ HTML Canvas thành tệp PDF tiếng Việt hoàn chỉnh, giữ nguyên 100% bố cục 2 cột, hình ảnh và công thức như bài báo gốc. |
