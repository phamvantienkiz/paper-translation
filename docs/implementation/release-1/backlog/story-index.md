# Sổ cái Backlog: Paper Translation — Release 1 (Personal Core MVP v3.3)

**Tầng tài liệu**: Implementation Layer  
**Release**: release-1 (Personal Core MVP)  
**Phiên bản**: 3.3 (Indra OCR, Standalone Llama.cpp Server + Gemma-4-E2B & 3-Layer HTML Canvas Edition)  
**Nguồn tham chiếu**: PRD [docs/implementation/release-1/prd.md](file:///E:/MyProject/paper-translation/docs/implementation/release-1/prd.md)  
**Ranh giới hệ thống**: Sơ đồ Use Case tại [docs/architecture/01-system-context.md](file:///E:/MyProject/paper-translation/docs/architecture/01-system-context.md)  
**Ngày cập nhật**: 2026-10-23  
**Trạng thái**: Ready for Implementation  

---

## 1. Ma trận phân bổ User Stories & Traceability (v3.3)

| Mã Story | Tiêu đề User Story | Persona | Ưu tiên | Ánh xạ PRD | Ước lượng | Rào chắn kiến trúc (Guardrails) | Trạng thái |
|---|---|---|---|---|---|---|---|
| [US-001](file:///E:/MyProject/paper-translation/docs/implementation/release-1/backlog/stories/US-001.md) | Tiếp nhận tệp bài báo PDF từ máy cục bộ hoặc tự động tải qua arXiv ID/URL | Cá nhân nhà nghiên cứu | P0 (Must) | FR-01 | 2 SP | 05-data, 08-integ | Ready for Dev |
| [US-002](file:///E:/MyProject/paper-translation/docs/implementation/release-1/backlog/stories/US-002.md) | Phân tích bố cục 2 cột, thứ tự đọc, chuẩn hóa tọa độ & thu hồi sạch RAM | Cá nhân nhà nghiên cứu | P0 (Must) | FR-02 | 5 SP | 02-arch, 03-service, 05-data, ADR-002 | Ready for Dev |
| [US-003](file:///E:/MyProject/paper-translation/docs/implementation/release-1/backlog/stories/US-003.md) | Kết xuất ảnh nền trang gốc (Layer 0) & crop khối hình ảnh theo BBox qua PyMuPDF | Kỹ sư R&D / Độc giả | P0 (Must) | FR-03 | 3 SP | 03-service, 05-data, ADR-002 | Ready for Dev |
| [US-004](file:///E:/MyProject/paper-translation/docs/implementation/release-1/backlog/stories/US-004.md) | Bộ lọc khối thông minh & Dịch toàn văn tùy chọn qua Google Gemini (`max_tokens=65536`) | Độc giả khoa học | P1 (Should) | FR-04 | 5 SP | 02-arch, 03-service, 08-integ, ADR-002 | Ready for Dev |
| [US-005](file:///E:/MyProject/paper-translation/docs/implementation/release-1/backlog/stories/US-005.md) | Tái hiện bài báo bản dịch trên 3-Layer HTML5 Canvas (Auto-Fit Text + KaTeX SVG) | Độc giả nghiên cứu | P0 (Must) | FR-05 | 5 SP | 02-arch, 03-service, 08-integ, ADR-002 | Ready for Dev |
| [US-006](file:///E:/MyProject/paper-translation/docs/implementation/release-1/backlog/stories/US-006.md) | Tương tác đối chiếu Bản gốc / Bản dịch, chỉnh sửa khối & Xuất PDF 1-click từ Canvas | Cá nhân nhà nghiên cứu | P0 (Must) | FR-05, FR-06 | 3 SP | 03-service, 08-integ, ADR-002 | Ready for Dev |
| [US-007](file:///E:/MyProject/paper-translation/docs/implementation/release-1/backlog/stories/US-007.md) | Xây dựng Service riêng quản lý Standalone `llama.cpp` Server (`Gemma-4-E2B`, 4 P-Cores i5-13500H, trần 8GB RAM) | Độc giả nghiên cứu khoa học | P0 (Must) | FR-07.1, FR-07.2 | 5 SP | 03-service, 06-ai, AGENTS.md | Ready for Dev |
| [US-008](file:///E:/MyProject/paper-translation/docs/implementation/release-1/backlog/stories/US-008.md) | Phân lô 2,000–2,500 từ tiếng Anh, giao tiếp Python Client nội bộ & chống tràn Context tiếng Việt (2–2.5x) | Kỹ sư R&D | P0 (Must) | FR-07.3, FR-07.4 | 5 SP | 05-data, 06-ai, 08-integ | Ready for Dev |
| [US-009](file:///E:/MyProject/paper-translation/docs/implementation/release-1/backlog/stories/US-009.md) | Điều phối Translation Router, chỉ báo Gemma-4-E2B trên UI & Đồng bộ Canvas Viewer | Độc giả nghiên cứu | P0 (Must) | FR-07.5, FR-08 | 2 SP | 03-service, 05-data, 08-integ | Ready for Dev |

**Tổng dung lượng ước lượng**: 35 Story Points (SP).

---

## 2. Thống kê độ bao phủ (Fact-list Coverage Summary)

- **Tổng số kịch bản Acceptance Criteria (AC)**: 30 ACs chuẩn Given-When-Then.
  - 🟢 **Happy Paths (Thành công chuẩn)**: Bao quát trọn vẹn luồng từ Upload PDF/arXiv $\rightarrow$ Indra OCR + Normalized BBox `[0..1]` $\rightarrow$ Thu hồi sạch RAM OCR (`unload()` & `gc.collect()`) $\rightarrow$ Khởi chạy tiến trình riêng `llama.cpp server` với mô hình `gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf` (cấu hình 4 P-cores trên Intel Core i5-13500H, tăng tốc phần cứng, trần $\le 8.0\text{ GB}$ RAM, ngữ cảnh 16K/8K) $\rightarrow$ Đóng gói lô 2,000–2,500 từ tiếng Anh & gọi qua Python Client nội bộ (`127.0.0.1`) với Output dự phòng gấp 2.0–2.5x $\rightarrow$ Hiển thị 3-Layer HTML Canvas kèm huy hiệu Engine trên UI $\rightarrow$ Xuất PDF bản dịch.
  - 🟡 **Edge Cases & Validation (Điều kiện biên)**: Rào chắn tách biệt tiến trình (không nhúng in-process vào FastAPI); rào chắn Mutex cấm chạy song song OCR và LLM; đảm bảo Output tiếng Việt dài gấp 2.0–2.5 lần không bị tràn context; tự động gọi bù qua mạng nội bộ khi thiếu nhãn `[[BLK_XXXX]]`; khối văn bản tiếng Việt tự co giãn font vừa khít BBox.
  - 🔴 **Negative Paths (Xử lý lỗi ngoại lệ)**: File không phải PDF hợp lệ, thiếu file model `gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf` trong `storage/models/`, lỗi khởi chạy tiến trình `llama.cpp server`, lỗi kết nối API Gemini.
