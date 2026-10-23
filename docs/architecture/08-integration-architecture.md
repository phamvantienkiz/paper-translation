# 08 - Kiến Trúc Tích Hợp & Chuẩn Hóa API (Integration Architecture & API Contracts)

**Tầng tài liệu**: Architecture Layer (Single Source of Truth)  
**Hệ thống**: Paper Translation (Personal & Open-Source Edition)  
**Phiên bản**: 3.3 (Standalone Llama.cpp Server, Gemma-4-E2B, 4 P-Cores i5-13500H & 8GB Hard RAM Ceiling)  
**Ngày cập nhật**: 2026-10-23  
**Trạng thái**: Approved  

---

## 1. API Surface Summary — Tổng quan Giao diện Hệ thống

- **Đối tượng tiêu thụ (Consumers):** Web UI cá nhân (React/Vite SPA + 3-Layer HTML5 Canvas Engine).
- **Giao thức:** REST API (JSON) + Server-Sent Events (SSE) cho tiến trình OCR và dịch thuật.
- **Giao thức Nội bộ (Backend $\leftrightarrow$ Standalone `llama.cpp` Server):** Python Async HTTP Client (`httpx`) giao tiếp qua mạng nội bộ Loopback (`http://127.0.0.1:8081/v1/chat/completions`).
- **Chiến lược Engine:** Mặc định **Local-First Standalone Serving** (`llama_cpp` + `gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf`), cho phép chuyển đổi sang Cloud (`gemini`) qua API.

---

## 2. Ma trận Điểm cuối API (Endpoints Matrix v3.3)

| Phương thức | Đường dẫn API | Mục đích nghiệp vụ | Định dạng dữ liệu |
|---|---|---|---|
| `POST` | `/api/v1/ingestion/upload` | Tải lên tệp bài báo **PDF** hoặc **DOCX** | `multipart/form-data` |
| `POST` | `/api/v1/ingestion/arxiv` | Nhập liên kết hoặc mã ID từ arXiv.org | `application/json` (`arxiv_id`) |
| `GET` | `/api/v1/sessions` | Lấy danh sách các bài báo đã xử lý gần đây | `application/json` |
| `GET` | `/api/v1/sessions/{session_id}` | Lấy thông tin chung và trạng thái phiên | `application/json` |
| `GET` | `/api/v1/sessions/{session_id}/progress` | Luồng SSE nhận tiến độ xử lý thời gian thực (0% $\rightarrow$ 100%) | `text/event-stream` (SSE) |
| `GET` | `/api/v1/sessions/{session_id}/canvas-data`| Lấy toàn bộ cấu trúc trang, ảnh Layer 0 & BBoxes cho HTML Canvas | `application/json` |
| `PATCH` | `/api/v1/blocks/{block_id}` | Chỉnh sửa trực tiếp nội dung dịch của một khối trên Canvas | `application/json` (`translated_text`) |
| `GET` | `/api/v1/assets/pages/{session_id}/{filename}` | Phục vụ ảnh nền toàn trang (Layer 0) độ nét cao | `image/png` |
| `GET` | `/api/v1/assets/figures/{session_id}/{filename}`| Phục vụ hình ảnh sơ đồ/đồ thị được crop riêng | `image/png` |
| `GET` | `/api/v1/export/{session_id}/pdf` | Tải về tệp PDF bản dịch hoàn chỉnh từ Backend (hoặc xuất trực tiếp từ Canvas) | `application/pdf` |
| `GET` | `/api/v1/system/engine-status` | Lấy trạng thái Engine (Standalone Llama Server vs Cloud), 4 P-cores, 16K/8K ctx & RAM | `application/json` |
| `POST` | `/api/v1/system/engine-switch` | Chuyển đổi runtime giữa Local Standalone Llama.cpp và Cloud Gemini | `application/json` |

---

## 3. Cấu trúc Khung Phản hồi Chuẩn hóa (Response Envelopes)

