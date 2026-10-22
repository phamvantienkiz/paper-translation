# 03 - Kiến Trúc Dịch Vụ & Phân Rã Thành Phần (Service Architecture & Decomposition)

**Tầng tài liệu**: Architecture Layer (Single Source of Truth)  
**Hệ thống**: Paper Translation (Personal & Open-Source Edition)  
**Phiên bản**: 3.1 (Reviewed & Hardened — Indra OCR, Single-Call Gemini & 3-Layer HTML Canvas)  
**Ngày cập nhật**: 2026-10-22  
**Trạng thái**: Approved  

---

## 1. Chiến lược Phân rã Dịch vụ (Modular Architecture v3.1)

Hệ thống được tổ chức theo kiến trúc **Self-Contained Modular Monolith** (FastAPI + SQLite WAL + Local Disk), đảm bảo chạy mượt mà bằng 1 lệnh duy nhất mà không cần Redis hay GPU:

```mermaid
flowchart LR
    subgraph FrontendSPA ["Frontend (React / Vite)"]
        UI["Web UI Controls<br>(Upload, Zoom, Toggle Original/VI)"]
        CanvasEngine["🎨 3-Layer HTML Canvas Engine<br>(Layer 0: Base Page, Layer 1: Whiteout, Layer 2: VI Text + KaTeX)"]
        PDFExport["📑 Canvas-to-PDF Exporter"]
        UI <--> CanvasEngine
        CanvasEngine --> PDFExport
    end

    subgraph BackendApp ["Backend Application (FastAPI Single Process)"]
        API["API Routers<br>(Ingestion, Sessions, Canvas-Data, Assets)"]
        
        subgraph CoreServices ["Core Domain Services v3.1"]
            IngestionSvc["1. Ingestion Service<br>(PDF Validator & arXiv Downloader)"]
            IndraOcrSvc["2. Indra OCR & Coordinate Normalizer<br>(indra_ocr ONNX + Normalized BBox [0..1])"]
            PageAssetSvc["3. Page Snapshot & Figure Extractor<br>(PyMuPDF Base Page PNG + Figure Crops)"]
            GeminiTranslator["4. Gemini Full-Text Translator<br>(Smart Filter + Single-Call 64K + Auto-Resume)"]
            LayoutMapper["5. Layout Coordinate Mapper<br>(Bind Translated Blocks to Normalized BBoxes)"]
            ProgressHub["6. SSE Broadcaster<br>(Real-time Phase & Progress Streaming)"]
        end

        Repo["Repository Layer<br>(SQLAlchemy Async)"]
    end

    subgraph LocalState ["Local Storage Tier"]
        SQLite[(SQLite DB WAL<br>paper_translation.db)]
        DiskStore[(Local Disk Storage<br>raw_pdfs/, pages/, figures/)]
    end

    UI <-->|HTTP REST & SSE| API
    API --> IngestionSvc
    API --> LayoutMapper
    API <--> ProgressHub

    IngestionSvc --> IndraOcrSvc
    IndraOcrSvc --> PageAssetSvc
    PageAssetSvc --> GeminiTranslator
    GeminiTranslator --> LayoutMapper
    
    IngestionSvc <--> DiskStore
    PageAssetSvc <--> DiskStore
    LayoutMapper --> Repo
    Repo <--> SQLite
    
    IndraOcrSvc -.-> ProgressHub
    PageAssetSvc -.-> ProgressHub
    GeminiTranslator -.-> ProgressHub
    LayoutMapper -.-> ProgressHub
```

---

## 2. Đặc Tả Chi Tiết Từng Dịch Vụ (Detailed Service Specifications)

### 2.1. Ingestion Service (`ingestion_service.py`)
- **Nhiệm vụ:**
  - Xác thực tệp PDF tải lên (kiểm tra magic bytes `%PDF-`, dung lượng $\le 50\text{MB}$).
  - Tự động tải tệp PDF từ `https://arxiv.org/pdf/{arxiv_id}.pdf` khi người dùng nhập mã hoặc URL arXiv.
  - Lưu tệp gốc vào `storage/raw_pdfs/{session_id}.pdf`.

### 2.2. Indra OCR & Coordinate Normalizer Service (`indra_ocr_service.py`)
- **Nhiệm vụ:**
  - Sử dụng API Python chính thức của `indra_ocr` (`conv = indra_ocr.load(threads=4); conv.convert(pdf_path)`).
  - Thu thập danh sách các khối bố cục (`page.blocks`) theo thứ tự đọc chuẩn (`reading_order`), bao gồm:
    - `label`: Nhãn ngữ nghĩa của khối (`text`, `section header`, `title`, `table`, `caption`, `footnote`, `list`, `page header`, `page footer`, `figure`).
    - `box` / `bbox`: Tọa độ pixel trên trang đã được khử nghiêng (`rotation`, `skew`).
    - `text`: Nội dung văn bản hoặc bảng HTML/LaTeX của khối.
  - **Chuẩn hóa Hệ Tọa Độ (Coordinate Normalization):**
    - Quy đổi mọi tọa độ hộp từ pixel của ảnh OCR sang hệ tọa độ tỷ lệ tương đối `[x0_norm, y0_norm, x1_norm, y1_norm]` nằm trong đoạn `[0.0, 1.0]` theo chiều rộng và chiều cao trang:
      $$x_{\text{norm}} = \frac{x_{\text{px}}}{W_{\text{ocr}}}, \quad y_{\text{norm}} = \frac{y_{\text{px}}}{H_{\text{ocr}}}$$
    - Nhờ hệ tọa độ `[0.0 .. 1.0]`, mọi sai lệch về DPI giữa Indra OCR, PyMuPDF (72 DPI) và HTML Canvas đều được loại bỏ hoàn toàn.

