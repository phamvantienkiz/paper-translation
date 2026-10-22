# Product Requirements Document (PRD): Release 1 (Personal Core MVP v3.1)

**Tầng tài liệu**: Implementation Layer  
**Release**: release-1 (Personal Core MVP)  
**Phiên bản**: 3.1 (Reviewed & Hardened — Indra OCR, Single-Call Gemini & 3-Layer HTML Canvas)  
**Ngày cập nhật**: 2026-10-22  
**Tác giả**: Senior IT-BA & PO  
**Trạng thái**: Approved  
**Chất lượng yêu cầu**: 100/100  

---

## 1. Mục tiêu Đợt Phát hành & Bối cảnh Nghiệp vụ (Business Context)

### 1.1. Mục tiêu đợt phát hành (Release Goals)
- **Tham chiếu Business Layer:** Bám sát tầm nhìn tại [docs/business/brd.md](file:///E:/MyProject/paper-translation/docs/business/brd.md) và quyết định kiến trúc [ADR-002](file:///E:/MyProject/paper-translation/docs/architecture/adr/ADR-002.md).
- **Trọng tâm Release 1 (v3.1):**
  1. Bóc tách chính xác bố cục 2 cột, thứ tự đọc (`reading_order`), bảng biểu HTML và công thức LaTeX bằng **Indra OCR (`indra_ocr` ONNX CPU)** kết hợp **Chuẩn hóa tọa độ `[0.0 .. 1.0]`**.
  2. Bảo toàn **100% hình ảnh, sơ đồ vector (TikZ/PGFPlots), đồ thị và đường kẻ bảng** thông qua việc kết xuất ảnh nền trang gốc độ phân giải cao (Layer 0) và crop riêng khối `figure` bằng `PyMuPDF`.
  3. Dịch toàn bộ bài báo trong **1 lần gọi duy nhất qua Google Gemini API** (`max_tokens = 65536`), kết hợp bộ lọc tự động bỏ qua phần `References / Bibliography` và cơ chế Auto-Continuation bảo vệ.
  4. Tái hiện bài báo bản dịch tiếng Việt trên **3-Layer HTML5 Canvas** (Layer 0: Ảnh trang gốc $\rightarrow$ Layer 1: Phủ trắng vùng chữ gốc của khối dịch $\rightarrow$ Layer 2: Vẽ chữ tiếng Việt tự co giãn cỡ chữ kèm công thức KaTeX SVG).
  5. Cho phép xuất và tải về trực tiếp **tệp PDF bản dịch hoàn chỉnh** giữ trọn vẹn bố cục 2 cột và hình ảnh minh họa.

---

## 2. Yêu cầu Chức năng Tinh gọn (Functional Requirements v3.1)

| Mã yêu cầu | Tên chức năng | Mô tả nghiệp vụ | Quy tắc nghiệp vụ & Kỹ thuật (Business & Technical Rules) | Mức ưu tiên |
|---|---|---|---|---|
| **FR-01** | Tiếp nhận tệp PDF & arXiv | Nhận tệp PDF tải lên từ máy tính hoặc tự động tải về khi dán mã/URL arXiv | Giới hạn tối đa 50MB. Kiểm tra định dạng magic bytes `%PDF-`. | P0 (Must) |
| **FR-02** | Indra OCR & Chuẩn hóa Tọa độ `[0..1]` | Chạy `indra_ocr` trên CPU để phân tích bố cục 2 cột, thứ tự đọc, bảng HTML, LaTeX và tọa độ hộp | Chuyển đổi toàn bộ tọa độ pixel sang tọa độ chuẩn hóa tương đối `[x0_norm, y0_norm, x1_norm, y1_norm]` trong đoạn `[0.0, 1.0]` theo kích thước trang. | P0 (Must) |
| **FR-03** | Kết xuất Ảnh Nền Trang (Layer 0) & Crop Hình Ảnh | Kết xuất từng trang PDF gốc thành ảnh độ nét cao (200 DPI) và crop riêng các khối `figure` bằng PyMuPDF | Lưu ảnh nền trang tại `storage/pages/` (bảo toàn 100% sơ đồ vector TikZ, đường kẻ bảng, công thức) và ảnh hình vẽ tại `storage/figures/`. | P0 (Must) |
| **FR-04** | Dịch Toàn Văn 1 Lần Gọi Gemini (`max_tokens=65536`) | Lọc bỏ các khối không cần dịch (`References`, `page header/footer`) và gửi toàn bộ khối cần dịch kèm mã `[[BLK_XXXX]]` tới Gemini trong 1 request | Sử dụng model mặc định `gemini-3.5-flash-lite` (1M context, `max_tokens=65536`). Giữ nguyên 100% LaTeX `$..$`, `<table>` và `[[BLK_XXXX]]`. Tự động gọi tiếp nối (Auto-Continuation) nếu chạm trần output token. | P0 (Must) |
| **FR-05** | Tái hiện Bài Báo Trên 3-Layer HTML Canvas | Hiển thị từng trang bài báo trên `<canvas>` với 3 lớp: Base Page, Smart Redaction (`#FFFFFF`) và Translated Text + KaTeX SVG | Tự động co giãn cỡ chữ (Binary-Search Font Auto-Scaling) để chữ tiếng Việt nằm gọn trong BBox gốc. Hỗ trợ Zoom, Pan và nút bật/tắt xem đối chiếu bản gốc tiếng Anh. | P0 (Must) |
| **FR-06** | Xuất Tệp PDF Bản Dịch Hoàn Chỉnh | Xuất và tải về tệp PDF tiếng Việt giữ nguyên bố cục 2 cột như bản gốc chỉ với 1 cú click | Kết xuất trực tiếp từ hệ thống trang Canvas độ phân giải cao sang tệp PDF chuẩn. | P0 (Must) |

---

## 3. Rào chắn Kiến trúc (Architecture Guardrails v3.1)

1. **Rào chắn Single-Call & Output Token:** Không băm nhỏ bài báo thành các chunk rời rạc. Luôn truyền `max_tokens: 65536`, tự động đánh dấu `is_translatable = False` cho mục `References` và kiểm tra đầy đủ mã `[[BLK_XXXX]]` sau khi dịch.
2. **Rào chắn 3-Layer Canvas Fidelity:** Không vẽ trên nền trắng trống rỗng làm mất sơ đồ vector TikZ và đường viền bảng. Luôn vẽ ảnh nền trang gốc (Layer 0), chỉ xóa trắng (`#FFFFFF`) đúng vùng BBox của các khối văn bản đã dịch (`is_translatable = True`) trước khi vẽ chữ tiếng Việt và công thức KaTeX.
3. **Rào chắn Tọa độ Chuẩn hóa:** Tuyệt đối không lưu tọa độ pixel thô phụ thuộc DPI mà không chuẩn hóa về `[0.0 .. 1.0]`.
