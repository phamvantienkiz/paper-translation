# Architecture Layer — Navigation Map & System Invariants

**Tầng tài liệu**: Architecture Layer (Single Source of Truth)  
**Hệ thống**: Paper Translation  
**Phiên bản**: 1.0  
**Ngày cập nhật**: 2026-10-05  

---

## 1. Giới thiệu & Nguyên tắc Bất biến

Tầng **Architecture Layer** là **Nguồn sự thật duy nhất (Single Source of Truth)** cho toàn bộ hệ thống Paper Translation. Mọi kỹ sư phần mềm và AI Coding Agent khi tham gia phát triển dự án bắt buộc phải đọc và tuân thủ các nguyên tắc thiết kế bất biến được định nghĩa tại đây.

> ⛔ **Nguyên tắc cốt lõi**:
> - Tầng Architecture **TUYỆT ĐỐI KHÔNG chia theo Release**. Không có `architecture-v1` hay `architecture-v2`. Chỉ có một bộ tài liệu duy nhất, liên tục cập nhật theo sự tiến hóa của hệ thống.
> - Bất kỳ thay đổi kiến trúc lớn nào đều phải lập hồ sơ **Architectural Decision Record (ADR)** trước khi sửa đổi các tài liệu thành phần.

---

## 2. Bản đồ Điều hướng Tài liệu Kiến trúc

| Thứ tự | Tài liệu thành phần | Mô tả nội dung chính |
|---|---|---|
| **01** | [01-system-context.md](file:///E:/MyProject/paper-translation/docs/architecture/01-system-context.md) | Bối cảnh hệ thống, Actors, External Systems & Sơ đồ ranh giới Use Case. |
| **02** | [02-high-level-architecture.md](file:///E:/MyProject/paper-translation/docs/architecture/02-high-level-architecture.md) | Kiến trúc tổng thể hệ thống, tính toán BOTEC tải lượng, sơ đồ tôpô & đánh giá đánh đổi kỹ thuật. |
| **03** | [03-service-architecture.md](file:///E:/MyProject/paper-translation/docs/architecture/03-service-architecture.md) | Phân rã dịch vụ Modular Monolith + Worker Pool, ranh giới container & trách nhiệm phân hệ. |
| **04** | [04-deployment-architecture.md](file:///E:/MyProject/paper-translation/docs/architecture/04-deployment-architecture.md) | Cấu hình Docker Compose, hạ tầng Cloud, Reverse Proxy Nginx & mạng. |
| **05** | [05-data-architecture.md](file:///E:/MyProject/paper-translation/docs/architecture/05-data-architecture.md) | Sơ đồ ERD, bảng dữ liệu PostgreSQL, chỉ mục, cấu trúc Redis & Object Storage. |
| **06** | [06-ai-architecture.md](file:///E:/MyProject/paper-translation/docs/architecture/06-ai-architecture.md) | Pipeline AI translation, chiến lược prompt, token masking & tái nạp LaTeX. |
| **07** | [07-security-architecture.md](file:///E:/MyProject/paper-translation/docs/architecture/07-security-architecture.md) | Bảo mật tải tệp (MIME magic bytes), phòng chống SSRF, quản lý khóa bí mật & Rate Limiting. |
| **08** | [08-integration-architecture.md](file:///E:/MyProject/paper-translation/docs/architecture/08-integration-architecture.md) | Chuẩn hóa API REST, khung Envelope, kênh Server-Sent Events & tích hợp ngoại vi (arXiv, LLM). |
| **09** | [09-design-principles.md](file:///E:/MyProject/paper-translation/docs/architecture/09-design-principles.md) | Quy chuẩn Clean Architecture, SOLID, Design Patterns (Repository, Adapter, Service). |
| **10** | [10-folder-structure.md](file:///E:/MyProject/paper-translation/docs/architecture/10-folder-structure.md) | Quy hoạch thư mục dự án Backend (FastAPI) & Frontend (React/Vite). |
| **11–14** | `11`..`14` Frontend System | Thiết kế kiến trúc giao diện, Design System, Dual-Pane State & Color Tokens. |
| **ADR** | [adr/ADR-001.md](file:///E:/MyProject/paper-translation/docs/architecture/adr/ADR-001.md) | Hồ sơ quyết định: Áp dụng Pipeline bất đồng bộ kết hợp Server-Sent Events (SSE). |

---

## 3. Các Bất biến Hệ thống (System Invariants)

1. **Toàn vẹn Công thức Toán:** Cấm gửi trực tiếp cú pháp toán học chưa cô lập qua LLM; bắt buộc phải đi qua cơ chế Token Masking (`<<<MATH_TOKEN_NNN>>>`).
2. **Khớp nối Phân đoạn 1-1:** Bắt buộc duy trì liên kết 1-1 giữa phân đoạn gốc tiếng Anh và bản dịch tiếng Việt thông qua `order_index` và `session_id`.
3. **Ưu tiên Thuật ngữ Glossary:** Mọi thuật ngữ có trong danh mục Glossary bắt buộc phải được ưu tiên áp dụng chuẩn xác trong bản dịch.
4. **Bất đồng bộ hóa Tác vụ Nặng:** Tuyệt đối không thực thi các tác vụ bóc tách PDF hoặc gọi LLM hàng loạt trong luồng chính của HTTP Request.
