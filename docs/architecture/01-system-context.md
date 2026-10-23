# 01 - Bối Cảnh Hệ Thống & Ranh Giới Phạm Vi (System Context & Boundary)

**Tầng tài liệu**: Architecture Layer (Single Source of Truth)  
**Hệ thống**: Paper Translation (Personal & Open-Source Edition)  
**Phiên bản**: 3.0 (Indra OCR, Single-Call Gemini & HTML Canvas Layout Edition)  
**Ngày cập nhật**: 2026-10-22  
**Trạng thái**: Approved  

---

## 1. Tổng quan Bối cảnh Hệ thống

Hệ thống **Paper Translation** phiên bản 3.2 chuyển đổi trọng tâm sang kiến trúc **Local-First (Ngoại Tuyến & Bảo Mật 100%)**:

> **Paper PDF $\rightarrow$ Indra OCR (Phân tích bố cục & văn bản) $\rightarrow$ [Thu hồi 100% RAM OCR] $\rightarrow$ Local LLM Engine (llama.cpp / Qwen3 GGUF $\le 4\text{GB}$ RAM) $\rightarrow$ HTML Canvas Layout Engine $\rightarrow$ Xuất PDF 1-click.**

---

## 2. Định danh các Tác nhân (Actors & Internal/External Systems)

### 2.1. Tác nhân con người (Human Actor)
- **Cá nhân Nhà nghiên cứu / Kỹ sư CNTT & AI:**
  - Tải lên tệp bài báo khoa học định dạng **PDF** (hoặc dán mã/liên kết arXiv).
  - Quan sát trạng thái xử lý trên UI thông qua **Engine Status Badge** (`Local LLM` vs `Cloud API`).
  - Trực tiếp xem và tương tác với bài báo bản dịch tiếng Việt trên giao diện **HTML Canvas** (giữ nguyên layout 2 cột, vị trí hình ảnh và bảng biểu như bản gốc).
  - Tải về tệp PDF bản dịch tiếng Việt hoàn chỉnh với 1 click.

### 2.2. Hệ thống dịch vụ xử lý (Processing Engines)
- **Local LLM Engine (`llama.cpp` + `Qwen3-1.7B-Q4_K_M.gguf` - Mặc định ưu tiên):**
  - Khởi tạo và quản lý trực tiếp bởi FastAPI backend; hoạt động ngoại tuyến 100% (chi phí 0đ, bảo mật dữ liệu tuyệt đối).
  - Giới hạn trần cứng: `n_ctx=8192` (mặc định ~2.8GB RAM), tối đa không vượt quá `16384` ($\le 4.0\text{ GB}$ RAM).
- **Google Gemini API (Cloud LLM - Tùy chọn thứ hai):**
  - Cung cấp khả năng dịch Single-Call toàn bài khi người dùng chọn chế độ Cloud.
- **arXiv Repository (Tùy chọn tiện ích):**
  - Tự động tải tệp PDF bài báo gốc khi người dùng nhập URL hoặc arXiv ID.

---

## 3. Sơ đồ Ranh giới Hệ thống & Use Case (System Boundary & Use Cases)

```mermaid
flowchart LR
    subgraph Actors ["Tác nhân (Actors)"]
        User["👤 Kỹ sư / Nhà nghiên cứu CNTT & AI"]
        GeminiAPI["🌐 Google Gemini API (Cloud Option)"]
        ArxivAPI["🌐 arXiv Repository"]
    end

    subgraph SystemBoundary ["Hệ Thống Paper Translation v3.2 (Local-First)"]
        UC1["(1. Nạp bài báo PDF / arXiv)"]
        UC2["(2. Giám sát & Chọn Engine trên UI: Local vs Cloud)"]
        UC3["(3. Phân tích bố cục qua Indra OCR)"]
        UC4["(4. Thu hồi sạch RAM OCR trước khi nạp LLM)"]
        UC5["(5. Dịch ngoại tuyến qua Local LLM Qwen3 <= 4GB RAM)"]
        UC6["(6. Dịch qua Cloud Gemini API)"]
        UC7["(7. Tái hiện bài báo bản dịch trên HTML Canvas)"]
        UC8["(8. Xuất tệp PDF bản dịch nguyên vẹn bố cục)"]

        UC1 --> UC2
        UC2 --> UC3
        UC3 -.->|<<sequential mutex>>| UC4
        UC4 -.->|<<release mem before load>>| UC5
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

## 4. Dòng chảy Nghiệp vụ (High-Level Process Flow)

```mermaid
flowchart TD
    Start([Bắt đầu]) --> Upload[Người dùng tải file PDF hoặc nhập arXiv ID]
    Upload --> RunIndra[Indra OCR chạy trên CPU: Bóc tách Bounding Boxes, Layout, Text, LaTeX, Tables]
    RunIndra --> CropImages[Trích xuất hình ảnh chất lượng cao theo BBox của Indra]
    RunIndra --> PackPrompt[Đóng gói toàn văn bài báo kèm Block IDs & Chỉ dẫn thuật ngữ IT & AI]
    PackPrompt --> CallGemini[Gọi Gemini API trong 1 lần gọi duy nhất - Full Context Translation]
    CallGemini --> ParseTranslation[Tiếp nhận bản dịch tiếng Việt, ánh xạ vào cấu trúc Block IDs]
    CropImages --> RenderCanvas[HTML Canvas Engine: Vẽ nền, đặt ảnh sơ đồ & điền văn bản dịch theo tọa độ BBox gốc]
    ParseTranslation --> RenderCanvas
    RenderCanvas --> WebViewer[Người dùng tương tác xem bài báo dịch trên Web UI]
    WebViewer --> ExportPDF[Xuất tệp PDF bản dịch chuẩn bố cục gốc]
    ExportPDF --> End([Hoàn tất])
```
