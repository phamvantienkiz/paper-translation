# Business Requirement Document (BRD) — Paper Translation

**Tầng tài liệu**: Business Layer  
**Dự án**: Paper Translation (Personal & Open-Source Edition)  
**Phiên bản**: 3.0 (Indra OCR, Single-Call Gemini & HTML Canvas Layout Edition)  
**Ngày cập nhật**: 2026-10-22  
**Trạng thái**: Approved  

---

## 1. Bối cảnh & Vấn đề nghiệp vụ (Problem Statement)

Là một kỹ sư / nhà nghiên cứu trong lĩnh vực **Công nghệ thông tin (IT)** và **Trí tuệ nhân tạo (AI / Machine Learning / Deep Learning)**, nhu cầu đọc và hấp thụ các bài báo khoa học xuất sắc (từ arXiv, hội nghị NeurIPS, ICML, CVPR, ICLR, ACL...) là công việc diễn ra thường xuyên. 

Tuy nhiên, các giải pháp dịch thuật truyền thống (kể cả phiên bản thử nghiệm ban đầu của dự án) đã bộc lộ **các sai lầm nghiêm trọng**:

1. **Mất đứt gãy ngữ cảnh do băm nhỏ văn bản (Chunking Context Loss):** Khi chia cắt bài báo thành các đoạn ngắn rời rạc (paragraphs/chunks) để dịch, mô hình AI mất đi góc nhìn toàn cục, dịch sai lệch các đại từ tham chiếu liên trang (*"this framework", "our proposed method", "it"*), thuật ngữ học thuật bị bất nhất giữa phần mở đầu và kết luận.
2. **Vỡ hoàn toàn cấu trúc & thứ tự đọc (Reading Order Spillage):** Bài báo khoa học hầu hết có định dạng 2 cột (Double-Column), xen kẽ bảng số liệu và hình ảnh. Việc bóc tách văn bản thô sơ làm chữ cột trái nhảy sang cột phải, biến bài báo thành một mớ hỗn độn.
3. **Mất diện mạo học thuật chuẩn (Loss of Original Layout):** Render lại văn bản dịch thành trang blog HTML tuyến tính khiến người đọc mất khả năng định vị trực quan sơ đồ, đồ thị và bảng thực nghiệm so với tài liệu gốc.

---

## 2. Tầm nhìn sản phẩm (Product Vision - Version 3.0)

Xây dựng **Paper Translation** thành công cụ dịch bài báo khoa học tinh gọn, đạt chuẩn xuất bản học thuật:
- **Bóc tách bố cục chuẩn xác bằng Indra OCR (`datalab-to/indra`):** Nhận diện cấu trúc 2 cột, thứ tự đọc chuẩn (reading order), bảng biểu HTML và công thức toán học LaTeX.
- **Trích xuất bảo toàn hình ảnh minh họa:** Tự động phát hiện và trích xuất nguyên vẹn các sơ đồ kiến trúc, đồ thị và hình vẽ từ PDF gốc dựa trên Bounding Box của OCR.
- **Dịch toàn văn 1 lần gọi duy nhất (Gemini Single-Call Translation):** Tận dụng cửa sổ ngữ cảnh khổng lồ (1M–2M tokens) của Google Gemini để dịch toàn bộ bài báo trong 1 request duy nhất, loại bỏ triệt để hiện tượng mất ngữ cảnh và đảm bảo văn phong học thuật đồng nhất 100%.
- **Tái hiện nguyên bản trên Web bằng HTML Canvas (Same-Origin Paper View):** Trực quan hóa bản dịch tiếng Việt trực tiếp lên canvas theo đúng tỷ lệ, vị trí 2 cột, khung ảnh và bảng biểu của tài liệu gốc.
- **Xuất PDF 1-click chất lượng cao:** Xuất bản dịch từ HTML Canvas sang tệp PDF tiếng Việt giữ nguyên bố cục tương đương bản gốc.

---

## 3. Chỉ số thành công & KPIs (Success Metrics)

| Chỉ số | Mục tiêu kỳ vọng (v3.0) | Phương pháp đo lường |
|---|---|---|
| **Tính toàn vẹn ngữ cảnh** | 100% bài báo được dịch trong **1 lần gọi AI duy nhất** | Ghi log API call (Single Prompt Request) |
| **Bảo toàn bố cục gốc (Layout Fidelity)** | Tái hiện đúng $\ge 95\%$ vị trí 2 cột, khối văn bản và hình vẽ trên Canvas | Đối chiếu trực quan Canvas với PDF gốc |
| **Bảo toàn công thức LaTeX** | 100% công thức toán học không bị dịch đè hoặc sai cú pháp | Kiểm tra MathJax / KaTeX rendering |
| **Bảo toàn hình ảnh & đồ thị** | 100% sơ đồ và hình vẽ được crop sắc nét và đặt đúng vị trí | Kiểm tra Asset Manager & Canvas Image Layer |
| **Độ chuẩn thuật ngữ CNTT & AI** | $\ge 98\%$ thuật ngữ AI/CNTT được dịch đúng ngữ cảnh | Kiểm tra đối chiếu từ điển chuyên sâu |
| **Trải nghiệm xuất PDF** | 1 click xuất ra tệp PDF tiếng Việt tương tự bố cục gốc | Xuất qua Canvas to PDF engine |

---

## 4. Đối tượng sử dụng mục tiêu (Target Users)

1. **Giai đoạn 1 (Cá nhân):**
   - Bản thân tôi (Nhà nghiên cứu / Kỹ sư CNTT & AI) cần đọc bài báo chuyên ngành nhanh chóng, chuẩn xác và có thể in/lưu trữ bản dịch PDF đẹp mắt.
2. **Giai đoạn 2 (Cộng đồng mã nguồn mở):**
   - Sinh viên, nghiên cứu sinh, giảng viên và kỹ sư AI/CNTT tại Việt Nam mong muốn một công cụ tự host, miễn phí, cài đặt 1-click Docker, sử dụng CPU mà không cần GPU đắt tiền (nhờ Indra ONNX).

---

## 5. Ranh giới giải pháp (Refined Scope v3.0)

### In-Scope:
- Tiếp nhận tệp **PDF** bài báo khoa học (tải lên trực tiếp hoặc qua liên kết arXiv).
- Chạy **Indra OCR** trên CPU để phân tích layout, nhận dạng text, reading order, bảng HTML và công thức LaTeX.
- Trích xuất ảnh sơ đồ/đồ thị từ PDF gốc dựa trên tọa độ Bounding Box của khối `Picture`/`Figure`.
- Đóng gói toàn văn bài báo và gọi **Google Gemini API trong 1 lần gọi duy nhất** để dịch sang tiếng Việt.
- Sử dụng **HTML Canvas** tại Frontend để tái hiện lại giao diện bài báo bản dịch tiếng Việt giống hệt tài liệu gốc.
- Hỗ trợ xem trực quan trên Web (phóng to, thu nhỏ, cuộn trang) và xuất tệp **PDF bản dịch hoàn chỉnh**.

### Out-of-Scope:
- Hệ thống tài khoản người dùng, đăng nhập OAuth, thanh toán SaaS.
- Huấn luyện lại model OCR (chỉ sử dụng model Indra pretrained có sẵn).
- Chỉnh sửa trực tiếp file PDF nhị phân dạng vector thô (thay vào đó vẽ layer tái tạo trên Canvas).
