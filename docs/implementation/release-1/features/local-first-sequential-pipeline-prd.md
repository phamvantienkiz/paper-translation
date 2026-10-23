# Product Requirements Document (PRD): Kiến Trúc Local-First, Bộ Điều Phối Tuần Tự Tài Nguyên, Standalone Serving & Giới Hạn Trần 8GB RAM

**Tầng tài liệu**: Implementation Layer  
**Release**: release-1 (Personal Core MVP — Local-First Standalone Shift)  
**Phiên bản**: 3.0 (Standalone `llama.cpp` Server, `Gemma-4-E2B`, 4 P-Cores i5-13500H, Resource Mutex & 8GB Hard RAM Ceiling)  
**Ngày cập nhật**: 2026-10-23  
**Tác giả**: Senior IT-BA & Product Owner  
**Trạng thái**: Approved  
**Chất lượng yêu cầu**: 98/100  

---

## 1. Mục Tiêu Nghiệp Vụ & Giới Hạn Phần Cứng Cốt Lõi (Business & Hardware Context)

### 1.1. Chuyển Dịch Chiến Lược Standalone Local-First (Standalone Serving Pivot)
- **Mục tiêu số 1**: Hệ thống ưu tiên mặc định việc dịch thuật bài báo khoa học bằng mô hình cục bộ **`gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf`**. Thay vì gộp chung vào bên trong tiến trình FastAPI qua `llama-cpp-python`, hệ thống sử dụng trực tiếp thư viện/công cụ `llama.cpp` gốc (cài đặt qua `uv/pip`), viết một **Service riêng quản lý tiến trình `llama.cpp server`** và dùng **Python Client giao tiếp qua mạng nội bộ (`127.0.0.1`)**.
- **Minh bạch hóa trên giao diện (UI Engine Transparency)**: Người dùng luôn quan sát thấy rõ hệ thống đang chạy ở chế độ nào (`Local LLM: Gemma-4-E2B` hay `Cloud API`) kèm thông số 4 P-cores, cửa sổ ngữ cảnh 16K/8K và mức RAM tiêu thụ.

### 1.2. Tối Ưu Phần Cứng Intel Core i5-13500H (4 P-Cores) & Rào Chắn Trần Cứng 8GB RAM
- **Bài toán phần cứng thực tế**: Hệ thống vận hành trên laptop trang bị vi xử lý **Intel Core i5-13500H** (kiến trúc lai gồm **4 Performance-cores** và 8 Efficient-cores).
- **Ràng buộc phần cứng & bộ nhớ bất biến**:
  - **Cấu hình 4 P-cores & Tăng tốc phần cứng**: Tiến trình `llama.cpp server` bắt buộc cấu hình sử dụng **4 P-cores** (`--threads 4 --threads-batch 4`) và bật tăng tốc phần cứng (Flash Attention `--flash-attn`, AVX2/VNNI, GPU/iGPU offloading nếu khả dụng) để đạt tốc độ xử lý cao nhất mà không bị nghẽn ở các nhân E-cores.
  - **Trần cứng $\le 8.0\text{ GB}$ RAM**: Tổng lượng RAM tối đa mà tiến trình `llama.cpp server` được phép chiếm dụng **bắt buộc không vượt quá ngưỡng 8.0 GB RAM**.
  - **Phân tích kích thước ngữ cảnh (Context Window 8K / 16K vs. RAM Usage & Token Budget)**:
    - Với mô hình `gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf` (~2.62 GB):
      - **Ngữ cảnh 16K (`n_ctx = 16384` - Mặc định chuẩn cho lô 2,000–2,500 từ EN)**: Trọng số (~2.62 GB) + KV Cache Q8_0 (~0.9 GB) + Compute Buffer (~0.6 GB) $\approx$ **4.1 GB – 4.5 GB RAM** $\rightarrow$ **Nằm rất sâu dưới trần 8.0 GB RAM**, đồng thời cung cấp đủ 16,384 tokens để chứa **Input 2,000–2,500 từ tiếng Anh (~3,000–3,800 tokens)** và **Output tiếng Việt dài gấp 2.0–2.5 lần (~6,500–9,500 tokens)** mà không bao giờ bị tràn context.
      - **Ngữ cảnh 8K (`n_ctx = 8192` - Chế độ tùy chọn nhanh)**: Tiêu thụ **~3.4 GB – 3.7 GB RAM**, sử dụng khi người dùng cấu hình lô đầu vào nhỏ hơn (~1,000–1,200 từ tiếng Anh).

