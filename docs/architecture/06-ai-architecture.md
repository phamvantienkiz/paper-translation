# 06 - Kiến Trúc Trí Tuệ Nhân Tạo & Dịch Thuật Học Thuật (AI & LLM Architecture)

**Tầng tài liệu**: Architecture Layer (Single Source of Truth)  
**Hệ thống**: Paper Translation (Personal & Open-Source Edition)  
**Phiên bản**: 3.1 (Universal OpenAI-Compatible Standard, Adaptive Batching & Hardware Resource Management)  
**Ngày cập nhật**: 2026-10-22  
**Trạng thái**: Approved  

---

## 1. Mục Tiêu & Triết Lý Thiết Kế AI (AI Core Philosophy)

1. **Bảo toàn Ngữ cảnh Toàn văn (Holistic Academic Context):**
   - Loại bỏ hoàn toàn lỗi suy diễn sai đại từ tham chiếu và thuật ngữ rời rạc giữa các trang do cơ chế chia nhỏ đoạn (chunking) cổ điển.
   - Khai thác tối đa cửa sổ ngữ cảnh 1M–2M tokens của các mô hình tiên tiến (Google Gemini) qua cơ chế dịch toàn bài một lần gọi (**Single-Call Translation**).
2. **Chuẩn Hóa Giao Thức OpenAI-Compatible (/v1/chat/completions):**
   - Không bị khóa chặt vào một nhà cung cấp (Zero Vendor Lock-in).
   - Thống nhất một giao thức duy nhất cho toàn bộ hệ sinh thái: Cloud LLM (Gemini, OpenAI, DeepSeek, Groq) và Local Offline Runtimes (Ollama, LM Studio, Llama.cpp, vLLM, Self-Hosted models).
3. **Thích Ứng Kích Thước Ngữ Cảnh (Context-Aware Adaptive Batching):**
   - Tự động nhận diện cấu hình: Chạy Single-Call đối với Cloud Model hoặc chuyển sang **Adaptive Batching** (~1,500 tokens / 8 khối mỗi batch) đối với Local Model có VRAM / Context Window nhỏ (4k–8k tokens).
4. **Phục Hồi Sự Cố Tự Động & Thu Hồi Tài Nguyên Phần Cứng:**
   - Xử lý mượt mà sự cố Rate Limit (429), lỗi mạng và lỗi quá tải máy chủ (5xx) bằng cơ chế **Exponential Backoff**.
   - Cơ chế thu hồi triệt để RAM và CPU (giải phóng toàn bộ ONNX InferenceSession và tắt ThreadPool) ngay khi hoàn thành tác vụ.

---

## 2. Sơ Đồ Kiến Trúc Hệ Thống AI (AI Architecture Diagram)

```mermaid
flowchart TD
    subgraph InputStage ["1. Bóc Tách Bố Cục & Chuẩn Bị Khối"]
        PDF["Tệp PDF Bài Báo"] --> Indra["Indra OCR (ONNX CPU)"]
        Indra --> Normalizer["Coordinate Normalizer [0..1]"]
        Normalizer --> Filter["Smart Translatable Filter<br>(Bỏ qua References, Headers, Footers, Figures)"]
    end

    subgraph DecisionStage ["2. Điều Phối Kênh Dịch Thuật"]
        Filter --> Router{"Kiểm Tra Provider<br>& Độ Dài Ngữ Cảnh"}
        Router -->|Cloud Large-Context<br>(Gemini 1M Context)| SingleCall["Single-Call toàn bài<br>(max_tokens = 65,536)"]
        Router -->|Local Model / VRAM Nhỏ<br>(Ollama, LM Studio, Llama.cpp)| Batching["Adaptive Batching<br>(~1,500 tokens / 8 blocks per batch)"]
    end

    subgraph ExecutionStage ["3. Chuẩn Hóa Giao Thức OpenAI-Compatible"]
        SingleCall --> APIEngine["HTTP Client (httpx) -> /v1/chat/completions"]
        Batching --> APIEngine
        APIEngine --> IncidentGuard{"Xử Lý Sự Cố<br>(Status Code Check)"}
        IncidentGuard -->|200 OK| Parser["Block Unpacker & Regex [[BLK_XXXX]]"]
        IncidentGuard -->|429 Rate Limit| Backoff["Exponential Backoff (Retry-After)"]
        IncidentGuard -->|5xx Server Error| Retry["Retry (max_retries = 3)"]
        IncidentGuard -->|400 Context Limit| FallbackBatch["Chuyển sang Adaptive Batching"]
        Backoff --> APIEngine
        Retry --> APIEngine
        FallbackBatch --> Batching
    end

    subgraph OutputStage ["4. Đồng Bộ Tiến Độ & Giải Phóng Tài Nguyên"]
        Parser --> SSE["ProgressCallback -> SSE Broadcaster (0% .. 100%)"]
        SSE --> DB[(SQLite paper_pages & ocr_blocks)]
        DB --> Cleanup["Hardware Resource Cleanup<br>(pool.shutdown + ONNX release + gc.collect)"]
    end
```

---

