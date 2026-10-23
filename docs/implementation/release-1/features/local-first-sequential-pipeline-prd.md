# Product Requirements Document (PRD): Kiến Trúc Local-First, Bộ Điều Phối Tuần Tự Tài Nguyên & Giới Hạn Trần 4GB RAM

**Tầng tài liệu**: Implementation Layer  
**Release**: release-1 (Personal Core MVP — Local-First Shift)  
**Phiên bản**: 2.0 (Local-First Priority, Resource Mutex & 4GB Hard RAM Ceiling)  
**Ngày cập nhật**: 2026-10-23  
**Tác giả**: Senior IT-BA & Product Owner  
**Trạng thái**: Approved  
**Chất lượng yêu cầu**: 100/100  

---

## 1. Mục Tiêu Nghiệp Vụ & Giới Hạn Phần Cứng Cốt Lõi (Business & Hardware Context)

### 1.1. Chuyển Dịch Chiến Lược Local-First (Local-First Pivot)
- **Mục tiêu số 1**: Hệ thống chuyển đổi trọng tâm mặc định sang **Local-First**, ưu tiên tối đa việc khởi động và thực thi dịch thuật bài báo khoa học bằng mô hình cục bộ `Qwen3-1.7B-Q4_K_M.gguf` do backend FastAPI quản lý thông qua `llama.cpp`. Cloud API (Google Gemini) trở thành phương án tùy chọn/dự phòng thứ hai.
- **Minh bạch hóa trên giao diện (UI Engine Transparency)**: Người dùng luôn quan sát thấy rõ hệ thống đang chạy ở chế độ nào (`Local LLM` hay `Cloud API`) kèm tên mô hình, thông số ngữ cảnh và cảnh báo tài nguyên thời gian thực.

### 1.2. Rào Chắn Trần Cứng 4GB RAM (Hard 4GB RAM Ceiling)
- **Bài toán phần cứng người dùng**: Người dùng nghiên cứu khoa học và kỹ sư thường chạy đồng thời nhiều tác vụ trên máy trạm cá nhân (IDE lập trình, trình duyệt web nhiều tabs, ứng dụng văn phòng). Máy tính phổ thông có dung lượng RAM 8GB–16GB và suy luận chủ yếu trên CPU.
- **Ràng buộc bất biến**:
  - Tổng lượng RAM tối đa mà tiến trình Local LLM được phép chiếm dụng trên hệ điều hành **bắt buộc không được vượt quá ngưỡng trần 4.0 GB RAM**.
  - **Phân tích kích thước ngữ cảnh (Context Window vs. RAM Usage)**:
    - *Ngữ cảnh 4K – 8K (`n_ctx = 4096 .. 8192`)*: Trọng số mô hình (~1.03 GB) + KV Cache (~1.2 – 1.8 GB) + Bộ đệm suy luận $\approx$ **2.5 GB – 3.2 GB RAM** $\rightarrow$ **Vùng an toàn lý tưởng (Mặc định khuyến nghị)**.
    - *Ngữ cảnh 16K (`n_ctx = 16384`)*: Trọng số mô hình (~1.03 GB) + KV Cache (~2.4 – 2.6 GB) + Bộ đệm $\approx$ **3.5 GB – 4.0 GB RAM** $\rightarrow$ **Ngưỡng cận trên kịch trần (Hard Ceiling)**.
  - **Quy tắc thiết lập**:
    - Mặc định cấu hình `n_ctx = 8192` (8K context) để đạt hiệu năng suy luận mượt mà, tiêu thụ ~2.8 GB RAM.
    - Khóa trần cứng `max_n_ctx = 16384` (16K context). Tuyệt đối cấm cấu hình `n_ctx > 16384` trên CPU để bảo vệ toàn bộ hệ thống không bao giờ vượt qua 4GB RAM.

### 1.3. Cơ Chế Điều Phối Tuần Tự Tài Nguyên (Sequential Mutex Pipeline)
- **Nguyên tắc "Một Vận Động Viên Trên Đường Đua"**:
  - Indra OCR (6 mô hình ONNX: `det`, `rec`, `order`, `orient`, `mask`, `math` + PyMuPDF) tiêu tốn khoảng **1.5 GB – 2.0 GB RAM** khi quét layout và kết xuất trang.
  - Nếu nạp đồng thời cả Indra OCR và mô hình Local LLM (chiếm ~2.8 GB – 4.0 GB RAM), tổng mức chiếm dụng sẽ lên tới **4.5 GB – 6.0 GB RAM**, lập tức gây hiện tượng tràn bộ nhớ (Out-Of-Memory / OOM Crash) hoặc nghẽn phân luồng CPU (CPU Throttling).