### 1.3. Cơ Chế Điều Phối Tuần Tự Tài Nguyên (Sequential Mutex Pipeline)
- **Quy trình tuần tự bắt buộc giữa OCR và Standalone LLM Server**:
  1. **Phase 1 (Chạy OCR)**: Indra OCR nạp vào bộ nhớ (~1.5 GB – 2.0 GB RAM) và xử lý toàn bộ các trang PDF. (Nếu `llama.cpp server` đang chạy trước đó và cần nhường toàn bộ CPU/RAM cho OCR tốc độ cao, hệ thống có thể tạm dừng hoặc cô lập luồng).
  2. **Phase 2 (Thu hồi sạch tài nguyên OCR)**: Ngay khi OCR kết thúc, hệ thống dừng ThreadPool (`pool.shutdown(wait=False)`), xóa sạch tham chiếu các session ONNX và gọi `gc.collect()` để giải phóng 100% RAM và giải phóng hoàn toàn 4 nhân P-cores.
  3. **Phase 3 (Khởi chạy/Gọi Standalone `llama.cpp` Server)**: Sau khi OCR đã giải phóng hoàn toàn CPU & RAM, `LlamaServerManager` đảm bảo tiến trình `llama.cpp server` (`gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf`, 4 P-cores, $\le 8\text{GB}$ RAM, 16K context) sẵn sàng tại `127.0.0.1:8081`, và **Python Client** gửi tuần tự các lô **2,000 – 2,500 từ tiếng Anh** qua mạng nội bộ để dịch thuật.

---

## 2. Sơ Đồ Ranh Giới & Luồng Tuần Tự (Process Diagrams)

### 2.1. Sơ đồ Ranh giới Hệ thống (Use Case System Boundary)
```mermaid
flowchart LR
    subgraph Users ["Người dùng"]
        U["👤 Kỹ sư / Nhà nghiên cứu"]
    end

    subgraph SystemBoundary ["Hệ Thống Dịch Bài Báo (Standalone Local-First MVP)"]
        UC1["(1. Tải lên bài báo PDF / arXiv)"]
        UC2["(2. Quan sát & Chọn Engine trên UI: Local vs Cloud)"]
        UC3["(3. Chạy Indra OCR bóc tách layout)"]
        UC4["(4. Thu hồi sạch tài nguyên OCR: unload & gc)"]
        UC5["(5. Khởi chạy Service riêng llama.cpp Server<br>Gemma-4-E2B • 4 P-Cores • <= 8GB RAM • 16K Ctx)"]
        UC6["(6. Python Client gửi lô 2,000-2,500 từ EN qua mạng nội bộ<br>Output tiếng Việt dư 2.0-2.5x chống tràn context)"]
        UC7["(7. Hiển thị 3-Layer HTML Canvas Viewer)"]

        UC1 --> UC2
        UC2 --> UC3
        UC3 -.->|<<sequential mutex>>| UC4
        UC4 -.->|<<release CPU/RAM before LLM>>| UC5
        UC5 --> UC6
        UC6 --> UC7
    end

    subgraph HardwareConstraint ["Phần Cứng Laptop Intel Core i5-13500H"]
        CPU_RAM["⚡ 4 P-Cores + HW Accel<br>🧠 Host RAM Ceiling <= 8.0 GB"]
        ModelDisk[("📦 storage/models/<br>gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf")]
    end

    U --> UC1
    U --> UC2
    UC3 <-->|Chiếm 1.5GB-2GB| CPU_RAM
    UC4 -.->|Trả lại 100% RAM & CPU| CPU_RAM
    UC5 <-->|Chiếm ~4.2GB (16K ctx) <= 8GB Max| CPU_RAM
    UC5 <--> ModelDisk
```

