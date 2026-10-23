# Business Requirement Document (BRD) — Paper Translation

**Tầng tài liệu**: Business Layer  
**Dự án**: Paper Translation (Personal & Open-Source Edition)  
**Phiên bản**: 3.3 (Indra OCR, Standalone Llama.cpp Server + Gemma-4-E2B & 3-Layer HTML Canvas Edition)  
**Ngày cập nhật**: 2026-10-23  
**Trạng thái**: Approved  

---

## 1. Bối cảnh & Vấn đề nghiệp vụ (Problem Statement)

Là một kỹ sư / nhà nghiên cứu trong lĩnh vực **Công nghệ thông tin (IT)** và **Trí tuệ nhân tạo (AI / Machine Learning / Deep Learning)**, nhu cầu đọc và hấp thụ các bài báo khoa học xuất sắc (từ arXiv, hội nghị NeurIPS, ICML, CVPR, ICLR, ACL...) là công việc diễn ra thường xuyên. 

Tuy nhiên, các giải pháp dịch thuật truyền thống (kể cả phiên bản thử nghiệm ban đầu của dự án) đã bộc lộ **các sai lầm nghiêm trọng**:

1. **Mất đứt gãy ngữ cảnh do băm nhỏ văn bản quá mức (Micro-Chunking Context Loss):** Khi chia cắt bài báo thành các đoạn ngắn rời rạc (paragraphs/chunks nhỏ) để dịch, mô hình AI mất đi góc nhìn toàn cục, dịch sai lệch các đại từ tham chiếu liên trang (*"this framework", "our proposed method", "it"*), thuật ngữ học thuật bị bất nhất giữa phần mở đầu và kết luận.
2. **Nghẽn cổ chai khi nhúng LLM trực tiếp vào tiến trình Web Server (In-Process Blocking):** Việc chạy mô hình LLM thông qua thư viện binding nội bộ (`llama-cpp-python`) gộp chung trong tiến trình FastAPI gây tranh chấp GIL, làm đơ vòng lặp sự kiện bất đồng bộ và hạn chế khả năng tối ưu hóa phần cứng chuyên sâu của `llama.cpp` gốc.
3. **Vỡ hoàn toàn cấu trúc & thứ tự đọc (Reading Order Spillage):** Bài báo khoa học hầu hết có định dạng 2 cột (Double-Column), xen kẽ bảng số liệu và hình ảnh. Việc bóc tách văn bản thô sơ làm chữ cột trái nhảy sang cột phải, biến bài báo thành một mớ hỗn độn.
4. **Mất diện mạo học thuật chuẩn (Loss of Original Layout):** Render lại văn bản dịch thành trang blog HTML tuyến tính khiến người đọc mất khả năng định vị trực quan sơ đồ, đồ thị và bảng thực nghiệm so với tài liệu gốc.

---

## 2. Tầm nhìn sản phẩm (Product Vision - Version 3.3 Standalone Local-First)

Xây dựng **Paper Translation** thành công cụ dịch bài báo khoa học tinh gọn, đạt chuẩn xuất bản học thuật với triết lý **Local-First & Standalone Serving (Tách Biệt Tiến Trình Suy Luận, Tối Ưu Phần Cứng & Bảo Mật Tuyệt Đối)**:
- **Bóc tách bố cục chuẩn xác bằng Indra OCR (`datalab-to/indra`):** Nhận diện cấu trúc 2 cột, thứ tự đọc chuẩn (reading order), bảng biểu HTML và công thức toán học LaTeX trên CPU.
- **Bảo vệ tài nguyên phần cứng tuần tự (Sequential Mutex Execution):** OCR chạy trước $\rightarrow$ Thu hồi sạch 100% tài nguyên RAM trước khi khởi chạy tiến trình suy luận LLM.
- **Kiến trúc Serving Độc Lập (`llama.cpp` gốc + `gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf`):**
  - Cài đặt và sử dụng trực tiếp `llama.cpp` gốc (thông qua `uv/pip`), tách thành một **Service chạy `llama.cpp server` riêng biệt** dưới sự quản lý của Backend và giao tiếp qua **Python HTTP Client nội bộ (`127.0.0.1`)**.
  - Khai thác mô hình chất lượng cao **`gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf`**, cho phép tăng tốc phần cứng, cấu hình tối ưu **4 P-cores trên CPU Intel Core i5-13500H**, giới hạn trần cứng **$\le 8.0\text{ GB}$ RAM**.
  - Tối ưu hóa cửa sổ ngữ cảnh **16K tokens (`n_ctx=16384`)** (hỗ trợ tùy chọn 8K `n_ctx=8192`) sao cho mỗi lô đầu vào (bao gồm System Prompt + Text của bài báo) đạt **2,000 – 2,500 từ tiếng Anh**, và dành không gian đầu ra cực kỳ dư dả để văn bản tiếng Việt sinh ra (dài gấp **2.0 – 2.5 lần** số từ/token tiếng Anh) **tuyệt đối không bao giờ bị tràn context**.
