# Architecture Layer — Navigation Map & System Invariants

**Tầng tài liệu**: Architecture Layer (Single Source of Truth)  
**Hệ thống**: Paper Translation  
**Phiên bản**: 3.1 (Indra OCR, Single-Call Gemini & 3-Layer HTML Canvas Edition)  
**Ngày cập nhật**: 2026-10-22  

---

## 1. Giới thiệu & Nguyên tắc Bất biến

Tầng **Architecture Layer** là **Nguồn sự thật duy nhất (Single Source of Truth)** cho toàn bộ hệ thống Paper Translation. Mọi kỹ sư phần mềm và AI Coding Agent khi tham gia phát triển dự án bắt buộc phải đọc và tuân thủ các nguyên tắc thiết kế bất biến được định nghĩa tại đây.

> ⛔ **Nguyên tắc cốt lõi**:
> - Tầng Architecture **TUYỆT ĐỐI KHÔNG chia theo Release**. Chỉ có một bộ tài liệu duy nhất, liên tục cập nhật theo sự tiến hóa của hệ thống.
> - Bất kỳ thay đổi kiến trúc lớn nào đều phải lập hồ sơ **Architectural Decision Record (ADR)** trước khi sửa đổi các tài liệu thành phần.

---

## 2. Bản đồ Điều hướng Tài liệu Kiến trúc

| Thứ tự | Tài liệu thành phần | Mô tả nội dung chính |
|---|---|---|
| **01** | [01-system-context.md](file:///E:/MyProject/paper-translation/docs/architecture/01-system-context.md) | Bối cảnh hệ thống, Actors, External Systems & Sơ đồ ranh giới Use Case v3.1. |
| **02** | [02-high-level-architecture.md](file:///E:/MyProject/paper-translation/docs/architecture/02-high-level-architecture.md) | Kiến trúc tổng thể hệ thống v3.1 (Indra OCR + Gemini Single-Call + 3-Layer HTML Canvas), BOTEC & ma trận đánh đổi. |
| **03** | [03-service-architecture.md](file:///E:/MyProject/paper-translation/docs/architecture/03-service-architecture.md) | Phân rã dịch vụ Modular Monolith (`IndraOcrSvc`, `PageAssetSvc`, `GeminiTranslator`, `LayoutMapper`, `CanvasEngine`). |
| **05** | [05-data-architecture.md](file:///E:/MyProject/paper-translation/docs/architecture/05-data-architecture.md) | Sơ đồ ERD SQLite WAL (`paper_sessions`, `paper_pages`, `ocr_blocks` với tọa độ chuẩn hóa `[0..1]`, `glossary_items`). |
| **08** | [08-integration-architecture.md](file:///E:/MyProject/paper-translation/docs/architecture/08-integration-architecture.md) | Chuẩn hóa API REST (`/canvas-data`), kênh Server-Sent Events (SSE) & giao thức Gemini Single-Call (`max_tokens=65536`). |
| **ADR-001** | [adr/ADR-001.md](file:///E:/MyProject/paper-translation/docs/architecture/adr/ADR-001.md) | Hồ sơ quyết định: Áp dụng Pipeline bất đồng bộ trong tiến trình (`asyncio`) kết hợp Server-Sent Events (SSE). |
| **ADR-002** | [adr/ADR-002.md](file:///E:/MyProject/paper-translation/docs/architecture/adr/ADR-002.md) | Hồ sơ quyết định: Chuyển đổi sang Indra OCR, Single-Call Gemini API và Tái hiện Bố cục bằng 3-Layer HTML Canvas. |

---

## 3. Các Bất biến Hệ thống (System Invariants v3.1)

1. **Dịch Toàn Văn Giữ Ngữ Cảnh (Single-Call Context Integrity):** Tuyệt đối không chia cắt bài báo thành các đoạn rời rạc (chunking) để dịch độc lập. Toàn bộ các khối văn bản cần dịch (`is_translatable = True`) được đóng gói kèm định danh `[[BLK_XXXX]]` và gửi qua Google Gemini trong **1 lần gọi duy nhất** (`max_tokens = 65536`), có cơ chế Auto-Continuation bảo vệ nếu bài báo vượt quá trần output token.
2. **Bất biến Hệ Tọa Độ Chuẩn Hóa (`[0.0 .. 1.0]`):** Mọi tọa độ Bounding Box lưu trong cơ sở dữ liệu và truyền qua API bắt buộc phải được chuẩn hóa về tỷ lệ tương đối `[x0_norm, y0_norm, x1_norm, y1_norm]` trong đoạn `[0.0, 1.0]` theo kích thước trang, đảm bảo ánh xạ chính xác 100% giữa Indra OCR, PyMuPDF và HTML Canvas ở mọi mức DPI/Zoom.
3. **Kiến Trúc Canvas 3 Lớp Bảo Toàn Đồ Họa (3-Layer Canvas Fidelity):** Giao diện HTML Canvas bắt buộc kết xuất theo 3 lớp:
   - *Layer 0:* Ảnh nền trang gốc độ phân giải cao (`page_X.png`) giúp bảo toàn 100% sơ đồ vector (TikZ), biểu đồ, đường kẻ bảng và công thức toán độc lập.
   - *Layer 1:* Xóa thông minh (Whiteout `#FFFFFF`) chỉ trên vùng Bounding Box của các khối văn bản được dịch.
   - *Layer 2:* Vẽ văn bản tiếng Việt đã dịch với thuật toán Auto-Fit Font Scaling kết hợp KaTeX SVG cho công thức toán học inline.
4. **Bất đồng bộ hóa Tác vụ Nặng:** Các tác vụ chạy Indra OCR, kết xuất ảnh trang và gọi Gemini API bắt buộc thực thi trong background task (`asyncio`) và phát tiến độ thời gian thực qua kênh SSE.
