# Thiết Kế Kỹ Thuật Chi Tiết (Technical Design) — Release 1 (Personal Core MVP)

**Tầng tài liệu**: Implementation Layer  
**Release**: release-1 (Personal Core MVP)  
**Phiên bản**: 2.0 (Scaled Down & Focused)  
**Nguồn tham chiếu**: PRD [docs/implementation/release-1/prd.md](file:///E:/MyProject/paper-translation/docs/implementation/release-1/prd.md)  
**Kiến trúc tham chiếu**: [docs/architecture/02-high-level-architecture.md](file:///E:/MyProject/paper-translation/docs/architecture/02-high-level-architecture.md) & [docs/architecture/05-data-architecture.md](file:///E:/MyProject/paper-translation/docs/architecture/05-data-architecture.md)  
**Ngày cập nhật**: 2026-10-05  
**Trạng thái**: Approved  

---

## 1. Tổng quan Luồng Kỹ thuật Release 1

Thiết kế kỹ thuật Release 1 tập trung phục vụ trải nghiệm cá nhân mượt mà với 4 luồng tuần tự (Sequence Flows) chính:
1. **Tiếp nhận đa định dạng:** Hỗ trợ upload tệp **PDF**, tệp **DOCX** và dán link **arXiv**.
2. **Bóc tách & Bảo toàn:** Bóc tách văn bản, cô lập công thức toán LaTeX, trích xuất hình ảnh minh họa và bảng biểu.
3. **Dịch thuật ngữ cảnh CNTT & AI:** Gom lô phân đoạn, gửi qua LLM và tái nạp công thức toán LaTeX.
4. **Giao diện Web song ngữ & Tải PDF bản dịch:** Hiển thị đối xứng 2 cột trên trình duyệt và cho phép tải về tệp PDF tiếng Việt hoàn chỉnh giữ 100% LaTeX, hình, bảng.

---

## 2. Sơ đồ Tuần tự 1: Tiếp nhận Đa định dạng (PDF & DOCX & arXiv)

```mermaid
sequenceDiagram
    autonumber
    actor User as 👤 Bạn (Cá nhân)
    participant Browser as 🌐 Web UI (React)
    participant API as ⚡ FastAPI Backend
    participant Storage as 📁 Local Disk (storage/)
    participant DB as 🗄️ SQLite DB

    alt 1. Tải lên tệp PDF hoặc DOCX (US-001 & US-002)
        User->>Browser: Chọn tệp PDF hoặc DOCX (<= 50MB)
        Browser->>API: POST /api/v1/ingestion/upload (Multipart FormData)
        API->>API: Kiểm tra định dạng (MIME / Extension)
        API->>Storage: Lưu tệp vào storage/raw/{session_id}/original.[pdf|docx]
        API->>DB: INSERT INTO paper_sessions (source_type, status='PENDING')
        API->>API: Kích hoạt background task: process_paper(session_id)
        API-->>Browser: 202 Accepted (session_id, status='PENDING')
    else 2. Nhập link arXiv (US-003)
        User->>Browser: Dán link arXiv hoặc mã ID và bấm "Tiếp tục"
        Browser->>API: POST /api/v1/ingestion/arxiv (arxiv_id)
        API->>API: Gọi arXiv API tải PDF & Metadata
        API->>Storage: Lưu tệp vào storage/raw/{session_id}/original.pdf
        API->>DB: INSERT INTO paper_sessions (source_type='ARXIV', status='PENDING')
        API->>API: Kích hoạt background task: process_paper(session_id)
        API-->>Browser: 202 Accepted (session_id, metadata preview)
    end
    Browser->>Browser: Mở kết nối SSE /api/v1/sessions/{session_id}/progress
```

---

## 3. Sơ đồ Tuần tự 2: Bóc tách, Cô lập Toán học & Dịch thuật CNTT/AI

```mermaid
sequenceDiagram
    autonumber
    participant Task as ⚙️ Async Background Task
    participant Storage as 📁 Local Disk (storage/)
    participant DB as 🗄️ SQLite DB
    participant SSE as 📡 SSE Broadcaster
    participant LLM as 🤖 AI Engine (Gemini / OpenAI / Ollama)

    Task->>SSE: Emit event (progress=15%, "Đang bóc tách cấu trúc tài liệu...")
    
    alt Xử lý tệp PDF (US-004)
        Task->>Storage: Đọc file PDF qua PyMuPDF
        Task->>Task: Trích xuất các khối text blocks, cô lập $ và $$ thành <<<MATH_TOKEN_NNN>>>
    else Xử lý tệp DOCX (US-002)
        Task->>Storage: Đọc file DOCX qua python-docx
        Task->>Task: Trích xuất paragraphs, bảng tables & hình ảnh InlineShapes lưu vào storage/assets/
    end

    Task->>DB: Lưu math_tokens và paper_segments
    Task->>SSE: Emit event (progress=35%, "Đã cô lập công thức toán & hình/bảng. Bắt đầu dịch...")

    Note over Task: US-005: Dịch thuật ngữ cảnh CNTT & AI theo Batch
    loop Từng lô 5-10 phân đoạn
        Task->>LLM: Gửi Prompt (Chỉ dẫn CNTT/AI, Content kèm <<<MATH_TOKEN>>>)
        LLM-->>Task: Trả về văn bản dịch tiếng Việt bảo toàn token
        Task->>Task: Tái nạp chuỗi LaTeX gốc từ math_tokens vào câu dịch
        Task->>DB: UPDATE paper_segments SET translated_content=..., status='TRANSLATED'
        Task->>SSE: Emit event (progress=%, "Đang dịch phân đoạn...")
    end

    Task->>DB: UPDATE paper_sessions SET status='COMPLETED', progress_percent=100
    Task->>SSE: Emit event (progress=100%, "Hoàn tất! Sẵn sàng đọc song ngữ.")
```

---

## 4. Sơ đồ Tuần tự 3: Đọc Song Ngữ trên Web UI (US-006 & US-007)

```mermaid
sequenceDiagram
    autonumber
    actor User as 👤 Bạn
    participant Browser as 🌐 Web UI (Dual-Pane Reader)
    participant API as ⚡ FastAPI Backend
    participant DB as 🗄️ SQLite DB

    Browser->>API: GET /api/v1/sessions/{session_id}/segments
    API->>DB: SELECT * FROM paper_segments ORDER BY order_index ASC
    DB-->>API: Trả về danh sách segments
    API-->>Browser: 200 OK (Danh sách segments gốc EN & dịch VI)
    Browser->>Browser: Render giao diện 2 cột song song + Render công thức qua KaTeX

    alt Người dùng cuộn đọc (Sync Scroll)
        User->>Browser: Cuộn cột gốc hoặc cột dịch
        Browser->>Browser: IntersectionObserver tự động cuộn đồng bộ cột đối ứng
    else Người dùng sửa trực tiếp phân đoạn (Inline Edit)
        User->>Browser: Nhấp đúp vào phân đoạn tiếng Việt
        Browser->>Browser: Hiển thị Inline Textarea Editor
        User->>Browser: Sửa câu chữ và bấm "Lưu" (Ctrl + Enter)
        Browser->>API: PATCH /api/v1/segments/{segment_id}
        API->>DB: UPDATE paper_segments SET translated_content=..., is_user_edited=TRUE
        DB-->>API: OK
        API-->>Browser: 200 OK (Cập nhật tức thì trên Web)
    end
```

---

## 5. Sơ đồ Tuần tự 4: Tải về Tệp PDF Bản Dịch Tiếng Việt (US-008)

```mermaid
sequenceDiagram
    autonumber
    actor User as 👤 Bạn
    participant Browser as 🌐 Web UI
    participant API as ⚡ FastAPI Backend
    participant DB as 🗄️ SQLite DB
    participant Renderer as 📑 WeasyPrint Render Engine
    participant Storage as 📁 Local Disk

    User->>Browser: Bấm nút "Tải PDF bản dịch"
    Browser->>API: GET /api/v1/export/{session_id}/pdf
    API->>DB: Lấy tiêu đề, metadata và toàn bộ segments tiếng Việt (đã user edit nếu có)
    API->>Renderer: Nạp dữ liệu vào HTML Academic Template (nhúng KaTeX, hình ảnh & bảng)
    Renderer->>Renderer: Biên dịch CSS Paged Media A4 -> Sinh tệp PDF tiếng Việt chuẩn học thuật
    Renderer->>Storage: Lưu tệp vào storage/exports/{session_id}/translated.pdf
    API-->>Browser: 200 OK (File stream: application/pdf; filename="[Ten-Bai-Bao]-vi.pdf")
    Browser-->>User: Tự động tải tệp PDF tiếng Việt về máy tính
```
