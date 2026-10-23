# 01 - Bối Cảnh Hệ Thống & Ranh Giới Phạm Vi (System Context & Boundary)

**Tầng tài liệu**: Architecture Layer (Single Source of Truth)  
**Hệ thống**: Paper Translation (Personal & Open-Source Edition)  
**Phiên bản**: 3.3 (Indra OCR, Standalone Llama.cpp Server + Gemma-4-E2B & 3-Layer HTML Canvas Edition)  
**Ngày cập nhật**: 2026-10-23  
**Trạng thái**: Approved  

---

## 1. Tổng quan Bối cảnh Hệ thống

Hệ thống **Paper Translation** phiên bản 3.3 áp dụng kiến trúc **Standalone Local-First Serving (Tách Biệt Tiến Trình Suy Luận & Tối Ưu Phần Cứng)**:

> **Paper PDF $\rightarrow$ Indra OCR (Phân tích bố cục & văn bản) $\rightarrow$ [Thu hồi 100% RAM OCR] $\rightarrow$ Python Internal Client $\leftrightarrow$ Standalone `llama.cpp` Server (`gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf` • 4 P-Cores i5-13500H • $\le 8\text{GB}$ RAM • 16K/8K Ctx) $\rightarrow$ 3-Layer HTML Canvas Layout Engine $\rightarrow$ Xuất PDF 1-click.**

---

## 2. Định danh các Tác nhân (Actors & Internal/External Systems)

### 2.1. Tác nhân con người (Human Actor)
- **Cá nhân Nhà nghiên cứu / Kỹ sư CNTT & AI:**
  - Tải lên tệp bài báo khoa học định dạng **PDF** (hoặc dán mã/liên kết arXiv).
  - Quan sát trạng thái xử lý trên UI thông qua **Engine Status Badge** (`Local LLM: Gemma-4-E2B` vs `Cloud API`).
  - Trực tiếp xem và tương tác với bài báo bản dịch tiếng Việt trên giao diện **HTML Canvas** (giữ nguyên layout 2 cột, vị trí hình ảnh và bảng biểu như bản gốc).
  - Tải về tệp PDF bản dịch tiếng Việt hoàn chỉnh với 1 click.

### 2.2. Hệ thống dịch vụ xử lý (Processing Engines)
- **Standalone Local `llama.cpp` Server (`gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf` - Mặc định ưu tiên):**
  - Được cài đặt trực tiếp từ thư viện `llama.cpp` gốc thông qua `uv/pip`, không nhúng gộp vào bên trong tiến trình FastAPI mà chạy như một **dịch vụ serving riêng biệt** dưới sự quản lý vòng đời của Backend.
  - Giao tiếp với FastAPI thông qua **Python Async HTTP Client** qua mạng nội bộ (`http://127.0.0.1:8081/v1/chat/completions`).
  - Cấu hình phần cứng chuyên biệt: Khai thác **4 P-cores trên Intel Core i5-13500H**, cho phép tăng tốc phần cứng, giới hạn trần cứng **RAM $\le 8.0\text{ GB}$**, cửa sổ ngữ cảnh **16K tokens (`n_ctx=16384`)** (hoặc tùy chọn 8K).
  - Quy tắc phân lô: Mỗi lượt gọi đóng gói **2,000 – 2,500 từ tiếng Anh** (bao gồm System Prompt + Text của bài báo), dành dư không gian đầu ra gấp **2.0 – 2.5 lần** cho văn bản tiếng Việt để không bao giờ bị tràn context.
- **Google Gemini API (Cloud LLM - Tùy chọn thứ hai):**
  - Cung cấp khả năng dịch Single-Call toàn bài khi người dùng chọn chế độ Cloud.
- **arXiv Repository (Tùy chọn tiện ích):**
  - Tự động tải tệp PDF bài báo gốc khi người dùng nhập URL hoặc arXiv ID.

---

## 3. Sơ đồ Ranh giới Hệ thống & Use Case (System Boundary & Use Cases v3.3)

