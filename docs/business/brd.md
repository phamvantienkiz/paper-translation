# Business Requirement Document (BRD) — Paper Translation

**Tầng tài liệu**: Business Layer  
**Dự án**: Paper Translation (Personal & Open-Source Edition)  
**Phiên bản**: 2.0 (Scaled Down & Focused)  
**Ngày cập nhật**: 2026-10-05  
**Trạng thái**: Approved  

---

## 1. Bối cảnh & Vấn đề nghiệp vụ (Problem Statement)

Là một kỹ sư / nhà nghiên cứu trong lĩnh vực **Công nghệ thông tin (IT)** và **Trí tuệ nhân tạo (AI / Machine Learning / Deep Learning)**, nhu cầu đọc và hấp thụ các bài báo khoa học xuất sắc (từ arXiv, hội nghị NeurIPS, ICML, CVPR, ICLR, ACL...) là công việc diễn ra thường xuyên. Tuy nhiên, quá trình đọc và dịch các tài liệu này gặp phải các rào cản cụ thể:

1. **Sai lệch công thức và cấu trúc học thuật:** Các công cụ dịch phổ thông làm mất hoặc làm sai cú pháp toán học LaTeX (`$ ... $`, `$$ ... $$`), vỡ các bảng số liệu thực nghiệm (Benchmark Tables) và làm mất hình vẽ sơ đồ kiến trúc mô hình.
2. **Thuật ngữ CNTT & AI bị dịch thô cứng:** Các khái niệm chuyên sâu như *Attention Mechanism, Latent Space, Zero-Shot, Transformer, Residual Connection, Gradient Descent...* thường bị dịch sai lệch nghĩa nếu không có ngữ cảnh chuyên ngành.
3. **Cần một công cụ tinh gọn, cá nhân hóa trước mắt và hướng tới cộng đồng:** Thay vì một hệ thống SaaS thương mại phức tạp, mục tiêu trước mắt là một công cụ phục vụ nhu cầu cá nhân tự vận hành, sau đó đóng gói mã nguồn mở (Open-Source) chia sẻ cho cộng đồng nghiên cứu Việt Nam.

---

## 2. Tầm nhìn sản phẩm (Product Vision)

Xây dựng **Paper Translation** thành công cụ dịch bài báo khoa học tinh gọn, dễ sử dụng, tập trung chuyên sâu cho ngành **Công nghệ thông tin & Trí tuệ nhân tạo**:
- **Hỗ trợ đa định dạng đầu vào:** Ưu tiên hàng đầu cho tệp **PDF** và **DOCX** (hai định dạng phổ biến nhất của tài liệu học thuật).
- **Trải nghiệm đọc song ngữ trên Web:** Giao diện trực quan cho phép vừa đọc tiếng Việt vừa đối chiếu tức thì với văn bản gốc tiếng Anh.
- **Tải về tệp PDF bản dịch hoàn chỉnh:** Cho phép tải xuống tệp PDF tiếng Việt đã được dàn trang sạch đẹp, **giữ nguyên 100% công thức toán học LaTeX, hình ảnh minh họa và bảng biểu**.
- **Định hướng Open-Source:** Thiết kế kiến trúc đơn giản, dễ cài đặt cục bộ (Self-hosted / Docker), cho phép người dùng tự nạp API key (Gemini, OpenAI...) hoặc kết nối mô hình LLM cục bộ (Ollama).

---

## 3. Chỉ số thành công & KPIs (Success Metrics)

| Chỉ số | Mục tiêu kỳ vọng | Phương pháp đo lường |
|---|---|---|
| **Bảo toàn công thức LaTeX** | 100% công thức toán không bị dịch đè hoặc sai cú pháp | Kiểm tra MathJax/KaTeX rendering |
| **Bảo toàn cấu trúc hình & bảng** | Giữ nguyên vẹn bảng biểu thực nghiệm và hình vẽ minh họa | Đối chiếu cấu trúc tài liệu xuất ra |
| **Độ chuẩn thuật ngữ CNTT & AI** | $\ge 95\%$ thuật ngữ AI/CNTT được dịch đúng ngữ cảnh | Kiểm tra bộ từ điển chuyên ngành |
| **Định dạng hỗ trợ** | Tiếp nhận tốt 100% tệp PDF và DOCX hợp lệ | Automated ingestion test |
| **Trải nghiệm xuất file** | Tải về 1 tệp PDF bản dịch hoàn chỉnh với 1 click | Thao tác trên Web UI |

---

## 4. Đối tượng sử dụng mục tiêu (Target Users)

1. **Giai đoạn 1 (Cá nhân):**
   - Bản thân tôi (Nhà nghiên cứu / Kỹ sư CNTT & AI) cần công cụ dịch nhanh tài liệu hàng ngày phục vụ công việc và học tập.
2. **Giai đoạn 2 (Cộng đồng mã nguồn mở):**
   - Sinh viên, nghiên cứu sinh, giảng viên và kỹ sư AI/CNTT tại Việt Nam mong muốn một công cụ tự host, miễn phí, không bị giới hạn bởi các dịch vụ thương mại đắt đỏ.

---

## 5. Ranh giới giải pháp (Refined Scope)

### In-Scope (Thuộc phạm vi hệ thống):
- Tiếp nhận tệp tài liệu định dạng **PDF** và **DOCX** từ máy tính (kèm hỗ trợ link arXiv tiện lợi).
- Bóc tách văn bản, cô lập công thức toán học LaTeX, hình ảnh và bảng biểu.
- Dịch thuật tự động ngữ cảnh chuyên sâu CNTT & AI (sử dụng LLM API hoặc local LLM).
- Giao diện Web hiển thị bản dịch song ngữ (Dual-Pane) cho trải nghiệm đọc trực quan.
- Xuất và tải về trực tiếp **tệp PDF bản dịch tiếng Việt** giữ nguyên vẹn công thức toán, hình ảnh, bảng biểu.

### Out-of-Scope (Loại bỏ để tinh giản tối đa):
- Hệ thống quản lý tài khoản người dùng, phân quyền doanh nghiệp, đăng nhập mạng xã hội.
- Cổng thanh toán, gói thuê bao thương mại.
- Mạng xã hội bình luận học thuật hoặc chia sẻ bài báo công cộng.
- Hạ tầng vi dịch vụ (Microservices) hoặc Kubernetes phân tán phức tạp.
