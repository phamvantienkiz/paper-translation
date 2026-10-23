# 08 - Kiến Trúc Tích Hợp & Chuẩn Hóa API (Integration Architecture & API Contracts)

**Tầng tài liệu**: Architecture Layer (Single Source of Truth)  
**Hệ thống**: Paper Translation (Personal & Open-Source Edition)  
**Phiên bản**: 3.2 (Local LLM Qwen3 GGUF, Sequential Mutex & 4GB Hard RAM Ceiling)  
**Ngày cập nhật**: 2026-10-23  
**Trạng thái**: Approved  

---

## 1. API Surface Summary — Tổng quan Giao diện Hệ thống

- **Đối tượng tiêu thụ (Consumers):** Web UI cá nhân (React/Vite SPA + 3-Layer HTML5 Canvas Engine).
- **Giao thức:** REST API (JSON) + Server-Sent Events (SSE) cho tiến trình OCR và dịch thuật.
- **Tiêu chí thiết kế:** Tinh giản, thống nhất khung phản hồi (`Response Envelope`), cung cấp đầy đủ thông số trang, ảnh nền Layer 0 và danh sách khối tọa độ chuẩn hóa `[0.0 .. 1.0]` để Canvas hiển thị tức thì.
- **Chiến lược Engine:** Mặc định **Local-First** (`llama_cpp` + `Qwen3-1.7B-Q4_K_M.gguf`), cho phép chuyển đổi sang Cloud (`gemini`) qua API.

---

## 2. Ma trận Điểm cuối API (Endpoints Matrix v3.2)

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
| `GET` | `/api/v1/system/engine-status` | Lấy trạng thái Engine (Local vs Cloud), context window & RAM | `application/json` |
| `POST` | `/api/v1/system/engine-switch` | Chuyển đổi runtime giữa Local LLM và Cloud (khóa trần <= 16K ctx) | `application/json` |

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
    "message": "Tệp PDF đã được tiếp nhận. Bắt đầu chạy Indra OCR và dịch toàn văn."
  }
}
```

### 3.2. Cấu trúc gói tin Server-Sent Events (`GET /api/v1/sessions/{id}/progress`)
```text
event: progress_update
data: {"session_id":"3fa85f64-5717-4562-b3fc-2c963f66afa6","step":"OCR_PROCESSING","progress_percent":35,"message":"Đang chạy Indra OCR phân tích bố cục 2 cột & kết xuất ảnh nền trang (5/15)..."}

event: progress_update
data: {"session_id":"3fa85f64-5717-4562-b3fc-2c963f66afa6","step":"TRANSLATING","progress_percent":70,"message":"Đang dịch toàn bộ bài báo trong 1 lần gọi qua Google Gemini API..."}

