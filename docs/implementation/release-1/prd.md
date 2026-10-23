# Product Requirements Document (PRD): Release 1 (Personal Core MVP v3.3)

**Tầng tài liệu**: Implementation Layer  
**Release**: release-1 (Personal Core MVP)  
**Phiên bản**: 3.3 (Indra OCR, Standalone Llama.cpp Server + Gemma-4-E2B & 3-Layer HTML Canvas)  
**Ngày cập nhật**: 2026-10-23  
**Tác giả**: Senior IT-BA & PO  
**Trạng thái**: Approved  
**Chất lượng yêu cầu**: 98/100  

---

## 1. Mục tiêu Đợt Phát hành & Bối cảnh Nghiệp vụ (Business Context)

### 1.1. Mục tiêu đợt phát hành (Release Goals)
- **Tham chiếu Business Layer:** Bám sát tầm nhìn tại [docs/business/brd.md](file:///E:/MyProject/paper-translation/docs/business/brd.md) và quyết định kiến trúc [ADR-002](file:///E:/MyProject/paper-translation/docs/architecture/adr/ADR-002.md).
- **Trọng tâm Release 1 (v3.3 — Standalone Local-First & Gemma-4-E2B Edition):**
  1. Bóc tách chính xác bố cục 2 cột, thứ tự đọc (`reading_order`), bảng biểu HTML và công thức LaTeX bằng **Indra OCR (`indra_ocr` ONNX CPU)** kết hợp **Chuẩn hóa tọa độ `[0.0 .. 1.0]`**.
  2. Bảo toàn **100% hình ảnh, sơ đồ vector (TikZ/PGFPlots), đồ thị và đường kẻ bảng** thông qua việc kết xuất ảnh nền trang gốc độ phân giải cao (Layer 0) và crop riêng khối `figure` bằng `PyMuPDF`.
  3. **Kiến trúc Serving Độc Lập (`llama.cpp` gốc + `gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf`):**
     - Không sử dụng `llama-cpp-python` gộp chung bên trong tiến trình FastAPI nữa; chuyển sang cài đặt trực tiếp thư viện `llama.cpp` gốc qua `uv/pip`, viết một **Service riêng quản lý tiến trình `llama.cpp server`** và sử dụng **Python Client để giao tiếp qua mạng nội bộ (`127.0.0.1`)**.
     - Khai thác mô hình **`gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf`**, cho phép sử dụng phần cứng, cấu hình tối ưu **4 P-cores trên Intel Core i5-13500H**, giới hạn trần cứng **RAM $\le 8.0\text{ GB}$**.
     - Tối ưu ngữ cảnh **16K tokens (`n_ctx=16384`)** (hoặc tùy chọn 8K) sao cho mỗi lượt gọi có Input (System Prompt + Text bài báo) nằm trong **2,000 – 2,500 từ tiếng Anh**, và Output tiếng Việt (dài gấp **2.0 – 2.5 lần** tiếng Anh) cực kỳ dư dả, **tuyệt đối không bị tràn context**.
  4. **Thực thi tuần tự ngặt nghèo (Sequential Mutex):** Không chạy song song OCR và LLM; giải phóng sạch 100% tài nguyên OCR trước khi khởi chạy/gọi dịch vụ `llama.cpp server`.
  5. Minh bạch hóa trạng thái trên UI bằng **Huy hiệu Engine Status Badge** (`Local LLM: Gemma-4-E2B` vs `Cloud API`).
  6. Tái hiện bài báo bản dịch tiếng Việt trên **3-Layer HTML5 Canvas** và xuất tệp PDF bản dịch hoàn chỉnh giữ trọn vẹn bố cục 2 cột.

---

## 2. Yêu cầu Chức năng Tinh gọn (Functional Requirements v3.3)

| Mã yêu cầu | Tên chức năng | Mô tả nghiệp vụ | Quy tắc nghiệp vụ & Kỹ thuật (Business & Technical Rules) | Mức ưu tiên |
|---|---|---|---|---|
| **FR-01** | Tiếp nhận tệp PDF & arXiv | Nhận tệp PDF tải lên từ máy tính hoặc tự động tải về khi dán mã/URL arXiv | Giới hạn tối đa 50MB. Kiểm tra định dạng magic bytes `%PDF-`. | P0 (Must) |
| **FR-02** | Indra OCR & Chuẩn hóa Tọa độ `[0..1]` | Chạy `indra_ocr` trên CPU để phân tích bố cục 2 cột, thứ tự đọc, bảng HTML, LaTeX và tọa độ hộp | Chuyển đổi toàn bộ tọa độ pixel sang tọa độ chuẩn hóa tương đối `[x0_norm, y0_norm, x1_norm, y1_norm]` trong đoạn `[0.0, 1.0]` theo kích thước trang. | P0 (Must) |
| **FR-03** | Kết xuất Ảnh Nền Trang (Layer 0) & Crop Hình Ảnh | Kết xuất từng trang PDF gốc thành ảnh độ nét cao (200 DPI) và crop riêng các khối `figure` bằng PyMuPDF | Lưu ảnh nền trang tại `storage/pages/` (bảo toàn 100% sơ đồ vector TikZ, đường kẻ bảng, công thức) và ảnh hình vẽ tại `storage/figures/`. | P0 (Must) |
| **FR-04** | Dịch Thuật Đám Mây Tùy Chọn (Gemini Single-Call) | Dịch toàn văn qua Google Gemini API (`max_tokens=65536`) khi người dùng lựa chọn chế độ Cloud | Giữ nguyên 100% LaTeX `$..$`, `<table>` và `[[BLK_XXXX]]`. Tự động gọi tiếp nối (Auto-Continuation) nếu chạm trần output token. | P1 (Should) |
| **FR-05** | Tái hiện Bài Báo Trên 3-Layer HTML Canvas | Hiển thị từng trang bài báo trên `<canvas>` với 3 lớp: Base Page, Smart Redaction (`#FFFFFF`) và Translated Text + KaTeX SVG | Tự động co giãn cỡ chữ (Binary-Search Font Auto-Scaling) để chữ tiếng Việt nằm gọn trong BBox gốc. Hỗ trợ Zoom, Pan và nút bật/tắt xem đối chiếu bản gốc tiếng Anh. | P0 (Must) |
| **FR-06** | Xuất Tệp PDF Bản Dịch Hoàn Chỉnh | Xuất và tải về tệp PDF tiếng Việt giữ nguyên bố cục 2 cột như bản gốc chỉ với 1 cú click | Kết xuất trực tiếp từ hệ thống trang Canvas độ phân giải cao sang tệp PDF chuẩn. | P0 (Must) |
| **FR-07** | Dịch Vụ Serving Riêng `llama.cpp` & Model `Gemma-4-E2B` | Xây dựng service riêng chạy `llama.cpp server` gốc với model `gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf`, giao tiếp qua Python Client nội bộ | Cấu hình **4 P-cores trên Intel Core i5-13500H**, cho phép tăng tốc phần cứng, giới hạn **RAM $\le 8.0\text{ GB}$**, tối ưu ngữ cảnh **16K (`16384`) / 8K (`8192`) tokens**. Input (System Prompt + Text bài báo) đạt **2,000 – 2,500 từ tiếng Anh**, Output dư dả gấp **2.0 – 2.5 lần** chống tràn context. Chi tiết tại [local-llm-service-prd.md](file:///E:/MyProject/paper-translation/docs/implementation/release-1/features/local-llm-service-prd.md). | P0 (Must) |
| **FR-08** | Chỉ Báo Động Cơ Trên UI (Engine Status Indicator) | Hiển thị huy hiệu trạng thái tại Header cho biết đang chạy Local Standalone Server hay Cloud API | 🟢 `Local LLM: Gemma-4-E2B (16K Ctx • 4 P-Cores)` vs 🔵 `Cloud API: Gemini (Online)` kèm công tắc chuyển đổi engine linh hoạt. | P0 (Must) |

---

## 3. Rào chắn Kiến trúc (Architecture Guardrails v3.3)

1. **Rào chắn Tách Biệt Tiến Trình Serving (Standalone Serving Guardrail):** Tuyệt đối không nhúng mô hình trực tiếp vào bên trong tiến trình FastAPI qua `llama-cpp-python`. Bắt buộc khởi chạy `llama.cpp server` như một service độc lập dưới sự quản lý của Backend và giao tiếp qua Python HTTP Client trên mạng nội bộ (`127.0.0.1`).
2. **Rào chắn Điều Phối Tuần Tự & Trần Cứng 8GB RAM / 4 P-Cores:** Không chạy đồng thời Indra OCR và `llama.cpp server`. Sau khi OCR kết thúc, bắt buộc gọi `unload()` và `gc.collect()` trước khi khởi chạy `llama.cpp server`. Tiến trình `llama.cpp server` phải khóa cứng `--threads 4` (4 P-cores trên Intel Core i5-13500H) và tổng mức chiếm dụng bộ nhớ **$\le 8.0\text{ GB}$ RAM**.
3. **Rào chắn Ngân Sách Từ 2,000–2,500 Words & Chống Tràn Ngữ Cảnh Tiếng Việt:** Mỗi lô gửi tới `llama.cpp server` phải có tổng độ dài (System Prompt + Text bài báo) nằm trong khoảng **2,000 – 2,500 từ tiếng Anh**, và không gian Output phải được cấp phát dư dả tối thiểu gấp **2.0 – 2.5 lần** độ dài token đầu vào (ưu tiên `n_ctx = 16384`, `max_tokens = 10240`) để bản dịch tiếng Việt không bao giờ bị cắt cụt.
4. **Rào chắn 3-Layer Canvas Fidelity & Tọa Độ Chuẩn Hóa `[0..1]`:** Luôn vẽ ảnh nền trang gốc (Layer 0), chỉ xóa trắng (`#FFFFFF`) đúng vùng BBox của các khối văn bản đã dịch (`is_translatable = True`) theo hệ tọa độ chuẩn hóa `[0.0 .. 1.0]`.