## 3. Đặc Tả Các Thành Phần Kỹ Thuật

### 3.1. Chuẩn Hóa Endpoint OpenAI-Compatible (`normalized_llm_endpoint`)

Tất cả các nguồn mô hình được tự động nhận diện và chuẩn hóa về đường dẫn `/chat/completions`:

| Nền tảng / Provider | URL Gốc Cấu Hình | Endpoint Tự Động Chuẩn Hóa |
|---|---|---|
| **Google Gemini** | `https://generativelanguage.googleapis.com/v1beta/openai` | `https://generativelanguage.googleapis.com/v1beta/openai/chat/completions` |
| **OpenAI ChatGPT** | `https://api.openai.com/v1` | `https://api.openai.com/v1/chat/completions` |
| **Ollama Local** | `http://localhost:11434` (hoặc `/v1`) | `http://localhost:11434/v1/chat/completions` |
| **LM Studio Local** | `http://localhost:1234` (hoặc `/v1`) | `http://localhost:1234/v1/chat/completions` |
| **Llama.cpp Local** | `http://localhost:8080` (hoặc `/v1`) | `http://localhost:8080/v1/chat/completions` |
| **Model Tự Host (vLLM / FastChat)** | `http://192.168.1.x:8000/v1` | `http://192.168.1.x:8000/v1/chat/completions` |

### 3.2. Bộ Lọc Thông Minh (Smart Pre-Filter)

- **Nguyên tắc**: Tiết kiệm tối đa 25% – 35% dung lượng token đầu vào/đầu ra và bảo tồn tính chính xác cho các danh mục không cần dịch.
- **Quy tắc phân loại**:
  - `is_translatable = False`:
    - Các khối có `label` là `page header`, `page footer` (số trang, tên hội nghị).
    - Các khối có `label` là `figure`, `picture` (hình ảnh sơ đồ).
    - Toàn bộ các khối nằm sau tiêu đề `References` hoặc `Bibliography` (tài liệu tham khảo quốc tế giữ nguyên tiếng Anh để tra cứu).
  - `is_translatable = True`: Toàn bộ các khối nội dung (`title`, `section header`, `text`, `table`, `caption`, `footnote`, `list`).

### 3.3. Xử Lý Sự Cố Khi Gọi API (Incident & Retry Management)

Dịch vụ áp dụng chiến lược tự phục hồi theo tiêu chuẩn cấp độ doanh nghiệp:
1. **Lỗi Rate Limit (HTTP 429):**
   - Đọc giá trị từ header `Retry-After`.
   - Nếu không có header, tự động giãn cách theo công thức: $\Delta t = \text{retry\_delay} \times 2^{(\text{attempt} - 1)}$.
   - Phát thông báo qua `ProgressCallback` để UI hiển thị trạng thái chờ minh bạch.
2. **Lỗi Máy chủ Tạm thời (HTTP 500, 502, 503, 504):**
   - Tự động thử lại tối đa `LLM_MAX_RETRIES` (mặc định 3 lần).
3. **Sự cố Kết nối Mạng (`httpx.NetworkError`, `httpx.TimeoutException`):**
   - Bắt ngoại lệ và kích hoạt retry tự động.
4. **Vượt Quá Giới Hạn Ngữ Cảnh (HTTP 400 Context Length Exceeded):**
   - Bắt riêng `ContextLengthExceededError`.
   - Tự động phân tách danh sách khối thành các batch nhỏ hơn và dịch tuần tự bằng **Adaptive Batching**.
5. **Dự Phòng An Toàn (Safe Fallback):**
   - Khi cạn kiệt số lần thử lại, hệ thống tự động fallback sang `MockTranslator` để bảo vệ pipeline không bị dừng đột ngột, đảm bảo giữ nguyên mã `[[BLK_XXXX]]` và công thức toán học.

### 3.4. Thu Hồi Tài Nguyên Phần Cứng Triệt Để (Hardware Resource Reclamation)

Nhằm đảm bảo hệ thống không chiếm dụng CPU và RAM sau khi chạy mô hình OCR và dịch thuật:
1. **Dừng ThreadPool:** Gọi `ocr.pool.shutdown(wait=False, cancel_futures=True)` trên `IndraOcrService` để giải phóng toàn bộ các luồng worker threads.
2. **Giải Phóng Bộ Nhớ ONNX:** Gán `None` cho toàn bộ các `InferenceSession` (`det`, `rec`, `order`, `orient`, `mask`, `math`) và xóa từ điển bộ nhớ đệm `groups`, `lms`.
3. **Xóa Bộ Nhớ Đệm Ảnh (Pixmaps):** Xóa tường minh `del pix` sau mỗi trang kết xuất ảnh Layer 0 (200 DPI).
4. **Bảo Đảm Bằng Khối `finally:`**: Toàn bộ quá trình giải phóng tài nguyên được bọc trong khối `finally:` của tiến trình nền, luôn luôn thực thi kể cả khi gặp lỗi.
5. **Garbage Collection:** Kích hoạt `gc.collect()` ép Python giải phóng bộ nhớ heap C++ và RAM ngay lập tức.
