# 02 - Kiến Trúc Tổng Thể Hệ Thống (High-Level System Architecture)

**Tầng tài liệu**: Architecture Layer (Single Source of Truth)  
**Hệ thống**: Paper Translation (Personal & Open-Source Edition)  
**Phiên bản**: 2.0 (Scaled Down & Focused)  
**Ngày cập nhật**: 2026-10-05  
**Trạng thái**: Approved  

---

## 1. Bối cảnh & Mục tiêu Kiến trúc Tinh gọn

Theo yêu cầu tái định vị phạm vi sản phẩm:
- **Giai đoạn trước mắt:** Phục vụ nhu cầu cá nhân của nhà nghiên cứu / kỹ sư chuyên ngành **Công nghệ thông tin (IT)** và **Trí tuệ nhân tạo (AI)** để dịch nhanh các bài báo (PDF, DOCX).
- **Giai đoạn tiếp theo:** Đóng gói mã nguồn mở (Open-Source) cho cộng đồng nghiên cứu tự do cài đặt và sử dụng (Self-hosted / 1-click Docker).
- **Trải nghiệm cốt lõi:** Đọc song ngữ trên Web UI và tải về tệp **PDF bản dịch tiếng Việt hoàn chỉnh** giữ nguyên 100% công thức toán học LaTeX, hình ảnh minh họa và bảng biểu.

Kiến trúc hệ thống chuyển dịch từ mô hình Cloud đa người dùng phức tạp sang mô hình **Self-Contained Local Monolith** (Độc lập, tinh giản tối đa, không cần cài đặt nhiều dịch vụ nền rườm rà).

---

## 2. Ước lượng Quy mô Cá nhân & Tự vận hành (BOTEC Estimation)

### 2.1. Giả định sử dụng cá nhân & Self-Hosted
- **Người dùng đồng thời:** 1 người (Cá nhân) đến 2–5 người (khi tự host trong phòng lab nghiên cứu nhỏ).
- **Khối lượng tài liệu:** 2 – 5 bài báo/ngày (khoảng 15 – 30 bài báo/tuần).
- **Kích thước trung bình một bài báo:** 10 – 25 trang (~6,000 – 12,000 từ, ~200 – 400 phân đoạn văn bản, 50 – 150 công thức toán LaTeX).
- **Dung lượng tệp tải lên:** 2MB – 15MB (giới hạn tối đa 50MB cho cả PDF và DOCX).
- **Dung lượng lưu trữ cục bộ:**
  - 100 bài báo $\times$ 5MB = 500MB (hoàn toàn nằm gọn trong ổ cứng cá nhân).

### 2.2. Chỉ tiêu chất lượng dịch vụ (SLA & Latency Targets)
- **Tiếp nhận tải lên tệp PDF/DOCX:** P99 $< 1.0$ giây.
- **Bóc tách cấu trúc tài liệu & cô lập LaTeX:** P95 $< 5.0$ giây.
- **Dịch thuật toàn bộ bài báo qua LLM:** P95 $< 30 – 45$ giây cho bài 20 trang.
- **Tải tệp PDF bản dịch tiếng Việt hoàn chỉnh:** P95 $< 3.0$ giây.
- **Tiêu thụ tài nguyên máy:** RAM $< 1$GB, CPU $< 15\%$ khi ở trạng thái nhàn rỗi.

---

## 3. Sơ đồ Tôpô Kiến trúc Tổng thể (High-Level Topology)

Hệ thống được gói gọn trong một kiến trúc **Single Self-Contained Application** cực kỳ dễ chạy trên máy tính cá nhân hoặc qua Docker:

```mermaid
flowchart TD
    subgraph Client ["Client Layer"]
        WebUI["🌐 Web UI (React/Vite SPA)<br>Dual-Pane Reader, Sync Scroll, PDF Downloader"]
    end

    subgraph AppServer ["Core Backend (FastAPI Self-Contained)"]
        Router["⚡ API Gateway / Routers<br>(Upload, arXiv, Sessions, Export)"]
        
        subgraph Pipeline ["Processing & Translation Pipeline"]
            DocParser["1. Multi-Format Parser<br>(PyMuPDF for PDF | python-docx for DOCX)"]
            LaTeXIsolator["2. LaTeX, Table & Figure Isolator<br>(Regex AST Token Masking)"]
            ITTranslationEngine["3. IT & AI Translation Engine<br>(Domain Context Prompting + Batching)"]
            Reassembler["4. Structure & Math Re-assembler"]
        end

        TaskManager["📬 Async Task Manager<br>(asyncio.Queue / BackgroundTasks)"]
        SSEStreamer["📡 SSE Broadcaster<br>(Real-time Progress Streaming)"]
        PDFRenderer["📑 PDF Export Engine<br>(WeasyPrint / HTML Paged Media)"]
    end

    subgraph LocalStorage ["Local Storage & State Tier (Zero-Hassle)"]
        DB[(🗄️ SQLite Database<br>Sessions, Segments, MathTokens, Glossary)]
        FileStore[(📁 Local File System<br>raw-files/, assets/, exports/)]
    end

    subgraph ExternalAI ["External AI Services"]
        CloudLLM["🌐 Cloud LLM API (Google Gemini / OpenAI / Claude)"]
        LocalLLM["💻 Local LLM via Ollama (Optional Offline Run)"]
        ArxivAPI["🌐 arXiv.org (Fetch PDF & Metadata)"]
    end

    WebUI <-->|HTTP REST & SSE| Router
    Router --> TaskManager
    Router <--> DB
    Router <--> FileStore

    TaskManager --> Pipeline
    DocParser <--> FileStore
    DocParser <--> ArxivAPI
    LaTeXIsolator <--> DB
    ITTranslationEngine <--> CloudLLM
    ITTranslationEngine <--> LocalLLM
    Reassembler --> DB

    Pipeline -.->|Gửi tiến độ| SSEStreamer
    SSEStreamer -.->|SSE Stream| WebUI

    Router --> PDFRenderer
    PDFRenderer <--> DB
    PDFRenderer <--> FileStore
    PDFRenderer -->>|Tải file PDF| WebUI
```