### 2.3. Page Snapshot & Figure Extractor Service (`page_asset_service.py`)
- **Nhiệm vụ:**
  - Dùng `PyMuPDF (fitz)` kết xuất từng trang PDF gốc thành ảnh nền độ phân giải cao (`storage/pages/{session_id}/page_{page_num}.png` ở 200 DPI) làm **Layer 0** cho HTML Canvas.
  - Việc có sẵn ảnh nền trang gốc (Layer 0) đảm bảo **100% sơ đồ vector (TikZ/PGFPlots), biểu đồ, đường viền bảng và công thức toán học độc lập** luôn hiển thị nguyên vẹn trên Canvas ngay cả khi OCR không đóng khung riêng cho hình vẽ.
  - Đồng thời, với các khối được đánh nhãn `figure` / `picture`, hệ thống hỗ trợ crop riêng thành `storage/figures/{session_id}/page_{p}_fig_{idx}.png` để phục vụ xem chi tiết.

### 2.4. Gemini Full-Text Translator (`gemini_translator.py`)
- **Nhiệm vụ:**
  - **Bước 1 — Bộ lọc Khối Cần Dịch (Smart Translatable Filter):**
    - Đánh dấu `is_translatable = False` đối với:
      1. Các khối `page header`, `page footer` (số trang, tên hội nghị ở lề trang).
      2. Các khối thuộc mục **References / Bibliography** (bắt đầu từ tiêu đề `References` hoặc `Bibliography` ở cuối bài báo) — vì tài liệu tham khảo quốc tế cần giữ nguyên tên tiếng Anh để tra cứu và chiếm tới 20–30% độ dài bài báo.
      3. Các khối chỉ chứa ký hiệu toán học thuần túy hoặc số liệu.
  - **Bước 2 — Đóng gói Toàn văn & Gọi Gemini Single-Call:**
    - Gom tất cả các khối `is_translatable = True` của toàn bộ bài báo thành một chuỗi văn bản có cấu trúc:
      ```text
      [[BLOCK_ID_0001]]
      Attention Is All You Need
      [[BLOCK_ID_0002]]
      The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...
      ```
    - Gửi trong **1 request duy nhất** tới Google Gemini API (mặc định model `gemini-3.5-flash-lite`) với tham số `max_tokens: 65536` và bộ từ điển chuyên ngành `IT_AI_GLOSSARY`.
  - **Bước 3 — Kiểm tra Toàn vẹn & Auto-Continuation Guard:**
    - Bóc tách kết quả dịch theo regex `\[\[BLOCK_ID_(\d{4})\]\]`.
    - Nếu bài báo cực dài (> 40 trang) khiến phản hồi chạm trần `finish_reason == "length"` hoặc còn thiếu một số `block_id` cuối, dịch vụ tự động gửi 1 lệnh tiếp nối (continuation call) chỉ chứa các `block_id` còn thiếu kèm ngữ cảnh tóm tắt, đảm bảo 100% khối văn bản đều được dịch đầy đủ.

### 2.5. Layout Coordinate Mapper (`layout_mapper.py`)
- **Nhiệm vụ:**
  - Ánh xạ từng bản dịch tiếng Việt vào đúng bản ghi `ocr_blocks` trong SQLite.
  - Cung cấp dữ liệu hoàn chỉnh qua endpoint `GET /api/v1/sessions/{session_id}/canvas-data` bao gồm kích thước chuẩn của từng trang (`width_pt`, `height_pt`, `page_image_url`) và danh sách các khối (`block_id`, `label`, `bbox_norm`, `original_text`, `translated_text`, `is_translatable`).

### 2.6. Frontend 3-Layer HTML Canvas Engine (`CanvasPaperViewer.tsx`)
- **Nhiệm vụ:**
  - Khởi tạo `<canvas>` cho từng trang theo đúng tỷ lệ `width_pt / height_pt` nhân với `devicePixelRatio` và mức `zoom`.
  - **Layer 0 (Base Page):** Vẽ `page_image_url` lên toàn bộ diện tích Canvas.
  - **Layer 1 (Smart Redaction):** Duyệt qua các khối có `is_translatable == true` và đã có `translated_text`; vẽ hình chữ nhật màu nền (`#FFFFFF`) phủ kín tọa độ `[x0 * W, y0 * H, (x1 - x0) * W, (y1 - y0) * H]` để xóa chữ tiếng Anh gốc mà không chạm vào bất kỳ hình ảnh hay sơ đồ nào bên ngoài hộp.
  - **Layer 2 (Translated Text & Math Rendering):**
    - Nếu khối chỉ chứa văn bản thuần: Dùng thuật toán Binary-Search Font Auto-Scaling (tìm cỡ chữ lớn nhất từ `6px` đến `28px` sao cho sau khi bẻ dòng `word-wrap` chiều cao văn bản nằm vừa khít trong chiều cao hộp `H_box`) và vẽ trực tiếp lên Canvas.
    - Nếu khối chứa công thức toán LaTeX (`$...$`, `$$...$$`) hoặc bảng HTML (`<table>`): Kết xuất thông qua KaTeX + SVG `foreignObject` và vẽ ảnh SVG sắc nét trực tiếp vào đúng tọa độ hộp trên Canvas.
  - Hỗ trợ chế độ xem đối chiếu (bật/tắt Layer 1+2 để xem tức thì bản gốc tiếng Anh bên dưới hoặc xem song song 2 trang) và xuất toàn bộ các trang Canvas ra tệp PDF chất lượng cao.