### 3.1. Phản hồi tải tệp thành công (`POST /api/v1/ingestion/upload`)
```json
{
  "success": true,
  "data": {
    "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "file_name": "attention_is_all_you_need.pdf",
    "source_type": "PDF",
    "status": "PENDING",
    "message": "Tệp PDF đã được tiếp nhận. Bắt đầu chạy Indra OCR và dịch qua Standalone Llama.cpp Server."
  }
}
```

### 3.2. Cấu trúc gói tin Server-Sent Events (`GET /api/v1/sessions/{id}/progress`)
```text
event: progress_update
data: {"session_id":"3fa85f64-5717-4562-b3fc-2c963f66afa6","step":"OCR_PROCESSING","progress_percent":35,"message":"Đang chạy Indra OCR phân tích bố cục 2 cột & kết xuất ảnh nền trang (5/15)..."}

event: progress_update
data: {"session_id":"3fa85f64-5717-4562-b3fc-2c963f66afa6","step":"TRANSLATING_LOCAL","progress_percent":70,"message":"Đang dịch lô 2,200 từ tiếng Anh qua Standalone llama.cpp Server (Gemma-4-E2B • 4 P-Cores)..."}

event: completed
data: {"session_id":"3fa85f64-5717-4562-b3fc-2c963f66afa6","step":"COMPLETED","progress_percent":100,"message":"Hoàn tất! Sẵn sàng tái hiện bài báo trên HTML Canvas."}
```

### 3.3. Phản hồi trạng thái Engine thời gian thực (`GET /api/v1/system/engine-status`)
```json
{
  "active_provider": "llama_cpp",
  "serving_mode": "standalone_server",
  "internal_server_url": "http://127.0.0.1:8081",
  "is_local": true,
  "model_name": "gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf",
  "cpu_p_cores_threads": 4,
  "hardware_acceleration": true,
  "context_window": 16384,
  "input_word_budget_range": [2000, 2500],
  "output_expansion_factor": "2.0x - 2.5x",
  "hard_ram_ceiling_gb": 8.0,
  "estimated_ram_usage_gb": 4.2,
  "ocr_loaded": false,
  "llm_server_running": true
}
```

---

## 4. Giao Thức Giao Tiếp Nội Bộ Giữa Backend Python Client & Standalone `llama.cpp` Server

1. **Quản lý Tiến trình & Kết nối Nội bộ (`127.0.0.1:8081`):**
   - Backend khởi chạy dịch vụ `llama.cpp server` gốc bằng tiến trình riêng lẻ và kiểm tra trạng thái sẵn sàng qua `GET http://127.0.0.1:8081/health`.
   - Khi dịch thuật, Python Client gửi yêu cầu `POST http://127.0.0.1:8081/v1/chat/completions` qua mạng nội bộ với độ trễ mạng gần như bằng 0 (< 1ms).
2. **Chiến Lược Phân Lô Theo Số Từ (Word-Budget Batching 2,000 – 2,500 Từ Tiếng Anh):**
   - Mỗi request gửi tới `llama.cpp server` chứa tổng lượng từ của **System Prompt + Văn bản các khối bài báo** nằm trong khoảng **2,000 – 2,500 từ tiếng Anh** (~3,000 – 3,800 tokens).
   - Thiết lập `max_tokens = 10240` trên cửa sổ ngữ cảnh `16384` (16K tokens) để đảm bảo đầu ra tiếng Việt (dài gấp **2.0 – 2.5 lần** tiếng Anh) luôn có dư không gian sinh văn bản mà không bao giờ bị tràn context.
3. **Cơ Chế Bảo Toàn & Tự Phục Hồi:**
   - Giữ nguyên 100% các thẻ `[[BLK_XXXX]]`, công thức toán LaTeX `$..$` và thẻ bảng `<table>`.
   - Nếu một khối bị sót nhãn hoặc chạm giới hạn, Python Client tự động gọi bù riêng khối đó qua kết nối nội bộ.