---

## 4. Ma trận Đánh giá Đánh đổi Kỹ thuật (Technical Trade-Offs)

Tuân thủ phương pháp luận: **Solves / Worsens / Change it when**:

| Thành phần | Lựa chọn kiến trúc | What it solves (Giải quyết vấn đề gì) | What it worsens (Gây ra gánh nặng gì) | Change it when (Thay đổi khi nào) |
|---|---|---|---|---|
| **Cơ sở dữ liệu** | SQLite (WAL Mode) | **Không cần cài đặt DB server**, lưu thẳng thành 1 file `.db` trên máy; khởi động tức thì; hỗ trợ đầy đủ ACID và Foreign Keys; dễ dàng backup chỉ bằng cách copy file. | Không tối ưu cho hàng nghìn kết nối ghi đồng thời từ nhiều máy chủ khác nhau. | Đổi sang PostgreSQL khi triển khai hệ thống SaaS nhiều người dùng với lưu lượng ghi lớn. |
| **Xử lý Bất đồng bộ** | In-Process Task Queue (Python `asyncio.Queue`) | **Không cần cài đặt Redis hay Celery** cồng kềnh; người dùng chỉ cần chạy 1 lệnh `uvicorn` là có đủ cả API lẫn worker; quản lý tiến trình mượt mà. | Nếu tiến trình server bị tắt đột ngột, tác vụ đang chạy trong hàng đợi RAM sẽ bị hủy (cần restart lại tác vụ). | Đổi sang Redis + Celery khi cần phân tán tác vụ ra nhiều máy tính worker khác nhau. |
| **Bóc tách Đa định dạng** | PyMuPDF (PDF) + `python-docx` (DOCX) | Tốc độ trích xuất cực nhanh; đọc chuẩn xác cả PDF và DOCX; cô lập công thức toán học và trích xuất bảng/hình nhúng hiệu quả. | Không tự động OCR được các tệp PDF scan hình ảnh chất lượng thấp (chỉ hỗ trợ file có text layer). | Tích hợp thêm module OCR (như Tesseract / PaddleOCR) khi có nhu cầu xử lý tài liệu scan cũ. |
| **Kết xuất PDF bản dịch** | HTML/CSS Paged Media + WeasyPrint | Dễ dàng tùy biến dàn trang chuẩn A4 bằng HTML/CSS; kết xuất hoàn hảo công thức toán KaTeX/MathJax và nhúng trực tiếp bảng số liệu/hình vẽ. | Tốc độ biên dịch tệp PDF tốn từ 2 – 5 giây cho tài liệu dài; cần cài đặt thư viện hệ thống Pango/Cairo. | Đổi sang Typst hoặc headless Chrome nếu cần tốc độ sinh PDF dưới 500ms. |
| **Mô hình Dịch thuật** | Adapter đa nguồn: Cloud API (Gemini/OpenAI) + Local LLM (Ollama) | Cho phép người dùng linh hoạt: dùng API trả phí giá rẻ chất lượng cao (Gemini Flash) hoặc dùng Ollama để dịch hoàn toàn offline bảo mật tuyệt đối. | Mô hình local chạy offline đòi hỏi máy tính cá nhân có cấu hình GPU tương đối tốt. | Mặc định sử dụng API Cloud cho người dùng phổ thông, cung cấp switch bật Local LLM trong settings. |

---

## 5. Rào chắn Chống Lỗi Tinh gọn (Resilience Guardrails)

1. **Bảo vệ Bộ nhớ khi Xử lý File Lớn (Out-Of-Memory Protection):**
   - Giới hạn tệp tải lên tối đa 50MB. Trình bóc tách xử lý tệp theo luồng (streaming) hoặc phân trang, giải phóng bộ nhớ đệm ngay sau khi trích xuất xong văn bản và hình ảnh.
2. **Xử lý Ngắt quãng Tiến trình Dịch (Process Interruption):**
   - Lưu trạng thái hoàn thành của từng phân đoạn (`status = 'TRANSLATED'`) trực tiếp vào SQLite. Nếu bị mất điện hoặc crash, người dùng chỉ cần bấm "Tiếp tục" để dịch tiếp các đoạn còn lại mà không cần dịch lại từ đầu.
3. **Chống Lỗi Vỡ Font Tiếng Việt trên Tệp PDF:**
   - Đóng gói sẵn bộ font Unicode chuẩn học thuật (Noto Serif / Roboto) trong thư mục tài nguyên của dự án; chỉ định rõ ràng đường dẫn font trong CSS template để bảo đảm PDF xuất ra không bao giờ bị lỗi dấu tiếng Việt.
