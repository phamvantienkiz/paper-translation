# 01 - Bối Cảnh Hệ Thống & Ranh Giới Phạm Vi (System Context & Boundary)

**Tầng tài liệu**: Architecture Layer (Single Source of Truth)  
**Hệ thống**: Paper Translation (Personal & Open-Source Edition)  
**Phiên bản**: 3.0 (Indra OCR, Single-Call Gemini & HTML Canvas Layout Edition)  
**Ngày cập nhật**: 2026-10-22  
**Trạng thái**: Approved  

---

## 1. Tổng quan Bối cảnh Hệ thống

Hệ thống **Paper Translation** phiên bản 3.0 khắc phục triệt để các sai lầm của các phiên bản trước đó (chia nhỏ đoạn gây mất ngữ cảnh, vỡ bố cục 2 cột và mất hình ảnh). Hệ thống được thiết kế theo luồng kiến trúc mới:

> **Paper PDF $\rightarrow$ Indra OCR (Layout, Text, Reading Order, LaTeX, Tables) $\rightarrow$ Gemini API (Dịch toàn văn 1 lần duy nhất) $\rightarrow$ HTML Canvas Layout Engine (Tái hiện bài báo như bản gốc trên Web) $\rightarrow$ Xuất PDF 1-click.**

---

## 2. Định danh các Tác nhân (Actors & External Systems)

### 2.1. Tác nhân con người (Human Actor)
- **Cá nhân Nhà nghiên cứu / Kỹ sư CNTT & AI:**
  - Tải lên tệp bài báo khoa học định dạng **PDF** (hoặc dán mã/liên kết arXiv).
  - Trực tiếp xem và tương tác với bài báo bản dịch tiếng Việt trên giao diện **HTML Canvas** (giữ nguyên layout 2 cột, vị trí hình ảnh và bảng biểu như bản gốc).
  - Tải về tệp PDF bản dịch tiếng Việt hoàn chỉnh với 1 click.

### 2.2. Hệ thống dịch vụ bên ngoài (External Services)
- **Google Gemini API (Cloud LLM - Single Call):**
  - Cung cấp khả năng tiếp nhận toàn bộ bài báo trong 1 lần gọi duy nhất nhờ cửa sổ ngữ cảnh khổng lồ (1M–2M tokens), đảm bảo tính nhất quán và bảo toàn ngữ cảnh học thuật tuyệt đối.
- **arXiv Repository (Tùy chọn tiện ích):**
  - Tự động tải tệp PDF bài báo gốc khi người dùng nhập URL hoặc arXiv ID.

---

## 3. Sơ đồ Ranh giới Hệ thống & Use Case (System Boundary & Use Cases)

```mermaid
flowchart LR
    subgraph Actors ["Tác nhân (Actors)"]
        User["👤 Kỹ sư / Nhà nghiên cứu CNTT & AI"]
        GeminiAPI["🤖 Google Gemini API<br>(Context Window 1M-2M Tokens)"]
        ArxivAPI["🌐 arXiv API / PDF Storage"]
    end

    subgraph SystemBoundary ["Hệ Thống Paper Translation v3.0"]
        UC1["(1. Nạp bài báo PDF / arXiv)"]
        UC2["(2. Phân tích bố cục & OCR qua Indra OCR)"]
        UC3["(3. Trích xuất hình ảnh & sơ đồ theo BBox)"]
        UC4["(4. Dịch thuật toàn văn trong 1 lần gọi Gemini)"]
        UC5["(5. Tái hiện bài báo bản dịch trên HTML Canvas)"]
        UC6["(6. Xuất tệp PDF bản dịch nguyên vẹn bố cục)"]

        UC1 -.->|<<include>>| UC2
        UC2 -.->|<<include>>| UC3
        UC2 -.->|<<include>>| UC4
        UC4 -.->|<<include>>| UC5
        UC5 -.->|<<extend>>| UC6
    end

    User --> UC1
    User --> UC5
    User --> UC6
    UC1 <-->|Tải tệp PDF| ArxivAPI
    UC4 <-->|Single-call Full-Text Translation| GeminiAPI
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
