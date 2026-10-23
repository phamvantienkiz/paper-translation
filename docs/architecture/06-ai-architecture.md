# 06 - Kiến Trúc Trí Tuệ Nhân Tạo & Dịch Thuật Học Thuật (AI & LLM Architecture)

**Tầng tài liệu**: Architecture Layer (Single Source of Truth)  
**Hệ thống**: Paper Translation (Personal & Open-Source Edition)  
**Phiên bản**: 3.3 (Standalone Llama.cpp Server, Gemma-4-E2B, 4 P-Cores i5-13500H, 8GB RAM Ceiling & Word-Count Batching)  
**Ngày cập nhật**: 2026-10-23  
**Trạng thái**: Approved  

---

## 1. Mục Tiêu & Triết Lý Thiết Kế AI (AI Core Philosophy v3.3)

1. **Kiến Trúc Serving Độc Lập (Standalone `llama.cpp` Server Service):**
   - Loại bỏ cách tiếp cận nhúng `llama-cpp-python` chạy chung bộ nhớ (in-process) với FastAPI.
   - Sử dụng trực tiếp **`llama.cpp` gốc** được cài đặt qua `uv/pip`, khởi chạy dưới dạng một **Service độc lập (`llama.cpp server`)** do Backend quản lý vòng đời, và giao tiếp thông qua **Python Client qua mạng nội bộ (`127.0.0.1:8081`)**.
2. **Nâng Cấp Mô Hình Lượng Hóa Thế Hệ Mới (`gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf`):**
   - Sử dụng mô hình `gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf` (~2.62 GB) được huấn luyện nhận thức lượng hóa (QAT - Quantization-Aware Training) và Unsloth Dynamic Quantization (`UD-Q4_K_XL`), mang lại chất lượng dịch thuật học thuật tiếng Việt vượt trội.
3. **Tối Ưu Phần Cứng Chuyên Sâu Trên Intel Core i5-13500H & Trần 8GB RAM:**
   - **Khai thác 4 P-cores:** Cấu hình `llama.cpp` sử dụng đúng **4 Performance-cores (P-cores)** trên vi xử lý **Intel Core i5-13500H** (`--threads 4 --threads-batch 4`), tránh hiện tượng hệ điều hành điều phối luồng tính toán nặng sang các nhân tiết kiệm điện (E-cores) gây giảm tốc độ.
   - **Cho phép tăng tốc phần cứng (Hardware Acceleration):** Bật hỗ trợ tăng tốc phần cứng, tập lệnh vector hóa AVX2/VNNI và **Flash Attention (`--flash-attn`)**.
   - **Giới hạn trần cứng $\le 8.0\text{ GB}$ RAM:** Đảm bảo tổng bộ nhớ tiêu thụ của tiến trình `llama.cpp server` luôn nằm dưới ngưỡng **8.0 GB RAM** (thực tế ở cấu hình 16K context với KV Cache Q8_0 chỉ tiêu tốn ~3.8 GB – 4.5 GB RAM).
4. **Quy Tắc Ngân Sách Từ & Chống Tràn Ngữ Cảnh Tuyệt Đối (Word-Budget & Zero Context Overflow):**
   - **Input (2,000 – 2,500 từ tiếng Anh):** Mỗi lượt gọi tới `llama.cpp server` phải đóng gói tổng cộng **System Prompt + Văn bản tiếng Anh của bài báo** nằm trong khoảng **2,000 đến 2,500 từ tiếng Anh** (~3,000 – 3,800 tokens).
   - **Output Tiếng Việt Dự Phòng Gấp 2.0 – 2.5 Lần:** Khi dịch từ tiếng Anh sang tiếng Việt học thuật, số lượng từ và số lượng token sẽ nở ra gấp **2.0 – 2.5 lần** (~6,500 – 9,500 tokens).
   - **Tối ưu cửa sổ ngữ cảnh 16K / 8K:** Cấu hình chuẩn **`n_ctx = 16384` (16K tokens)** với `max_tokens = 10240` để tổng `Input (~3,800) + Output (~9,500) = ~13,300 tokens` luôn nằm gọn trong cửa sổ ngữ cảnh, cam kết **0% nguy cơ tràn context**. Đồng thời hỗ trợ cấu hình `n_ctx = 8192` (8K tokens) cho chế độ lô thu gọn.
