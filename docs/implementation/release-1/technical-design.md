# Thiết Kế Kỹ Thuật Chi Tiết (Technical Design) — Release 1 (v3.1)

**Tầng tài liệu**: Implementation Layer  
**Release**: release-1 (Personal Core MVP)  
**Phiên bản**: 3.1 (Reviewed & Hardened — Indra OCR, Single-Call Gemini & 3-Layer HTML Canvas)  
**Nguồn tham chiếu**: PRD [docs/implementation/release-1/prd.md](file:///E:/MyProject/paper-translation/docs/implementation/release-1/prd.md)  
**Kiến trúc tham chiếu**: [docs/architecture/02-high-level-architecture.md](file:///E:/MyProject/paper-translation/docs/architecture/02-high-level-architecture.md) & [docs/architecture/05-data-architecture.md](file:///E:/MyProject/paper-translation/docs/architecture/05-data-architecture.md)  
**Ngày cập nhật**: 2026-10-22  
**Trạng thái**: Approved  

---

## 1. Tổng quan Luồng Kỹ thuật Release 1 (v3.1)

Thiết kế kỹ thuật v3.1 bao gồm 4 luồng xử lý chính đã được gia cố để loại bỏ mọi rủi ro lệch tọa độ, mất sơ đồ vector, lỗi hiển thị công thức LaTeX trên Canvas và chạm trần output token:
1. **Tiếp nhận tài liệu (Ingestion):** Nhận tệp PDF hoặc tải tự động từ arXiv.
2. **Indra OCR, Chuẩn hóa Tọa độ `[0..1]` & Kết xuất Ảnh Nền Trang (Layer 0):** Bóc tách bố cục 2 cột, chuẩn hóa tọa độ tương đối, kết xuất ảnh nền toàn trang 200 DPI và crop các khối `figure` bằng PyMuPDF.
3. **Lọc Thông Minh & Dịch Toàn Văn 1 Lần Gọi Qua Gemini (`max_tokens=65536`):** Lọc bỏ mục `References` và `page header/footer`, đóng gói toàn văn kèm mã `[[BLK_XXXX]]`, dịch trong 1 request duy nhất kèm cơ chế Auto-Continuation Guard.
4. **Tái Hiện 3 Lớp Trên HTML Canvas & Xuất PDF:** Vẽ Layer 0 (Base Page) $\rightarrow$ Layer 1 (Smart Redaction `#FFFFFF` trên các khối dịch) $\rightarrow$ Layer 2 (Văn bản tiếng Việt Auto-Fit + KaTeX SVG) và xuất PDF.

---

## 2. Sơ đồ Tuần tự 1: Tiếp nhận PDF, Indra OCR & Chuẩn Hóa Tọa Độ

```mermaid
sequenceDiagram
    autonumber
    actor User as 👤 Kỹ sư / Nhà nghiên cứu
    participant Browser as 🌐 Web UI (React)
    participant API as ⚡ FastAPI Backend
    participant Indra as ⚡ Indra OCR (ONNX CPU)
    participant PyMuPDF as 🖼️ Page & Asset Renderer (fitz)
    participant Storage as 📁 Local Disk (storage/)
    participant DB as 🗄️ SQLite DB

    User->>Browser: Chọn tệp PDF hoặc nhập arXiv ID
    Browser->>API: POST /api/v1/ingestion/upload (hoặc /arxiv)
    API->>Storage: Lưu PDF gốc vào storage/raw_pdfs/{session_id}.pdf
    API->>DB: INSERT INTO paper_sessions (id, status='PENDING')
    API-->>Browser: 202 Accepted (session_id)
    Browser->>Browser: Mở kết nối SSE /api/v1/sessions/{session_id}/progress

    API->>Indra: Chạy indra_ocr.load() -> convert(pdf_path) trong ThreadPool
    Indra-->>API: Trả về từng trang: rotation, skew, blocks(label, box, text)

    loop Từng trang PDF (page_number = 1..N)
        API->>PyMuPDF: Mở trang PDF, lấy kích thước chuẩn (width_pt, height_pt)
        PyMuPDF->>Storage: Kết xuất ảnh nền trang 200 DPI -> storage/pages/{session_id}/page_{n}.png
        API->>API: Quy đổi tọa độ box pixel của Indra sang Normalized BBox [0.0 .. 1.0]
        opt Nếu block.label == 'figure'
            PyMuPDF->>Storage: Crop ảnh theo BBox -> storage/figures/{session_id}/page_{n}_fig_{k}.png
        end
    end

    API->>DB: Lưu paper_pages và ocr_blocks (kèm cờ is_translatable)
```

---

## 3. Sơ đồ Tuần tự 2: Bộ Lọc Thông Minh & Dịch Toàn Văn Qua Gemini Single-Call

```mermaid
sequenceDiagram
    autonumber
    participant Task as ⚙️ Async Pipeline
    participant Filter as 🔍 Smart Block Filter & Packer
    participant Gemini as 🤖 Google Gemini API (Single-Call)
    participant DB as 🗄️ SQLite DB
    participant SSE as 📡 SSE Broadcaster

    Task->>SSE: Emit event (step='TRANSLATING', progress=50%, "Đang chuẩn bị dữ liệu và dịch toàn văn qua Gemini...")
    Task->>Filter: Đọc toàn bộ ocr_blocks theo reading_order ASC
    Filter->>Filter: Đánh dấu is_translatable=False cho page header/footer, figure & mục References
    Filter->>Filter: Đóng gói các khối is_translatable=True kèm thẻ [[BLK_0001]]..[[BLK_NNNN]] + IT/AI Glossary
    
    Task->>Gemini: POST /v1beta/openai/chat/completions (Full-text prompt, max_tokens=65536)
    Note over Gemini: Dịch toàn bài trong 1 lần gọi duy nhất,<br>giữ nguyên LaTeX $..$, <table> và [[BLK_XXXX]]
    Gemini-->>Task: Trả về bản dịch tiếng Việt kèm [[BLK_XXXX]]

    Task->>Task: Parse regex [[BLK_XXXX]] ánh xạ vào từng khối
    opt Nếu bài báo cực dài (>40 trang) làm thiếu các BLK cuối (finish_reason == 'length')
        Task->>Gemini: Gọi Auto-Continuation cho các BLK còn thiếu (giữ nguyên ngữ cảnh)
        Gemini-->>Task: Trả về phần dịch của các BLK cuối
    end

    Task->>DB: UPDATE ocr_blocks SET translated_text=...
    Task->>DB: UPDATE paper_sessions SET status='COMPLETED', progress_percent=100
    Task->>SSE: Emit event (step='COMPLETED', progress=100%, "Hoàn tất! Sẵn sàng xem trên HTML Canvas.")
```

---

## 4. Sơ đồ Tuần tự 3: Kết Xuất 3 Lớp Trên HTML Canvas & Xuất PDF

```mermaid
sequenceDiagram
    autonumber
    actor User as 👤 Kỹ sư / Nhà nghiên cứu
    participant Browser as 🌐 Web UI (React)
    participant Canvas as 🎨 3-Layer HTML Canvas Engine
    participant API as ⚡ FastAPI Backend
    participant DB as 🗄️ SQLite DB

    Browser->>API: GET /api/v1/sessions/{session_id}/canvas-data
    API->>DB: SELECT paper_pages & ocr_blocks WHERE session_id = ...
    DB-->>API: Danh sách trang (page_image_url, width_pt, height_pt) & blocks (bbox_norm, translated_text)
    API-->>Browser: 200 OK (Canvas Layout Payload)

    loop Từng trang bài báo
        Browser->>Canvas: Khởi tạo <canvas> theo tỷ lệ (width_pt x height_pt) * zoom * devicePixelRatio
        Canvas->>Canvas: [Layer 0] Vẽ ảnh nền trang gốc (page_image_url) -> Bảo toàn 100% hình vẽ, vector TikZ, bảng
        loop Từng khối có is_translatable == true & có translated_text
            Canvas->>Canvas: Quy đổi bbox_norm [0..1] sang tọa độ Canvas [x, y, w, h]
            Canvas->>Canvas: [Layer 1] Vẽ hộp trắng (#FFFFFF) phủ lên [x, y, w, h] để xóa chữ tiếng Anh gốc
            alt Khối chứa công thức LaTeX ($..$) hoặc bảng HTML (<table>)
                Canvas->>Canvas: [Layer 2a] Render KaTeX + HTML vào SVG foreignObject (Auto-fit font) -> Vẽ lên [x, y, w, h]
            else Khối văn bản thuần túy
                Canvas->>Canvas: [Layer 2b] Binary-Search Font Auto-Scaling + Word-Wrap -> Vẽ chữ tiếng Việt lên [x, y, w, h]
            end
        end
    end

    User->>Browser: Xem bài báo: Zoom, Pan, giữ nút "Xem bản gốc" (ẩn tạm Layer 1+2) hoặc sửa khối
    
    opt Người dùng bấm "Xuất PDF Bản Dịch"
        User->>Browser: Click "Xuất PDF"
        Browser->>Canvas: Kết xuất tuần tự các trang Canvas sang tệp PDF chất lượng cao
        Browser-->>User: Tải tệp [Ten-Bai-Bao]-vi.pdf về máy
    end
```