- **Quy trình tuần tự bắt buộc**:
  1. **Phase 1 (Chạy OCR)**: Chỉ một mình Indra OCR được nạp vào bộ nhớ và xử lý toàn bộ các trang PDF.
  2. **Phase 2 (Thu hồi sạch tài nguyên OCR)**: Ngay khi OCR kết thúc, hệ thống kích hoạt thu hồi toàn bộ tài nguyên: dừng ThreadPool (`pool.shutdown(wait=False)`), xóa sạch tham chiếu các session ONNX và gọi `gc.collect()` để RAM trở về trạng thái cơ bản.
  3. **Phase 3 (Nạp & Dịch Local LLM)**: Sau khi RAM đã được giải phóng hoàn toàn, hệ thống mới nạp mô hình `Qwen3-1.7B-Q4_K_M.gguf` vào RAM (duy trì nghiêm ngặt dưới ngưỡng trần 4GB) và tiến hành dịch thuật theo cơ chế Adaptive Batching.
  4. **Phase 4 (Hậu xử lý)**: Khi kết thúc dịch hoặc khi người dùng bắt đầu tải lên bài báo mới, mô hình LLM sẵn sàng được `unload()` để nhường chỗ lại cho chu kỳ OCR kế tiếp.

---

## 2. Sơ Đồ Ranh Giới & Luồng Tuần Tự (Process Diagrams)

### 2.1. Sơ đồ Ranh giới Hệ thống (Use Case System Boundary)
```mermaid
flowchart LR
    subgraph Users ["Người dùng"]
        U["👤 Kỹ sư / Nhà nghiên cứu"]
    end

    subgraph SystemBoundary ["Hệ Thống Dịch Bài Báo (Local-First MVP)"]
        UC1["(1. Tải lên bài báo PDF / arXiv)"]
        UC2["(2. Quan sát & Chọn Engine trên UI: Local vs Cloud)"]
        UC3["(3. Chạy Indra OCR bóc tách layout)"]
        UC4["(4. Thu hồi sạch tài nguyên OCR: unload & gc)"]
        UC5["(5. Nạp Local LLM Qwen3 với trần cứng <= 4GB RAM)"]
        UC6["(6. Dịch Adaptive Batching 6-8 khối / ~1500 tokens)"]
        UC7["(7. Hiển thị 3-Layer HTML Canvas Viewer)"]

        UC1 --> UC2
        UC2 --> UC3
        UC3 -.->|<<sequential mutex>>| UC4
        UC4 -.->|<<release mem before load>>| UC5
        UC5 --> UC6
        UC6 --> UC7
    end

    subgraph HardwareConstraint ["Ràng Buộc Phần Cứng (Hard Ceiling <= 4GB RAM)"]
        RAM["🧠 Shared Host Memory<br>(Max 4.0 GB Allocation)"]
        ModelDisk[("📦 storage/models/<br>Qwen3-1.7B-Q4_K_M.gguf")]
    end

    U --> UC1
    U --> UC2
    UC3 <-->|Chiếm 1.5GB-2GB| RAM
    UC4 -.->|Trả lại 100% RAM| RAM
    UC5 <-->|Chiếm 2.8GB (8K ctx) <= 4GB Max| RAM
    UC5 <--> ModelDisk
```

### 2.2. Sơ đồ Luồng Tuần Tự Chi Tiết (Detailed Sequential Mutex Pipeline Flow)
```mermaid
flowchart TD
    Start([Bắt đầu xử lý bài báo]) --> LockCheck{Kiểm tra trạng thái bộ nhớ}
    
    LockCheck --> EnsureLLMUnloaded["Đảm bảo LLM đang Unloaded (nếu còn trong bộ nhớ)"]
    EnsureLLMUnloaded --> LoadOCR["Khởi tạo Indra OCR Service (ONNX CPU)"]
    
    LoadOCR --> ExecOCR["Bóc tách bố cục 2 cột, thứ tự đọc, bảng HTML, LaTeX"]
    ExecOCR --> OCRDone{OCR hoàn thành 100% trang?}
    
    OCRDone -- Có --> CleanupOCR["THU HỒI SẠCH TÀI NGUYÊN OCR:<br>1. pool.shutdown(wait=False)<br>2. del sessions (det, rec, math...)<br>3. gc.collect()<br>-> RAM trở về mức tối thiểu"]
    
    CleanupOCR --> CheckEngine{Kiểm tra cấu hình Engine<br>(Mặc định: Local LLM)?}
    
    CheckEngine -- "Local LLM (Qwen3)" --> CheckRAMCeiling["Xác định Context Window & Giới hạn RAM:<br>• n_ctx = 8192 (Mặc định ~2.8GB RAM)<br>• Cấm n_ctx > 16384 (Trần cứng 4.0GB RAM)"]
    
    CheckRAMCeiling --> LoadLLM["Nạp mô hình Qwen3-1.7B-Q4_K_M.gguf vào RAM<br>(Giới hạn chiếm dụng <= 4.0 GB)"]
    LoadLLM --> BatchInfer["Adaptive Batching: Dịch 6-8 khối (~1500 tokens) kèm [[BLK_XXXX]]"]
    BatchInfer --> LLMDone{Dịch xong tất cả các khối?}
    
    CheckEngine -- "Cloud API (Gemini)" --> CallCloud["Gọi Single-Call Gemini API qua Internet (0 MB RAM chiếm dụng)"]
    CallCloud --> LLMDone
    
    LLMDone -- Có --> SyncData["Đồng bộ tọa độ & Lưu kết quả vào SQLite (ocr_blocks)"]
    SyncData --> RenderCanvas["Render bài báo lên 3-Layer HTML Canvas Viewer"]
    RenderCanvas --> UpdateUIBadge["Cập nhật UI Engine Badge ('Local LLM: Qwen3-1.7B • 8K Ctx • 2.8GB RAM')"]
    UpdateUIBadge --> End([Hoàn tất])
```