5. **Bộ Điều Phối Tuần Tự Tài Nguyên (Sequential Mutex Scheduling):**
   - Indra OCR (~1.5GB–2.0GB RAM) chạy xong phải thu hồi sạch 100% tài nguyên (`unload()`, hủy ONNX sessions, `pool.shutdown()`, `gc.collect()`) trước khi khởi chạy/gọi tiến trình `llama.cpp server`.

---

## 2. Sơ Đồ Kiến Trúc Hệ Thống AI (AI Architecture Diagram v3.3)

```mermaid
flowchart TD
    subgraph Stage1 ["1. Bóc Tách Bố Cục (Indra OCR - Phase 1)"]
        PDF["Tệp PDF Bài Báo"] --> Indra["Indra OCR (ONNX CPU)<br>Chiếm 1.5GB-2.0GB RAM"]
        Indra --> Normalizer["Coordinate Normalizer [0..1]"]
        Normalizer --> Filter["Smart Translatable Filter"]
    end

    subgraph MutexStage ["2. Thu Hồi Tài Nguyên Tuần Tự (Sequential Mutex)"]
        Filter --> OCRCleanup["IndraOcrService.unload()<br>• pool.shutdown(wait=False)<br>• del ONNX InferenceSessions<br>• gc.collect() -> Giải phóng 100% RAM OCR"]
    end

    subgraph Stage2 ["3. Điều Phối Kênh Dịch & Phân Lô Theo Số Từ (Local-First Default)"]
        OCRCleanup --> Router{"Kiểm Tra Provider<br>(Mặc định: llama_cpp)"}
        Router -->|Local-First (Mặc định)| WordBatcher["Word-Aware Batcher<br>Đóng gói: System Prompt + Paper Text<br>= 2,000 - 2,500 từ tiếng Anh (~3,000-3,800 tokens)"]
        Router -->|Cloud Option| CloudEngine["GeminiTranslator<br>Single-Call toàn bài (max_tokens=65536)"]
    end

    subgraph StandaloneStage ["4. Dịch Vụ Serving Riêng Lẻ & Giao Tiếp Mạng Nội Bộ"]
        WordBatcher --> PyClient["Python Async HTTP Client (httpx)<br>Giao tiếp qua Loopback 127.0.0.1:8081"]
        PyClient <-->|POST /v1/chat/completions<br>max_tokens=10240 (dự phòng 2-2.5x)| LlamaSrv["Standalone llama.cpp Server Process<br>• Model: gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf<br>• CPU: 4 P-Cores i5-13500H + HW Accel<br>• Context: 16K (16384) / 8K • RAM <= 8GB"]
        CloudEngine --> APIEngine["HTTP Client -> Google Cloud API"]
        PyClient --> Parser["Block Unpacker & Regex [[BLK_XXXX]]"]
        APIEngine --> Parser
    end

    subgraph OutputStage ["5. Đồng Bộ Tiến Độ & Hiển Thị"]
        Parser --> SSE["ProgressCallback -> SSE Broadcaster"]
        SSE --> DB[(SQLite paper_pages & ocr_blocks)]
        DB --> UIIndicator["Cập nhật UI Engine Badge:<br>'Local LLM: Gemma-4-E2B (16K Ctx • 4 P-Cores)'"]
    end
```

---

## 3. Phân Tích Toán Học Ngân Sách Token, Bộ Nhớ & Cấu Hình Phần Cứng

### 3.1. Bảng Cân Đối Ngân Sách Từ & Token (Word & Token Budget Matrix)