event: completed
data: {"session_id":"3fa85f64-5717-4562-b3fc-2c963f66afa6","step":"COMPLETED","progress_percent":100,"message":"Hoàn tất! Sẵn sàng tái hiện bài báo trên HTML Canvas."}
```

### 3.3. Phản hồi dữ liệu tái hiện HTML Canvas (`GET /api/v1/sessions/{id}/canvas-data`)
```json
{
  "success": true,
  "data": {
    "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "title": "Attention Is All You Need",
    "total_pages": 15,
    "pages": [
      {
        "page_number": 1,
        "width_pt": 595.27,
        "height_pt": 841.89,
        "page_image_url": "/api/v1/assets/pages/3fa85f64-5717-4562-b3fc-2c963f66afa6/page_1.png",
        "blocks": [
          {
            "id": "b1a2b3c4-0001",
            "block_code": "BLK_0001",
            "reading_order": 0,
            "label": "title",
            "bbox_norm": [0.084, 0.085, 0.915, 0.130],
            "is_translatable": true,
            "original_text": "Attention Is All You Need",
            "translated_text": "Cơ Chế Chú Ý Là Tất Cả Những Gì Bạn Cần",
            "figure_image_url": null,
            "is_user_edited": false
          },
          {
            "id": "b1a2b3c4-0002",
            "block_code": "BLK_0002",
            "reading_order": 1,
            "label": "text",
            "bbox_norm": [0.084, 0.237, 0.478, 0.534],
            "is_translatable": true,
            "original_text": "The dominant sequence transduction models are based on complex recurrent neural networks where $d_{model} = 512$.",
            "translated_text": "Các mô hình chuyển đổi chuỗi chiếm ưu thế dựa trên mạng nơ-ron hồi quy phức tạp với $d_{model} = 512$.",
            "figure_image_url": null,
            "is_user_edited": false
          }
        ]
      }
    ]
  }
}
```

### 3.4. Phản hồi trạng thái Engine thời gian thực (`GET /api/v1/system/engine-status`)
```json
{
  "active_provider": "llama_cpp",
  "is_local": true,
  "model_name": "Qwen3-1.7B-Q4_K_M.gguf",
  "context_window": 8192,
  "hard_ram_ceiling_gb": 4.0,
  "estimated_ram_usage_gb": 2.8,
  "ocr_loaded": false,
  "llm_loaded": true
}
```

---

## 4. Chuẩn Hóa Giao Thức Gọi LLM OpenAI-Compatible (Cloud & Local)

Hệ thống chuẩn hóa toàn bộ các kết nối mô hình ngôn ngữ lớn theo chuẩn **OpenAI Chat Completions (`/v1/chat/completions`)**:

1. **Endpoint Đa Nền Tảng & Tự Động Chuẩn Hóa (`normalized_llm_endpoint`):**
   - **Google Gemini**: `https://generativelanguage.googleapis.com/v1beta/openai` (Tự động chuyển đổi nếu người dùng nhập native URL `:generateContent`).
   - **OpenAI**: `https://api.openai.com/v1`
   - **Ollama**: `http://localhost:11434/v1` (Tự động bù `/v1` nếu người dùng chỉ nhập port `11434`).
   - **LM Studio**: `http://localhost:1234/v1` (Tự động bù `/v1` nếu người dùng chỉ nhập port `1234`).
   - **Llama.cpp**: `http://localhost:8080/v1` (Tự động bù `/v1` nếu người dùng chỉ nhập port `8080`).
   - **Model Dịch Tự Host**: Hỗ trợ bất kỳ endpoint nào triển khai chuẩn `/v1/chat/completions` (vLLM, FastChat, TGI, LocalAI).

2. **Chiến Lược Dịch Thích Ứng (Single-Call vs. Adaptive Batching):**
   - **Cloud Models (Gemini 1M Context Window):** Gửi toàn bộ các khối `is_translatable = True` trong **1 lần gọi duy nhất** với `max_tokens: 65536`.
   - **Local Models (Context Window 4k–8k Tokens):** Tự động gom khối thành các lô nhỏ (~1,500 tokens / 8 khối mỗi batch) để dịch tuần tự, chống tràn VRAM và lỗi HTTP 400 Context Limit.

3. **Cơ Chế Callback & Xử Lý Sự Cố Khi Gọi API:**
   - **ProgressCallback**: Liên tục phát sự kiện cập nhật tiến độ phần trăm và thông báo chi tiết đến người dùng qua kênh Server-Sent Events (`GET /api/v1/sessions/{id}/progress`).
   - **Retries & Exponential Backoff**: Tự động thử lại khi gặp HTTP 429 Rate Limit (tôn trọng header `Retry-After`), HTTP 5xx Server Error, hoặc lỗi gián đoạn mạng/timeout (`httpx.NetworkError`).
   - **Cơ chế Bảo toàn Định danh Khối (`[[BLK_XXXX]]`):** Yêu cầu mô hình giữ nguyên 100% các thẻ `[[BLK_XXXX]]`, công thức toán LaTeX `$..$` và thẻ bảng `<table>`.
   - **Auto-Continuation Guard:** Tự động gọi tiếp nối cho các khối còn thiếu nếu gặp `finish_reason == "length"` hoặc bài báo quá dài (> 40 trang).
   - **Safe Fallback:** Tự động fallback sang `MockTranslator` nếu mạng mất kết nối hoặc hết số lần thử lại, tránh làm crash pipeline nền.