---

## 3. Yêu Cầu Chức Năng Chi Tiết (Detailed Functional Requirements)

| Mã Yêu Cầu | Tên Chức Năng | Mô Tả Nghiệp Vụ & Quy Tắc Kỹ Thuật | Ưu Tiên |
|---|---|---|---|
| **FR-07.1** | Động Cơ Dịch Local-First Mặc Định | Hệ thống mặc định kích hoạt và sử dụng Local LLM Engine (`llama_cpp` + `Qwen3-1.7B-Q4_K_M.gguf`) khi khởi động backend mà không yêu cầu người dùng phải cấu hình API key. Cloud Gemini đóng vai trò tùy chọn thứ hai. | P0 (Must) |
| **FR-07.2** | Giới Hạn Ngữ Cảnh & Khóa Trần Cứng 4GB RAM | Cấu hình kích thước ngữ cảnh mặc định `n_ctx = 8192` (8K tokens) tiêu thụ ~2.8 GB RAM. Thiết lập giới hạn trần cứng `max_n_ctx = 16384` (16K tokens) tiêu thụ tối đa 4.0 GB RAM. Nghiêm cấm mọi thiết lập vượt quá 4GB RAM nhằm bảo vệ hệ điều hành và các ứng dụng khác của người dùng. | P0 (Must) |
| **FR-07.3** | Bộ Điều Phối Tuần Tự Tài Nguyên (Sequential Mutex Scheduler) | Bắt buộc thực thi tuần tự hoàn toàn giữa Indra OCR và Local LLM. Sau khi OCR kết thúc, bắt buộc giải phóng toàn bộ session ONNX, dừng threadpool và gọi `gc.collect()`. Chỉ khi bộ nhớ đã được giải phóng mới được nạp LLM. Ngược lại, nếu có tác vụ OCR mới, LLM phải được unload trước. | P0 (Must) |
| **FR-08.1** | Huy Hiệu Trạng Thái Động Cơ Trên UI (UI Engine Status Badge) | Giao diện hiển thị rõ ràng huy hiệu trạng thái tại Header: <br>- 🟢 `Local LLM: Qwen3-1.7B (8K Ctx • Offline)`<br>- 🔵 `Cloud API: Gemini-3.5-Flash (Single-Call 1M)`<br>Kèm công tắc chuyển đổi (Engine Switcher) để người dùng chủ động lựa chọn. | P0 (Must) |
| **FR-08.2** | Báo Cáo Tiến Độ & Bộ Nhớ Thời Gian Thực (SSE Stream) | Kênh Server-Sent Events (SSE) phát thông tin chi tiết về từng giai đoạn: `phase: "ocr"` $\rightarrow$ `phase: "reclaiming_memory"` $\rightarrow$ `phase: "loading_llm"` $\rightarrow$ `phase: "translating_local"` kèm phần trăm hoàn thành. | P0 (Must) |

---

## 4. Rào Chắn Kiến Trúc Bất Biến (Architecture Guardrails)

1. **Rào chắn Trần Cứng 4GB RAM (Hardware Invariant):**
   - Bất kỳ mã nguồn nào khởi tạo `Llama(...)` đều phải kiểm tra và xác nhận tham số `n_ctx <= 16384`. Tuyệt đối không cho phép vượt quá ngưỡng 4GB RAM khi chạy trên CPU.
2. **Rào chắn Cách Ly Tuần Tự (Mutual Exclusion Invariant):**
   - Cấm mọi hành vi gọi hàm nạp mô hình LLM khi `IndraOcrService` chưa gọi `unload()`.
   - Áp dụng cờ khóa nội bộ `_ai_resource_lock: asyncio.Lock` để đảm bảo hai mô hình AI không bao giờ tồn tại đồng thời trong không gian bộ nhớ tiến trình.
3. **Rào chắn Minh Bạch Trạng Thái (UI Observability):**
   - API trả về trạng thái phiên dịch bắt buộc phải chứa trường `active_engine: "local_llm" | "cloud_gemini"` và `model_name: string` để UI hiển thị chính xác cho người dùng.
