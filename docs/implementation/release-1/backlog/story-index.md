# Sổ cái Backlog: Paper Translation — Release 1 (Personal Core MVP v3.1)

**Tầng tài liệu**: Implementation Layer  
**Release**: release-1 (Personal Core MVP)  
**Phiên bản**: 3.1 (Indra OCR, Single-Call Gemini & 3-Layer HTML Canvas Edition)  
**Nguồn tham chiếu**: PRD [docs/implementation/release-1/prd.md](file:///E:/MyProject/paper-translation/docs/implementation/release-1/prd.md)  
**Ranh giới hệ thống**: Sơ đồ Use Case tại [docs/architecture/01-system-context.md](file:///E:/MyProject/paper-translation/docs/architecture/01-system-context.md)  
**Ngày cập nhật**: 2026-10-22  
**Trạng thái**: Ready for Implementation  

---

## 1. Ma trận phân bổ User Stories & Traceability (v3.1)

| Mã Story | Tiêu đề User Story | Persona | Ưu tiên | Ánh xạ PRD | Ước lượng | Rào chắn kiến trúc (Guardrails) | Trạng thái |
|---|---|---|---|---|---|---|---|
| [US-001](file:///E:/MyProject/paper-translation/docs/implementation/release-1/backlog/stories/US-001.md) | Tiếp nhận tệp bài báo PDF từ máy cục bộ hoặc tự động tải qua arXiv ID/URL | Cá nhân nhà nghiên cứu | P0 (Must) | FR-01 | 2 SP | 05-data, 08-integ | Ready for Dev |
| [US-002](file:///E:/MyProject/paper-translation/docs/implementation/release-1/backlog/stories/US-002.md) | Phân tích bố cục 2 cột, thứ tự đọc & chuẩn hóa tọa độ `[0..1]` bằng Indra OCR | Cá nhân nhà nghiên cứu | P0 (Must) | FR-02 | 5 SP | 02-arch, 03-service, 05-data, ADR-002 | Ready for Dev |
| [US-003](file:///E:/MyProject/paper-translation/docs/implementation/release-1/backlog/stories/US-003.md) | Kết xuất ảnh nền trang gốc (Layer 0) & crop khối hình ảnh theo BBox qua PyMuPDF | Kỹ sư R&D / Độc giả | P0 (Must) | FR-03 | 3 SP | 03-service, 05-data, ADR-002 | Ready for Dev |
| [US-004](file:///E:/MyProject/paper-translation/docs/implementation/release-1/backlog/stories/US-004.md) | Bộ lọc khối thông minh & Dịch toàn văn 1 lần gọi qua Google Gemini (`max_tokens=65536`) | Độc giả khoa học | P0 (Must) | FR-04 | 5 SP | 02-arch, 03-service, 08-integ, ADR-002 | Ready for Dev |
| [US-005](file:///E:/MyProject/paper-translation/docs/implementation/release-1/backlog/stories/US-005.md) | Tái hiện bài báo bản dịch trên 3-Layer HTML5 Canvas (Auto-Fit Text + KaTeX SVG) | Độc giả nghiên cứu | P0 (Must) | FR-05 | 5 SP | 02-arch, 03-service, 08-integ, ADR-002 | Ready for Dev |
| [US-006](file:///E:/MyProject/paper-translation/docs/implementation/release-1/backlog/stories/US-006.md) | Tương tác đối chiếu Bản gốc / Bản dịch, chỉnh sửa khối & Xuất PDF 1-click từ Canvas | Cá nhân nhà nghiên cứu | P0 (Must) | FR-05, FR-06 | 3 SP | 03-service, 08-integ, ADR-002 | Ready for Dev |

**Tổng dung lượng ước lượng**: 23 Story Points (SP).

---

## 2. Thống kê độ bao phủ (Fact-list Coverage Summary)

- **Tổng số kịch bản Acceptance Criteria (AC)**: 18 ACs chuẩn Given-When-Then.
  - 🟢 **Happy Paths (Thành công chuẩn)**: Bao quát trọn vẹn luồng từ Upload PDF/arXiv $\rightarrow$ Indra OCR + Normalized BBox `[0..1]` $\rightarrow$ Kết xuất Layer 0 & Crop Figures $\rightarrow$ Lọc bỏ References & Dịch toàn văn 1 lần gọi qua Gemini $\rightarrow$ Hiển thị 3-Layer HTML Canvas $\rightarrow$ Xuất PDF bản dịch.
  - 🟡 **Edge Cases & Validation (Điều kiện biên)**: Bài báo dài chạm trần output token kích hoạt Auto-Continuation; khối văn bản tiếng Việt dài hơn tiếng Anh tự động thu nhỏ font chữ vừa khít hộp; khối chứa công thức LaTeX inline kết xuất qua KaTeX SVG `foreignObject`.
  - 🔴 **Negative Paths (Xử lý lỗi ngoại lệ)**: File không phải PDF hợp lệ, vượt quá 50MB, arXiv ID không tồn tại, lỗi kết nối API Gemini.
