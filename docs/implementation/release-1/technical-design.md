# Thiết Kế Kỹ Thuật Chi Tiết (Technical Design) — Release 1 (v3.3 Standalone Local-First)

**Tầng tài liệu**: Implementation Layer  
**Release**: release-1 (Personal Core MVP)  
**Phiên bản**: 3.3 (Standalone `llama.cpp` Server, `Gemma-4-E2B`, 4 P-Cores i5-13500H, 8GB Hard RAM Ceiling & 2000-2500 EN Words Batching)  
**Nguồn tham chiếu**: PRD [docs/implementation/release-1/prd.md](file:///E:/MyProject/paper-translation/docs/implementation/release-1/prd.md)  
**Kiến trúc tham chiếu**: [docs/architecture/02-high-level-architecture.md](file:///E:/MyProject/paper-translation/docs/architecture/02-high-level-architecture.md), [docs/architecture/03-service-architecture.md](file:///E:/MyProject/paper-translation/docs/architecture/03-service-architecture.md), [docs/architecture/06-ai-architecture.md](file:///E:/MyProject/paper-translation/docs/architecture/06-ai-architecture.md)  
**Ngày cập nhật**: 2026-10-23  
**Trạng thái**: Approved  

---

## 1. Tổng quan Luồng Kỹ thuật Release 1 (v3.3 Standalone Local-First)

Thiết kế kỹ thuật v3.3 tách biệt hoàn toàn tiến trình suy luận LLM ra khỏi tiến trình FastAPI và tối ưu hóa cho phần cứng **Intel Core i5-13500H** qua 5 luồng xử lý chính:
1. **Tiếp nhận tài liệu (Ingestion):** Nhận tệp PDF hoặc tải tự động từ arXiv.
2. **Indra OCR & Chuẩn hóa Tọa độ `[0..1]`:** Bóc tách bố cục 2 cột, chuẩn hóa tọa độ tương đối, kết xuất ảnh nền toàn trang 200 DPI và crop các khối `figure` bằng PyMuPDF.
3. **Thu Hồi Sạch Tài Nguyên OCR (Sequential Mutex Reclamation):** Dừng ThreadPool, giải phóng toàn bộ ONNX sessions và gọi `gc.collect()` để trả lại 100% RAM và 4 nhân P-cores trước khi gọi LLM.
4. **Dịch Vụ Serving Độc Lập (`llama.cpp` Server + `gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf`):**
   - Backend quản lý một tiến trình riêng chạy `llama.cpp server` gốc (cài qua `uv/pip`), cấu hình **4 P-cores trên Intel Core i5-13500H (`-t 4 -tb 4`)**, bật tăng tốc phần cứng (`--flash-attn`), giới hạn **RAM $\le 8.0\text{ GB}$**, cửa sổ ngữ cảnh **16K (`n_ctx=16384`)** (hoặc tùy chọn 8K).
   - **Python Client** của Backend đóng gói mỗi lượt gọi gồm **System Prompt + Text bài báo = 2,000 – 2,500 từ tiếng Anh** (~3,000 – 3,800 tokens) và giao tiếp qua mạng nội bộ (`http://127.0.0.1:8081/v1/chat/completions`) với `max_tokens=10240` (dự phòng gấp **2.0 – 2.5 lần** cho tiếng Việt) để không bao giờ tràn context.
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
    
    Note over API,Indra: [SEQUENTIAL MUTEX RECLAMATION]<br>Bắt buộc thu hồi 100% RAM & CPU trước khi sang bước dịch
    API->>Indra: IndraOcrService.unload()
    Note over Indra: pool.shutdown(wait=False)<br>del sessions (det, rec, math...)<br>gc.collect() -> Giải phóng sạch RAM & 4 P-Cores
```

---

## 3. Sơ đồ Tuần tự 2: Dịch Thuật Qua Standalone `llama.cpp` Server (`Gemma-4-E2B` • 4 P-Cores • $\le 8\text{GB}$ RAM) Hoặc Cloud Gemini

```mermaid
sequenceDiagram
    autonumber
    participant Task as ⚙️ Async Pipeline (FastAPI)
    participant Batcher as 📏 Word-Budget Batcher (2000-2500 EN Words)
    participant PyClient as 🔌 Python Internal HTTP Client (httpx)
    participant SrvMgr as 🛠️ LlamaServerManager
    participant LlamaSrv as 🚀 Standalone llama.cpp Server (127.0.0.1:8081)
    participant Gemini as 🌐 Google Gemini API (Cloud Option)
    participant DB as 🗄️ SQLite DB
    participant SSE as 📡 SSE Broadcaster

    Task->>Batcher: Đọc toàn bộ ocr_blocks (is_translatable=True) theo reading_order ASC
    
    alt Chế độ Mặc định: Standalone Local llama.cpp (LLM_PROVIDER="llama_cpp")
        Task->>SSE: Emit event (phase='starting_llm_server', progress=40%, "Đang khởi động dịch vụ llama.cpp server (Gemma-4-E2B)...")
        Task->>SrvMgr: ensure_server_running()
        SrvMgr->>LlamaSrv: Spawn subprocess llama-server (model=gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf, -t 4, -tb 4, -c 16384, -fa, --cache-type-k q8_0)
        Note over LlamaSrv: Sử dụng 4 P-Cores i5-13500H + HW Accel<br>RAM chiếm dụng ~4.2GB (<= 8.0GB Trần Cứng)
        SrvMgr->>LlamaSrv: GET http://127.0.0.1:8081/health
        LlamaSrv-->>SrvMgr: 200 OK {"status": "ok"}
        
        loop Từng lô theo ngân sách từ (System Prompt + Paper Text = 2,000 - 2,500 từ tiếng Anh)
            Batcher->>PyClient: Đóng gói Batch (~3,000 - 3,800 tokens) kèm [[BLK_XXXX]] + IT/AI Glossary
            PyClient->>LlamaSrv: POST http://127.0.0.1:8081/v1/chat/completions (max_tokens=10240)
            Note over LlamaSrv: Output tiếng Việt nở gấp 2.0 - 2.5x (~6,500 - 9,500 tokens)<br>Nằm gọn trong 16K Context -> 0% tràn context
            LlamaSrv-->>PyClient: JSON Response (Translated Vietnamese blocks)
            PyClient->>Task: Regex bóc tách [[BLK_XXXX]]
            opt Nếu thiếu mã khối (Edge Case)
                PyClient->>LlamaSrv: Fallback gọi bù riêng khối bị thiếu qua mạng nội bộ
            end
            Task->>SSE: Emit event (phase='translating_local', progress=40% + N%, "Đang dịch qua Gemma-4-E2B Standalone Server...")
        end
    else Chế độ Tùy chọn: Cloud Gemini (LLM_PROVIDER="gemini")
        Task->>SSE: Emit event (phase='translating_cloud', progress=50%, "Dịch Single-Call qua Gemini...")
        Batcher->>Gemini: Single-Call 64K tokens kèm [[BLK_0001]]..[[BLK_NNNN]]
        Gemini-->>Task: Phản hồi toàn văn bản dịch
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

## 5. Đặc Tả Hợp Đồng API Chỉ Báo Trạng Thái Engine (UI Engine Status Contract v3.3)

### 5.1. Endpoint: `GET /api/v1/system/engine-status`
- **Mục đích:** Cung cấp thông tin thời gian thực về dịch vụ Standalone `llama.cpp` Server, cấu hình phần cứng 4 P-cores i5-13500H, ngân sách từ và mức giới hạn 8GB RAM.
- **Phản hồi mẫu (JSON):**
```json
{
  "active_provider": "llama_cpp",
  "serving_architecture": "standalone_llama_cpp_server",
  "internal_endpoint": "http://127.0.0.1:8081/v1/chat/completions",
  "is_local": true,
  "model_name": "gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf",
  "cpu_target": "Intel Core i5-13500H (4 P-Cores)",
  "threads_config": 4,
  "hardware_acceleration": true,
  "context_window": 16384,
  "supported_context_modes": [8192, 16384],
  "input_word_budget": "2000 - 2500 English words (System Prompt + Paper Text)",
  "output_token_headroom": "10240 tokens (2.0x - 2.5x Vietnamese expansion safe)",
  "hard_ram_ceiling_gb": 8.0,
  "estimated_ram_usage_gb": 4.2,
  "sequential_mutex_status": "READY",
  "ocr_active": false,
  "llama_server_running": true
}
```
