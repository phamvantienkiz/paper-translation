# Sổ cái Backlog: Paper Translation — Release 1 (Personal Core MVP)

**Tầng tài liệu**: Implementation Layer  
**Release**: release-1 (Personal Core MVP)  
**Nguồn tham chiếu**: PRD [docs/implementation/release-1/prd.md](file:///E:/MyProject/paper-translation/docs/implementation/release-1/prd.md)  
**Ranh giới hệ thống**: Sơ đồ Use Case tại [docs/architecture/01-system-context.md](file:///E:/MyProject/paper-translation/docs/architecture/01-system-context.md)  
**Ngày cập nhật**: 2026-10-05  
**Trạng thái**: Ready for Sprint Planning  

---

## 1. Ma trận phân bổ User Stories & Traceability

| Mã Story | Tiêu đề User Story | Persona | Ưu tiên | Ánh xạ PRD | Ước lượng | Rào chắn kiến trúc (Guardrails) | Trạng thái |
|---|---|---|---|---|---|---|---|
| [US-001](file:///E:/MyProject/paper-translation/docs/implementation/release-1/backlog/stories/US-001.md) | Tiếp nhận & kiểm tra tệp bài báo PDF upload từ máy cục bộ | Cá nhân nhà nghiên cứu | P0 (Must) | FR-01 | 2 SP | 05-data, 07-security, 09-principles | Ready for Dev |
| [US-002](file:///E:/MyProject/paper-translation/docs/implementation/release-1/backlog/stories/US-002.md) | Tiếp nhận & bóc tách tệp bài báo DOCX bảo toàn hình và bảng | Cá nhân nhà nghiên cứu | P0 (Must) | FR-01, FR-02 | 3 SP | 05-data, 09-principles, 10-folder | Ready for Dev |
| [US-003](file:///E:/MyProject/paper-translation/docs/implementation/release-1/backlog/stories/US-003.md) | Thu thập tự động bài báo và siêu dữ liệu từ arXiv URL/ID | Kỹ sư R&D / Độc giả | P0 (Must) | FR-01 | 2 SP | 07-security, 08-integ, 09-principles | Ready for Dev |
| [US-004](file:///E:/MyProject/paper-translation/docs/implementation/release-1/backlog/stories/US-004.md) | Bóc tách cấu trúc PDF & cô lập công thức toán LaTeX | Nhà nghiên cứu | P0 (Must) | FR-02 | 5 SP | 05-data, 09-principles, 10-folder | Ready for Dev |
| [US-005](file:///E:/MyProject/paper-translation/docs/implementation/release-1/backlog/stories/US-005.md) | Dịch thuật tự động phân đoạn chuyên sâu ngữ cảnh CNTT & AI | Độc giả khoa học | P0 (Must) | FR-03 | 5 SP | 05-data, 07-security, 08-integ, 09-principles | Ready for Dev |
| [US-006](file:///E:/MyProject/paper-translation/docs/implementation/release-1/backlog/stories/US-006.md) | Giao diện Web đọc song ngữ Dual-pane cuộn đồng bộ & highlight | Độc giả nghiên cứu | P0 (Must) | FR-04 | 5 SP | 09-principles, 10-folder, 11-frontend | Ready for Dev |
| [US-007](file:///E:/MyProject/paper-translation/docs/implementation/release-1/backlog/stories/US-007.md) | Chỉnh sửa trực tiếp & lưu tức thì phân đoạn bản dịch | Người nghiên cứu | P1 (Should) | FR-04 | 3 SP | 05-data, 09-principles, 11-frontend | Ready for Dev |
| [US-008](file:///E:/MyProject/paper-translation/docs/implementation/release-1/backlog/stories/US-008.md) | Biên dịch & tải về tệp PDF bản dịch tiếng Việt hoàn chỉnh | Cá nhân nhà nghiên cứu | P0 (Must) | FR-05 | 3 SP | 05-data, 08-integ, 09-principles | Ready for Dev |

**Tổng dung lượng ước lượng**: 28 Story Points (SP).

---

## 2. Thống kê độ bao phủ (Fact-list Coverage Summary)

- **Tổng số kịch bản Acceptance Criteria (AC)**: 25 ACs.
  - 🟢 **Happy Paths (Thành công chuẩn)**: 9 ACs (Bao quát trọn vẹn luồng từ Upload PDF/DOCX/arXiv $\rightarrow$ Bóc tách LaTeX/hình/bảng $\rightarrow$ Dịch CNTT/AI $\rightarrow$ Đọc song ngữ Web $\rightarrow$ Tải PDF bản dịch tiếng Việt).
  - 🟡 **Edge Cases & Validation (Điều kiện biên)**: 8 ACs (Bảng biểu phức tạp trong DOCX, giới hạn dung lượng 50MB, công thức đa dòng, co giãn lề trang PDF).
  - 🔴 **Negative Paths (Xử lý lỗi ngoại lệ)**: 8 ACs (File hỏng, DOCX zip lỗi, PDF scan không text layer, arXiv timeout, LLM rate-limit, lỗi render PDF).
- **Trạng thái sẵn sàng triển khai**: 100% User Stories đã được gắn Architecture Guardrails, sẵn sàng đưa vào Sprint thực thi mã nguồn.
