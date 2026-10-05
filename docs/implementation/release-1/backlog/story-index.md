# Sổ cái Backlog: Paper Translation — Release 1 (Core MVP)

**Tầng tài liệu**: Implementation Layer  
**Release**: release-1 (Core MVP)  
**Nguồn tham chiếu**: PRD [docs/implementation/release-1/prd.md](file:///E:/MyProject/paper-translation/docs/implementation/release-1/prd.md)  
**Ranh giới hệ thống**: Sơ đồ Use Case tại [docs/architecture/01-system-context.md](file:///E:/MyProject/paper-translation/docs/architecture/01-system-context.md)  
**Ngày cập nhật**: 2026-10-05  
**Trạng thái**: Ready for Sprint Planning  

---

## 1. Ma trận phân bổ User Stories & Traceability

| Mã Story | Tiêu đề User Story | Persona | Ưu tiên | Ánh xạ PRD | Ước lượng | Rào chắn kiến trúc (Guardrails) | Trạng thái |
|---|---|---|---|---|---|---|---|
| [US-001](file:///E:/MyProject/paper-translation/docs/implementation/release-1/backlog/stories/US-001.md) | Tiếp nhận & kiểm tra tệp bài báo PDF upload từ máy cục bộ | Độc giả học thuật | P0 (Must) | FR-01 | 2 SP | 05-data, 07-security, 09-principles | Ready for Dev |
| [US-002](file:///E:/MyProject/paper-translation/docs/implementation/release-1/backlog/stories/US-002.md) | Thu thập tự động tệp PDF & Metadata từ arXiv URL/ID | Kỹ sư R&D / Độc giả | P0 (Must) | FR-01 | 3 SP | 07-security, 08-integ, 09-principles | Ready for Dev |
| [US-003](file:///E:/MyProject/paper-translation/docs/implementation/release-1/backlog/stories/US-003.md) | Bóc tách cấu trúc bài báo & cô lập công thức toán LaTeX | Nhà nghiên cứu | P0 (Must) | FR-02 | 5 SP | 05-data, 09-principles, 10-folder | Ready for Dev |
| [US-004](file:///E:/MyProject/paper-translation/docs/implementation/release-1/backlog/stories/US-004.md) | Quản lý & áp dụng bộ từ điển thuật ngữ chuyên ngành Glossary | Nhà nghiên cứu | P0 (Must) | FR-03 | 3 SP | 05-data, 07-security, 09-principles | Ready for Dev |
| [US-005](file:///E:/MyProject/paper-translation/docs/implementation/release-1/backlog/stories/US-005.md) | Dịch thuật tự động phân đoạn văn bản EN sang VI qua AI Engine | Độc giả khoa học | P0 (Must) | FR-04 | 5 SP | 05-data, 07-security, 08-integ, 09-principles | Ready for Dev |
| [US-006](file:///E:/MyProject/paper-translation/docs/implementation/release-1/backlog/stories/US-006.md) | Giao diện đọc song ngữ Dual-pane cuộn đồng bộ & highlight | Độc giả nghiên cứu | P0 (Must) | FR-05 | 5 SP | 09-principles, 10-folder, 11-frontend | Ready for Dev |
| [US-007](file:///E:/MyProject/paper-translation/docs/implementation/release-1/backlog/stories/US-007.md) | Chỉnh sửa trực tiếp & lưu tức thì phân đoạn bản dịch | Người nghiên cứu | P1 (Should) | FR-06 | 3 SP | 05-data, 09-principles, 11-frontend | Ready for Dev |
| [US-008](file:///E:/MyProject/paper-translation/docs/implementation/release-1/backlog/stories/US-008.md) | Xuất bài báo đã dịch ra định dạng tài liệu Markdown & PDF | Độc giả học thuật | P1 (Should) | FR-07 | 3 SP | 05-data, 08-integ, 09-principles | Ready for Dev |

**Tổng dung lượng ước lượng**: 29 Story Points (SP).

---

## 2. Thống kê độ bao phủ (Fact-list Coverage Summary)

- **Tổng số kịch bản Acceptance Criteria (AC)**: 25 ACs.
  - 🟢 **Happy Paths (Thành công chuẩn)**: 9 ACs (Bao phủ 100% các luồng chính từ Ingestion đến Export).
  - 🟡 **Edge Cases & Validation (Điều kiện biên)**: 8 ACs (Giới hạn dung lượng, định dạng arXiv, công thức phức tạp, trùng lặp glossary, code block).
  - 🔴 **Negative Paths (Lỗi bên thứ 3 & Ngoại lệ)**: 8 ACs (File hỏng, PDF scan không text layer, arXiv timeout, LLM rate-limit, lỗi render PDF).
- **Trạng thái Câu hỏi mở (Open Questions)**: 0 OQ đang chờ (Toàn bộ OQ-01 đến OQ-04 trong PRD đã được chốt và phản ánh vào AC).