```mermaid
flowchart LR
    subgraph Actors ["Tác nhân (Actors)"]
        User["👤 Kỹ sư / Nhà nghiên cứu CNTT & AI"]
        GeminiAPI["🌐 Google Gemini API (Cloud Option)"]
        ArxivAPI["🌐 arXiv Repository"]
    end

    subgraph SystemBoundary ["Hệ Thống Paper Translation v3.3 (Managed Backend Ecosystem)"]
        subgraph FastAPIProcess ["Tiến trình FastAPI Backend"]
            UC1["(1. Nạp bài báo PDF / arXiv)"]
            UC2["(2. Giám sát & Chọn Engine trên UI: Local vs Cloud)"]
            UC3["(3. Phân tích bố cục qua Indra OCR)"]
            UC4["(4. Thu hồi sạch RAM OCR trước khi gọi LLM)"]
            UC5["(5. Phân lô 2000-2500 từ EN & Gọi qua Python Client nội bộ)"]
            UC6["(6. Dịch tùy chọn qua Cloud Gemini API)"]
            UC7["(7. Tái hiện bài báo bản dịch trên 3-Layer HTML Canvas)"]
            UC8["(8. Xuất tệp PDF bản dịch nguyên vẹn bố cục)"]
        end

        subgraph StandaloneLlamaService ["Tiến trình Serving Riêng: llama.cpp Server (127.0.0.1:8081)"]
            UC5_Srv["(Suy luận Gemma-4-E2B Q4_K_XL<br>4 P-Cores i5-13500H • <= 8GB RAM • 16K Ctx)"]
        end

        UC1 --> UC2
        UC2 --> UC3
        UC3 -.->|<<sequential mutex>>| UC4
        UC4 -.->|<<start/ensure server>>| UC5
        UC5 <-->|Loopback HTTP /v1/chat/completions| UC5_Srv
        UC2 -.->|<<tùy chọn>>| UC6
        UC5 --> UC7
        UC6 --> UC7
        UC7 -.->|<<extend>>| UC8
    end

    User --> UC1
    User --> UC2
    User --> UC7
    User --> UC8
    UC1 <-->|Tải tệp PDF| ArxivAPI
    UC6 <-->|Cloud Translation| GeminiAPI
```

---

## 4. Dòng chảy Nghiệp vụ (High-Level Process Flow v3.3)

```mermaid
flowchart TD
    Start([Bắt đầu]) --> Upload[Người dùng tải file PDF hoặc nhập arXiv ID]
    Upload --> RunIndra[Indra OCR chạy trên CPU: Bóc tách Bounding Boxes, Layout, Text, LaTeX, Tables]
    RunIndra --> CropImages[Kết xuất ảnh nền trang 200 DPI Layer 0 & Trích xuất hình ảnh theo BBox]
    RunIndra --> ReclaimOCR["Thu hồi sạch 100% RAM của Indra OCR (unload & gc.collect)"]
    ReclaimOCR --> StartLlamaSrv["Backend Service khởi chạy tiến trình riêng llama.cpp Server<br>(gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf | 4 P-Cores i5-13500H | <= 8GB RAM | 16K Ctx)"]
    StartLlamaSrv --> PackWordBatch["Gom lô thích ứng theo số từ: System Prompt + Text bài báo = 2,000 - 2,500 từ tiếng Anh"]
    PackWordBatch --> CallLocalClient["Python Client gọi tới llama.cpp Server qua mạng nội bộ (127.0.0.1:8081)<br>Đảm bảo Output tiếng Việt dư gấp 2 - 2.5 lần Input không bị tràn context"]
    CallLocalClient --> ParseTranslation[Tiếp nhận bản dịch tiếng Việt, ánh xạ vào cấu trúc Block IDs]
    CropImages --> RenderCanvas[3-Layer HTML Canvas Engine: Vẽ nền, xóa trắng thông minh & điền văn bản dịch]
    ParseTranslation --> RenderCanvas
    RenderCanvas --> WebViewer[Người dùng tương tác xem bài báo dịch trên Web UI]
    WebViewer --> ExportPDF[Xuất tệp PDF bản dịch chuẩn bố cục gốc]
    ExportPDF --> End([Hoàn tất])
```