- **Minh bạch hóa động cơ trên UI:** Người dùng luôn theo dõi được trạng thái Engine đang kích hoạt (`Local LLM: Gemma-4-E2B` hay `Cloud API`).
- **Tái hiện nguyên bản trên Web bằng 3-Layer HTML Canvas:** Trực quan hóa bản dịch tiếng Việt trực tiếp lên canvas theo đúng tỷ lệ, vị trí 2 cột, khung ảnh và bảng biểu của tài liệu gốc.
- **Xuất PDF 1-click chất lượng cao:** Xuất bản dịch từ HTML Canvas sang tệp PDF tiếng Việt giữ nguyên bố cục tương đương bản gốc.

---

## 3. Chỉ số thành công & KPIs (Success Metrics)

| Chỉ số | Mục tiêu kỳ vọng (v3.3) | Phương pháp đo lường |
|---|---|---|
| **Giới hạn chiếm dụng RAM phần cứng** | **$\le 8.0\text{ GB}$ RAM** kịch trần (Thực tế ~4.0–4.5 GB với Gemma-4-E2B 16K ctx) | Task Manager / Resource Monitor APM |
| **Tối ưu hóa CPU & Phần cứng** | Khai thác đúng **4 P-cores trên Intel Core i5-13500H** + Hardware Acceleration | Kiểm tra tham số `--threads 4 --threads-batch 4` của `llama-server` |
| **Quy mô lô dịch & Chống tràn Context** | Input **2,000 – 2,500 từ tiếng Anh** / lần gọi; Output dự phòng gấp **2.0 – 2.5 lần** (0% lỗi tràn context) | Kiểm tra log batch word count & `finish_reason == "stop"` |
| **Tính độc lập & bảo mật dữ liệu** | 100% ngoại tuyến ở chế độ Local-First qua mạng Loopback nội bộ | Kiểm tra ngắt kết nối Internet vẫn dịch bình thường |
| **Bảo toàn bố cục gốc (Layout Fidelity)** | Tái hiện đúng $\ge 95\%$ vị trí 2 cột, khối văn bản và hình vẽ trên Canvas | Đối chiếu trực quan Canvas với PDF gốc |
| **Bảo toàn công thức LaTeX & Bảng** | 100% công thức toán học và bảng biểu không bị dịch đè hoặc sai cú pháp | Kiểm tra KaTeX SVG rendering |
| **Độ chuẩn thuật ngữ CNTT & AI** | $\ge 98\%$ thuật ngữ AI/CNTT được dịch đúng ngữ cảnh học thuật nhờ Gemma-4-E2B QAT | Kiểm tra đối chiếu từ điển chuyên sâu |
| **Trải nghiệm xuất PDF** | 1 click xuất ra tệp PDF tiếng Việt tương tự bố cục gốc | Xuất qua Canvas to PDF engine |

---

## 4. Đối tượng sử dụng mục tiêu (Target Users)

1. **Giai đoạn 1 (Cá nhân):**
   - Bản thân tôi (Nhà nghiên cứu / Kỹ sư CNTT & AI) sử dụng laptop trang bị **Intel Core i5-13500H** cần đọc bài báo chuyên ngành nhanh chóng, chuẩn xác và có thể in/lưu trữ bản dịch PDF đẹp mắt.
2. **Giai đoạn 2 (Cộng đồng mã nguồn mở):**
   - Sinh viên, nghiên cứu sinh, giảng viên và kỹ sư AI/CNTT tại Việt Nam mong muốn một công cụ tự host, miễn phí, tối ưu hóa phần cứng máy tính cá nhân.

---

## 5. Ranh giới giải pháp (Refined Scope v3.3)

### In-Scope:
- Tiếp nhận tệp **PDF** bài báo khoa học (tải lên trực tiếp hoặc qua liên kết arXiv).
- Chạy **Indra OCR** trên CPU để phân tích layout, nhận dạng text, reading order, bảng HTML và công thức LaTeX, sau đó thu hồi sạch 100% RAM.
- Trích xuất ảnh nền toàn trang (Layer 0) và ảnh sơ đồ/đồ thị từ PDF gốc dựa trên tọa độ Bounding Box.
- Quản lý tiến trình **Standalone `llama.cpp` Server** chạy mô hình **`gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf`** (cấu hình 4 P-cores, trần 8GB RAM, 16K/8K context) và giao tiếp qua **Python Client** trong mạng nội bộ.
- Gom cụm văn bản đầu vào (System Prompt + Text bài báo) đạt **2,000 – 2,500 từ tiếng Anh** mỗi lượt gọi, đảm bảo đầu ra tiếng Việt dư dả gấp **2.0 – 2.5 lần** không bị tràn ngữ cảnh.
- Giữ tùy chọn gọi **Google Gemini API** (Single-Call) khi người dùng chọn chế độ Cloud.
- Sử dụng **3-Layer HTML Canvas** tại Frontend để tái hiện lại giao diện bài báo bản dịch tiếng Việt giống hệt tài liệu gốc và xuất tệp **PDF bản dịch hoàn chỉnh**.

### Out-of-Scope:
- Nhúng trực tiếp mô hình vào bên trong tiến trình FastAPI qua `llama-cpp-python` in-process (đã loại bỏ để chuyển sang Standalone Server Service).
- Hệ thống tài khoản người dùng, đăng nhập OAuth, thanh toán SaaS.
- Huấn luyện lại model OCR hoặc LLM.