### 2.2. Sơ đồ Luồng Tuần Tự Chi Tiết (Detailed Sequential Mutex & Standalone Serving Flow)
```mermaid
flowchart TD
    Start([Bắt đầu xử lý bài báo]) --> LoadOCR["Khởi tạo Indra OCR Service (ONNX CPU)"]
    
    LoadOCR --> ExecOCR["Bóc tách bố cục 2 cột, thứ tự đọc, bảng HTML, LaTeX"]
    ExecOCR --> OCRDone{OCR hoàn thành 100% trang?}
    
    OCRDone -- Có --> CleanupOCR["THU HỒI SẠCH TÀI NGUYÊN OCR:<br>1. pool.shutdown(wait=False)<br>2. del sessions (det, rec, math...)<br>3. gc.collect()<br>-> Giải phóng 100% RAM & 4 P-Cores"]
    
    CleanupOCR --> CheckEngine{Kiểm tra cấu hình Engine<br>(Mặc định: Local llama.cpp)?}
    
    CheckEngine -- "Local LLM (Gemma-4-E2B)" --> EnsureStandaloneSrv["LlamaServerManager kiểm tra / khởi chạy tiến trình riêng llama.cpp Server:<br>• Model: gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf<br>• CPU: 4 P-Cores i5-13500H (-t 4 -tb 4) + Flash-Attn<br>• Ngữ cảnh: n_ctx = 16384 (16K) / 8192 (8K) | Trần <= 8.0GB RAM"]
    
    EnsureStandaloneSrv --> WordBatcher["Word-Aware Batching:<br>Đóng gói (System Prompt + Text bài báo) = 2,000 - 2,500 từ tiếng Anh (~3,500 tokens)"]
    WordBatcher --> InternalClient["Python Client gọi POST http://127.0.0.1:8081/v1/chat/completions<br>với max_tokens = 10240 (dư gấp 2.0 - 2.5x cho tiếng Việt)"]
    InternalClient --> LLMDone{Dịch xong tất cả các lô?}
    
    CheckEngine -- "Cloud API (Gemini)" --> CallCloud["Gọi Single-Call Gemini API qua Internet"]
    CallCloud --> LLMDone
    
    LLMDone -- Có --> SyncData["Đồng bộ tọa độ & Lưu kết quả vào SQLite (ocr_blocks)"]
    SyncData --> RenderCanvas["Render bài báo lên 3-Layer HTML Canvas Viewer"]
    RenderCanvas --> UpdateUIBadge["Cập nhật UI Engine Badge ('Local LLM: Gemma-4-E2B • 16K Ctx • 4 P-Cores')"]
    UpdateUIBadge --> End([Hoàn tất])
```

---

## 3. Yêu Cầu Chức Năng Chi Tiết (Detailed Functional Requirements)

| Mã Yêu Cầu | Tên Chức Năng | Mô Tả Nghiệp Vụ & Quy Tắc Kỹ Thuật | Ưu Tiên |
|---|---|---|---|
| **FR-07.1** | Dịch Vụ Serving Riêng Lẻ (`llama.cpp` Server + Python Client) | Không gộp chung LLM vào trong tiến trình FastAPI. Sử dụng `uv/pip` cài đặt trực tiếp `llama.cpp` gốc, viết service riêng quản lý tiến trình `llama.cpp server` chạy mô hình `gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf` và giao tiếp qua Python Client trên mạng nội bộ (`127.0.0.1:8081`). | P0 (Must) |
| **FR-07.2** | Tối Ưu 4 P-Cores Intel Core i5-13500H, Tăng Tốc Phần Cứng & Trần 8GB RAM | Cấu hình `llama.cpp server` sử dụng đúng **4 P-cores** (`--threads 4 --threads-batch 4`) trên Intel Core i5-13500H, cho phép bật tăng tốc phần cứng (`--flash-attn`, GPU/iGPU layers) và giới hạn tổng bộ nhớ chiếm dụng **$\le 8.0\text{ GB}$ RAM**. | P0 (Must) |
| **FR-07.3** | Ngân Sách Lô 2,000–2,500 Từ Tiếng Anh & Dự Phòng Output 2.0–2.5x Trên 16K/8K Ctx | Tối ưu cửa sổ ngữ cảnh **16K tokens (`n_ctx=16384`)** (hỗ trợ tùy chọn 8K) sao cho mỗi lượt gọi có Input (System Prompt + Text bài báo) đạt **2,000 – 2,500 từ tiếng Anh**, và không gian Output (`max_tokens=10240`) dư dả gấp **2.0 – 2.5 lần** để bản dịch tiếng Việt không bao giờ bị tràn context. | P0 (Must) |
| **FR-07.4** | Bộ Điều Phối Tuần Tự Tài Nguyên (Sequential Mutex Scheduler) | Thực thi tuần tự hoàn toàn giữa Indra OCR và `llama.cpp server`. Sau khi OCR kết thúc, bắt buộc giải phóng toàn bộ session ONNX, dừng threadpool và gọi `gc.collect()` trước khi bắt đầu phiên suy luận trên `llama.cpp server`. | P0 (Must) |
| **FR-08.1** | Huy Hiệu Trạng Thái Động Cơ Trên UI (UI Engine Status Badge) | Giao diện hiển thị rõ ràng huy hiệu trạng thái tại Header: <br>- 🟢 `Local LLM: Gemma-4-E2B (16K Ctx • 4 P-Cores)`<br>- 🔵 `Cloud API: Gemini-3.5-Flash (Single-Call 1M)` | P0 (Must) |
