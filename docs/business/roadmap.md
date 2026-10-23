# Product Roadmap — Paper Translation (Personal & Open-Source)

**Tầng tài liệu**: Business Layer  
**Dự án**: Paper Translation  
**Phiên bản**: 3.1 (Indra OCR, Single-Call Gemini & 3-Layer HTML Canvas Edition)  
**Ngày cập nhật**: 2026-10-22  
**Trạng thái**: Approved  

---

## 1. Chiến lược Phân kỳ Lộ trình

```mermaid
flowchart LR
    H1["Horizon 1: Release 1 (v3.1 Core MVP)<br>Indra OCR + Gemini Single-Call + 3-Layer HTML Canvas & PDF Export"] --> H2["Horizon 2: Release 2 (Open-Source Community)<br>Đóng gói Docker 1-click, Chỉnh sửa trực tiếp trên Canvas & Chia sẻ Glossary"]
```

---

## 2. Chi tiết các Đợt phát hành

### Horizon 1: Release 1 (v3.2) — Local-First Layout-Preserving Core MVP
- **Mục tiêu:** Giải quyết triệt để bài toán dịch bài báo khoa học CNTT & AI với triết lý **Local-First**, bảo vệ dữ liệu nội bộ 100%, chi phí 0đ, không bao giờ gây gián đoạn hệ thống nhờ rào chắn giới hạn trần cứng $\le 4.0\text{ GB}$ RAM.
- **Tính năng trọng tâm:**
  - [ ] Tiếp nhận tệp bài báo **PDF** từ máy tính hoặc tải tự động qua mã/liên kết **arXiv**.
  - [ ] Tích hợp **Indra OCR (`indra_ocr` ONNX CPU)** bóc tách bố cục 2 cột, thứ tự đọc, bảng biểu HTML, công thức LaTeX và chuẩn hóa hệ tọa độ `[0.0 .. 1.0]`.
  - [ ] **Bộ điều phối tuần tự tài nguyên (Sequential Mutex Execution)**: Giải phóng sạch 100% tài nguyên RAM của Indra OCR trước khi nạp mô hình LLM.
  - [ ] **Động cơ dịch Local-First mặc định (`llama.cpp` + `Qwen3-1.7B-Q4_K_M.gguf`)**: Quản lý trực tiếp bởi FastAPI, chạy ngoại tuyến 100%, cấu hình `n_ctx=8192` (~2.8GB RAM) và khóa trần cứng tối đa 4.0GB RAM. Tùy chọn Cloud Gemini Single-Call giữ vai trò thứ hai.
  - [ ] **Chỉ báo động cơ trên UI**: Hiển thị rõ ràng huy hiệu trạng thái đang xử lý bằng Local LLM hay Cloud API.
  - [ ] Kết xuất ảnh nền trang gốc độ phân giải cao (Layer 0) và crop riêng các khối hình ảnh (`figure`) qua `PyMuPDF`.
  - [ ] Giao diện **3-Layer HTML5 Canvas Viewer**: Tái hiện bài báo bản dịch tiếng Việt giống hệt bản gốc (hỗ trợ Zoom, Pan, bật/tắt đối chiếu tức thì với lớp tiếng Anh gốc).
  - [ ] Xuất và tải về **tệp PDF bản dịch tiếng Việt** giữ nguyên vẹn bố cục gốc chỉ với 1 click.

---

### Horizon 2: Release 2 — Open-Source Community & Advanced Canvas Editing
- **Mục tiêu:** Đóng gói mã nguồn mở tiện lợi và mở rộng khả năng tương tác nâng cao trên Canvas.
- **Tính năng dự kiến:**
  - [ ] Đóng gói Docker Compose chạy 1-click (tích hợp sẵn trọng số ONNX của Indra OCR).
  - [ ] Tính năng nhấp đúp vào bất kỳ khối văn bản nào trên HTML Canvas để chỉnh sửa câu dịch tiếng Việt và tự động vẽ lại khối đó theo thời gian thực.
  - [ ] Lớp Transparent DOM Text Overlay phía trên Canvas giúp người dùng bôi đen và copy văn bản tiếng Việt trực tiếp.
