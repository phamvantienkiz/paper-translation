# 08 - Kiến Trúc Tích Hợp & Chuẩn Hóa API (Integration Architecture & API Contracts)

**Tầng tài liệu**: Architecture Layer (Single Source of Truth)  
**Hệ thống**: Paper Translation (Personal & Open-Source Edition)  
**Phiên bản**: 2.0 (Scaled Down & Focused)  
**Ngày cập nhật**: 2026-10-05  
**Trạng thái**: Approved  

---

## 1. API Surface Summary — Tổng quan Giao diện Hệ thống Tinh gọn

- **Đối tượng tiêu thụ (Consumers):** Web UI cá nhân (React/Vite SPA).
- **Giao thức:** REST API (JSON) + Server-Sent Events (SSE) cho tiến trình dịch thuật.
- **Tiêu chí thiết kế:** Tinh giản tối đa, không cần header xác thực JWT phức tạp khi chạy cục bộ; hỗ trợ nạp API key qua file `.env` hoặc cấu hình Web.

---

## 2. Ma trận Điểm cuối API Tinh gọn (Endpoints Matrix)

| Phương thức | Đường dẫn API | Mục đích nghiệp vụ | Định dạng dữ liệu |
|---|---|---|---|
| `POST` | `/api/v1/ingestion/upload` | Tải lên tệp bài báo (**PDF** hoặc **DOCX**) | `multipart/form-data` |
| `POST` | `/api/v1/ingestion/arxiv` | Nhập liên kết hoặc mã ID từ arXiv.org | `application/json` (`arxiv_id`) |
| `GET` | `/api/v1/sessions/{session_id}` | Lấy thông tin bài báo, metadata và trạng thái | `application/json` |
| `GET` | `/api/v1/sessions/{session_id}/progress` | Luồng SSE nhận tiến độ dịch (0% $\rightarrow$ 100%) | `text/event-stream` (SSE) |
| `GET` | `/api/v1/sessions/{session_id}/segments` | Lấy toàn bộ phân đoạn song ngữ cho Web UI | `application/json` |
| `PATCH` | `/api/v1/segments/{segment_id}` | Chỉnh sửa trực tiếp nội dung phân đoạn dịch | `application/json` (`translated_content`) |
| `GET` | `/api/v1/export/{session_id}/pdf` | Tải về tệp PDF bản dịch tiếng Việt hoàn chỉnh | `application/pdf` (Download file) |
| `GET` | `/api/v1/assets/{session_id}/{filename}` | Phục vụ hình ảnh trích xuất từ bài báo | `image/*` |

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
    "message": "Tệp đã được tiếp nhận và bắt đầu quy trình bóc tách."
  }
}
```

### 3.2. Cấu trúc gói tin Server-Sent Events (`GET /api/v1/sessions/{id}/progress`)
```text
event: progress_update
data: {"session_id":"3fa85f64-5717-4562-b3fc-2c963f66afa6","step":"TRANSLATING","progress_percent":65,"message":"Đang dịch phân đoạn 52/80 qua LLM..."}

event: completed
data: {"session_id":"3fa85f64-5717-4562-b3fc-2c963f66afa6","step":"COMPLETED","progress_percent":100,"message":"Hoàn tất dịch thuật! Sẵn sàng đọc song ngữ."}
```

### 3.3. Phản hồi danh sách phân đoạn song ngữ (`GET /api/v1/sessions/{id}/segments`)
```json
{
  "success": true,
  "data": {
    "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "total_segments": 80,
    "segments": [
      {
        "id": "c1a2b3c4-...",
        "order_index": 0,
        "segment_type": "TITLE",
        "original_content": "Attention Is All You Need",
        "translated_content": "Cơ chế chú ý là tất cả những gì bạn cần",
        "media_path": null,
        "is_user_edited": false
      },
      {
        "id": "d2e3f4g5-...",
        "order_index": 5,
        "segment_type": "FIGURE",
        "original_content": "Figure 1: The Transformer - model architecture.",
        "translated_content": "Hình 1: Kiến trúc mô hình Transformer.",
        "media_path": "/api/v1/assets/3fa85f64.../fig_01.png",
        "is_user_edited": false
      }
    ]
  }
}
```

---

## 4. Tích hợp Ngoại vi Đa nguồn LLM (LLM Provider Integration)

Hệ thống hỗ trợ cơ chế Adapter linh hoạt để người dùng tự do lựa chọn nhà cung cấp AI:

1. **Google Gemini API (Khuyên dùng):**
   - Sử dụng model `gemini-1.5-flash` hoặc `gemini-2.0-flash`.
   - Ưu điểm: Tốc độ xử lý siêu nhanh ($< 2$s/batch), chi phí token cực thấp hoặc miễn phí với hạn mức cá nhân, hiểu ngữ cảnh CNTT/AI xuất sắc.
2. **OpenAI API:**
   - Hỗ trợ model `gpt-4o-mini` hoặc `gpt-4o`.
3. **Local LLM via Ollama (Offline hoàn toàn):**
   - Hỗ trợ kết nối tới máy chủ Ollama cục bộ (`http://localhost:11434/v1`).
   - Khuyên dùng các mô hình: `qwen2.5:7b-instruct` hoặc `llama3.1:8b-instruct`.
   - Giúp bảo mật dữ liệu tuyệt đối khi dịch các bài báo nghiên cứu nội bộ chưa công bố.
