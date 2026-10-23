# 06 - Kiến Trúc Trí Tuệ Nhân Tạo & Dịch Thuật Học Thuật (AI & LLM Architecture)

**Tầng tài liệu**: Architecture Layer (Single Source of Truth)  
**Hệ thống**: Paper Translation (Personal & Open-Source Edition)  
**Phiên bản**: 3.1 (Universal OpenAI-Compatible Standard, Adaptive Batching & Hardware Resource Management)  
**Ngày cập nhật**: 2026-10-22  
**Trạng thái**: Approved  

---

## 1. Mục Tiêu & Triết Lý Thiết Kế AI (AI Core Philosophy)

1. **Ưu Tiên Local-First & Bảo Mật Tuyệt Đối (Local-First Priority):**
   - Đặt động cơ dịch cục bộ (`llama.cpp` + `Qwen3-1.7B-Q4_K_M.gguf`) làm cốt lõi xử lý mặc định, bảo vệ 100% dữ liệu nghiên cứu nội bộ và vận hành hoàn toàn ngoại tuyến với chi phí 0đ.
   - Cloud Gemini (Single-Call 1M context) đóng vai trò tùy chọn thứ hai khi người dùng cần tốc độ cực đại trên đám mây.
2. **Khóa Trần Cứng 4.0 GB RAM Cho Phần Cứng Cá Nhân (Hard 4GB RAM Ceiling):**
   - Bảo vệ hệ thống máy trạm cá nhân (8GB–16GB RAM) khỏi hiện tượng treo máy hoặc Out-Of-Memory.
   - Cấu hình chuẩn ngữ cảnh: `n_ctx = 8192` (8K tokens) tiêu tốn ~2.8 GB RAM (vùng an toàn tối ưu).
   - Thiết lập giới hạn trần cứng: `max_n_ctx = 16384` (16K tokens) tiêu tốn tối đa 4.0 GB RAM. Nghiêm cấm mọi cấu hình vượt quá 4GB RAM khi chạy trên CPU.
3. **Bộ Điều Phối Tuần Tự Tài Nguyên Ngặt Nghèo (Sequential Mutex Scheduling):**
   - Indra OCR (~1.5GB–2.0GB RAM) và Local LLM (~2.8GB–4.0GB RAM) tuyệt đối **không được nạp cùng lúc**.
   - Chu trình bắt buộc: Chạy OCR $\rightarrow$ Thu hồi sạch 100% tài nguyên (`unload()`, hủy ONNX sessions, `pool.shutdown()`, `gc.collect()`) $\rightarrow$ Mới nạp Local LLM vào RAM/VRAM để suy luận.
4. **Thích Ứng Kích Thước Ngữ Cảnh (Context-Aware Adaptive Batching):**
   - Tự động đóng gói 6–8 khối văn bản liên tiếp (~1,500 tokens) cho Local LLM, bảo toàn mã định danh `[[BLK_XXXX]]`, công thức LaTeX và thẻ bảng biểu.

---

## 2. Sơ Đồ Kiến Trúc Hệ Thống AI (AI Architecture Diagram)

```mermaid
flowchart TD
    subgraph Stage1 ["1. Bóc Tách Bố Cục (Indra OCR - Phase 1)"]
        PDF["Tệp PDF Bài Báo"] --> Indra["Indra OCR (ONNX CPU)<br>Chiếm 1.5GB-2.0GB RAM"]
        Indra --> Normalizer["Coordinate Normalizer [0..1]"]
        Normalizer --> Filter["Smart Translatable Filter"]
    end

    subgraph MutexStage ["2. Thu Hồi Tài Nguyên Tuần Tự (Sequential Mutex)"]
        Filter --> OCRCleanup["IndraOcrService.unload()<br>• pool.shutdown(wait=False)<br>• del ONNX InferenceSessions<br>• gc.collect() -> RAM trở về tối thiểu"]
    end

    subgraph Stage2 ["3. Điều Phối Kênh Dịch Thuật (Local-First Default)"]
        OCRCleanup --> Router{"Kiểm Tra Provider<br>(Mặc định: Local LLM)"}
        Router -->|Local-First (Mặc định)<br>Qwen3-1.7B GGUF| LocalEngine["LlamaCppService (In-Process)<br>n_ctx=8192 (~2.8GB RAM) <= 4GB Trần Cứng<br>Adaptive Batching (~1,500 tokens / batch)"]
        Router -->|Cloud Option<br>Gemini API 1M Context| CloudEngine["GeminiTranslator<br>Single-Call toàn bài (max_tokens=65536)"]
    end

    subgraph ExecutionStage ["4. Thực Thi Suy Luận & Bóc Tách Nhãn"]
        LocalEngine --> InferEngine["llama-cpp-python suy luận CPU đa luồng"]
        CloudEngine --> APIEngine["HTTP Client (httpx) -> /v1/chat/completions"]
        InferEngine --> Parser["Block Unpacker & Regex [[BLK_XXXX]]"]
        APIEngine --> Parser
    end

    subgraph OutputStage ["5. Đồng Bộ Tiến Độ & Hiển Thị"]
        Parser --> SSE["ProgressCallback -> SSE Broadcaster<br>(phase: ocr -> cleanup -> translating_local)"]
        SSE --> DB[(SQLite paper_pages & ocr_blocks)]
        DB --> UIIndicator["Cập nhật UI Engine Badge: 'Local LLM: Qwen3-1.7B'"]
    end
```
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