| Thông số | Giá trị định mức | Quy đổi Token (Gemma Tokenizer) | Giải thích kỹ thuật |
|---|---|---|---|
| **System Prompt (Chỉ dẫn + Glossary)** | ~250 – 350 từ tiếng Anh | ~350 – 500 tokens | Chứa quy tắc bảo toàn `[[BLK_XXXX]]`, LaTeX `$..$`, `<table>` và thuật ngữ CNTT/AI. |
| **Văn bản Bài báo trong 1 Batch** | **1,750 – 2,150 từ tiếng Anh** | ~2,650 – 3,300 tokens | Gom các khối `ocr_blocks` liên tiếp sao cho tổng cùng System Prompt đạt **2,000 – 2,500 từ tiếng Anh**. |
| **Tổng Input mỗi Batch** | **2,000 – 2,500 từ tiếng Anh** | **~3,000 – 3,800 tokens** | Đảm bảo ngữ cảnh liền mạch của cả một phần lớn (1.5 – 3 trang bài báo 2 cột). |
| **Hệ số giãn nở Tiếng Việt** | **Gấp 2.0 – 2.5 lần tiếng Anh** | **~6,500 – 9,500 tokens** | Tiếng Việt học thuật nhiều âm tiết + dấu thanh + giữ nguyên thẻ `[[BLK_XXXX]]` và công thức LaTeX. |
| **Trần cấp phát Output (`max_tokens`)** | Dư dả tuyệt đối | **`10,240` tokens** | Luôn lớn hơn mức tối đa 9,500 tokens để câu dịch không bao giờ bị cắt ngang (`finish_reason != "length"`). |
| **Tổng Context Window (`n_ctx`)** | **16K (`16,384` tokens)** *(Mặc định)* | `3,800 + 10,240 = 14,040 <= 16,384` | Dư hơn 2,300 tokens đệm an toàn. (Hỗ trợ chế độ `8,192` tokens khi cấu hình batch thu gọn). |

### 3.2. Cấu Hình Tối Ưu `llama.cpp` Server Trên Intel Core i5-13500H (RAM $\le 8\text{GB}$)

| Tham số `llama.cpp` Server | Giá trị cấu hình | Lý do tối ưu hóa trên Laptop Intel Core i5-13500H |
|---|---|---|
| `--model` (`-m`) | `storage/models/gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf` | Mô hình Gemma 4 E2B Instruction-Tuned QAT (~2.62 GB trên đĩa). |
| `--host` / `--port` | `127.0.0.1` / `8081` | Chỉ lắng nghe trên mạng nội bộ (Loopback) để Python Client của Backend kết nối an toàn. |
| `--threads` (`-t`) | **`4`** | Khớp chính xác **4 P-cores (Performance Cores)** của Intel Core i5-13500H, tránh tràn sang E-cores làm chậm toàn cục. |
| `--threads-batch` (`-tb`) | **`4`** | Tăng tốc độ xử lý Prompt (Prompt Evaluation) trên 4 nhân P-cores cho gói 2,000–2,500 từ. |
| `--ctx-size` (`-c`) | **`16384`** *(hoặc `8192`)* | Đảm bảo chứa trọn Input (2,000–2,500 từ EN) + Output tiếng Việt (gấp 2–2.5x) không tràn context. |
| `--batch-size` (`-b`) / `-ub` | `512` / `512` | Tăng tốc độ đọc hiểu 3,500 tokens đầu vào chỉ trong vài giây. |
| `--flash-attn` (`-fa`) | `on` (Enabled) | Tăng tốc tính toán ma trận Attention trên ngữ cảnh dài 16K và giảm mạnh bộ nhớ KV Cache. |
| `--cache-type-k` / `-v` | `q8_0` / `q8_0` | Lượng hóa KV Cache về 8-bit giúp giữ nguyên 100% chất lượng dịch trong khi giảm 50% RAM của KV Cache. |
| `--n-gpu-layers` (`-ngl`) | `auto` / cấu hình phần cứng | Cho phép tận dụng tăng tốc phần cứng (GPU/iGPU nếu khả dụng) kết hợp 4 P-cores CPU. |
| **Tổng RAM chiếm dụng** | **~3.8 GB – 4.5 GB RAM** | Nằm hoàn toàn dưới **trần cứng $\le 8.0\text{ GB}$ RAM** đã quy định. |
