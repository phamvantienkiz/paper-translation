# Thiết Kế Kỹ Thuật Chi Tiết (Technical Design) — Release 1 (v3.2 Local-First)

**Tầng tài liệu**: Implementation Layer  
**Release**: release-1 (Personal Core MVP)  
**Phiên bản**: 3.2 (Local-First Priority, Sequential Mutex & 4GB Hard RAM Ceiling)  
**Nguồn tham chiếu**: PRD [docs/implementation/release-1/prd.md](file:///E:/MyProject/paper-translation/docs/implementation/release-1/prd.md)  
**Kiến trúc tham chiếu**: [docs/architecture/02-high-level-architecture.md](file:///E:/MyProject/paper-translation/docs/architecture/02-high-level-architecture.md), [docs/architecture/03-service-architecture.md](file:///E:/MyProject/paper-translation/docs/architecture/03-service-architecture.md), [docs/architecture/06-ai-architecture.md](file:///E:/MyProject/paper-translation/docs/architecture/06-ai-architecture.md)  
**Ngày cập nhật**: 2026-10-23  
**Trạng thái**: Approved  

---

## 1. Tổng quan Luồng Kỹ thuật Release 1 (v3.2 Local-First)

Thiết kế kỹ thuật v3.2 chuyển trọng tâm sang **Local-First**, bảo vệ an toàn phần cứng người dùng qua 5 luồng xử lý chính:
1. **Tiếp nhận tài liệu (Ingestion):** Nhận tệp PDF hoặc tải tự động từ arXiv.
2. **Indra OCR & Chuẩn hóa Tọa độ `[0..1]`:** Bóc tách bố cục 2 cột, chuẩn hóa tọa độ tương đối, kết xuất ảnh nền toàn trang 200 DPI và crop các khối `figure` bằng PyMuPDF.
3. **Thu Hồi Sạch Tài Nguyên OCR (Sequential Mutex Reclamation):** Dừng ThreadPool, giải phóng toàn bộ ONNX sessions và gọi `gc.collect()` để RAM trở về mức tối thiểu trước khi nạp LLM.
4. **Động Cơ Dịch Local-First (llama.cpp & Qwen3 GGUF với Trần Cứng $\le 4.0\text{ GB}$ RAM):** Nạp `Qwen3-1.7B-Q4_K_M.gguf` với `n_ctx=8192` (~2.8GB RAM), khóa trần $n\_ctx \le 16384$, thực thi dịch qua Adaptive Batching (~1500 tokens / batch). Cho phép tùy chọn Cloud Gemini Single-Call.
5. **Tái Hiện 3 Lớp Trên HTML Canvas, Hiển Thị UI Engine Indicator & Xuất PDF:** Vẽ Layer 0 (Base Page) $\rightarrow$ Layer 1 (Smart Redaction `#FFFFFF`) $\rightarrow$ Layer 2 (Auto-Fit Text + KaTeX SVG), hiển thị huy hiệu trạng thái Engine trên UI và xuất PDF 1-click.

---

## 2. Sơ đồ Tuần tự 1: Tiếp nhận PDF, Indra OCR & Thu Hồi Tài Nguyên Tuần Tự

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

    API->>Indra: Chạy indra_ocr.load() -> convert(pdf_path) trong ThreadPool (Chiếm 1.5GB-2.0GB RAM)
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
    
    Note over API,Indra: [SEQUENTIAL MUTEX RECLAMATION]<br>Bắt buộc thu hồi 100% RAM trước khi sang bước dịch
    API->>Indra: IndraOcrService.unload()
    Note over Indra: pool.shutdown(wait=False)<br>del sessions (det, rec, math...)<br>gc.collect() -> RAM trở về tối thiểu
```

---

## 3. Sơ đồ Tuần tự 2: Dịch Thuật Local-First (Llama.cpp Qwen3 $\le$ 4GB RAM) Hoặc Cloud Gemini

```mermaid
sequenceDiagram
    autonumber
    participant Task as ⚙️ Async Pipeline
    participant Filter as 🔍 Smart Block Filter & Packer
    participant Llama as 🧠 LlamaCppService (Local Qwen3 GGUF)
    participant Gemini as 🌐 Google Gemini API (Cloud Option)
    participant DB as 🗄️ SQLite DB
    participant SSE as 📡 SSE Broadcaster

    Task->>Filter: Đọc toàn bộ ocr_blocks theo reading_order ASC
    Filter->>Filter: Đánh dấu is_translatable=False cho page header/footer, figure & mục References
    
    alt Chế độ Mặc định: Local-First (LLM_PROVIDER="llama_cpp")
        Task->>SSE: Emit event (phase='loading_llm', progress=40%, "Đang nạp mô hình Qwen3 GGUF...")
        Task->>Llama: LlamaCppService.get_instance(n_ctx=8192)
        Note over Llama: Khóa trần cứng <= 4.0GB RAM (n_ctx <= 16384)<br>Mặc định n_ctx=8192 chiếm ~2.8GB RAM
        
        loop Từng batch thích ứng (6-8 khối ~1500 tokens)
            Filter->>Llama: Gửi batch kèm [[BLK_XXXX]] + IT/AI Glossary
            Llama-->>Task: Sinh bản dịch bảo toàn [[BLK_XXXX]], LaTeX $..$, <table>
            Task->>Task: Regex bóc tách [[BLK_XXXX]]
            opt Nếu thiếu mã khối (Edge Case)
                Task->>Llama: Fallback dịch đơn lẻ riêng khối bị thiếu
            end
            Task->>SSE: Emit event (phase='translating_local', progress=40% + N%, "Đang dịch qua Qwen3...")
        end
    else Chế độ Tùy chọn: Cloud Gemini (LLM_PROVIDER="gemini")
        Task->>SSE: Emit event (phase='translating_cloud', progress=50%, "Dịch Single-Call qua Gemini...")
        Filter->>Gemini: Single-Call 64K tokens kèm [[BLK_0001]]..[[BLK_NNNN]]
        Gemini-->>Task: Phản hồi toàn văn bản dịch
        Task->>Task: Regex bóc tách [[BLK_XXXX]]
    end

    Task->>DB: UPDATE ocr_blocks SET translated_text=...
    Task->>DB: UPDATE paper_sessions SET status='COMPLETED', progress_percent=100
    Task->>SSE: Emit event (phase='completed', progress=100%, "Hoàn tất! Sẵn sàng xem trên Canvas.")
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

---

## 5. Đặc Tả Hợp Đồng API Chỉ Báo Trạng Thái Engine (UI Engine Status Contract)

### 5.1. Endpoint: `GET /api/v1/system/engine-status`
- **Mục đích:** Cung cấp thông tin thời gian thực về Engine dịch thuật đang kích hoạt và mức giới hạn tài nguyên cho Frontend hiển thị huy hiệu trên Header.
- **Phản hồi mẫu (JSON):**
```json
{
  "active_provider": "llama_cpp",
  "is_local": true,
  "model_name": "Qwen3-1.7B-Q4_K_M.gguf",
  "context_window": 8192,
  "hard_ram_ceiling_gb": 4.0,
  "estimated_ram_usage_gb": 2.8,
  "sequential_mutex_status": "READY",
  "ocr_active": false
}
```

### 5.2. Endpoint: `POST /api/v1/system/engine-switch`
- **Mục đích:** Cho phép người dùng chuyển đổi qua lại giữa `llama_cpp` (Local-First) và `gemini` (Cloud).
- **Yêu cầu (JSON):** `{"provider": "llama_cpp" | "gemini"}`.
- **Cơ chế:** Khi chuyển sang `gemini`, nếu `llama_cpp` đang nạp, hệ thống kích hoạt `unload()` để trả lại RAM. Ngược lại, khi chuyển sang `llama_cpp`, kiểm tra tệp GGUF và nạp Singleton an toàn dưới 4GB RAM.
