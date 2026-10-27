---
name: paper-translation
description: Dịch bài báo khoa học trực tiếp bằng Agent và Indra OCR ngoại tuyến, tự động cô lập công thức toán học LaTeX, trích xuất hình ảnh, kiểm tra chéo bằng VLM trực tiếp trên PDF gốc và kết xuất tài liệu chuẩn A4 dạng HTML Canvas kèm nút Tải PDF.
---

# Paper Translation Skill

Skill chuyên dụng cho phép AI Agent trực tiếp đảm nhận vai trò dịch thuật chuyên sâu các bài báo khoa học kỹ thuật (đặc biệt là lĩnh vực Công nghệ Thông tin, Trí tuệ Nhân tạo - IT & AI) từ tệp PDF gốc sang tiếng Việt chất lượng cao mà không cần gọi API LLM ngoài hay dựng cụm server LLM cục bộ phức tạp.

Skill tích hợp **quy trình kiểm tra chéo đa phương thức (Multimodal VLM Verification Loop)**, cho phép Agent đọc trực tiếp file PDF gốc để rà soát, triệt tiêu toàn bộ rác OCR, sửa lỗi lệch cột bảng biểu và chuẩn hóa công thức toán học trước khi xuất bản.

---

## 1. Môi trường & Điều kiện tiên quyết (Environment Isolation)

Tuân thủ nghiêm ngặt quy tắc cô lập môi trường trong `AGENTS.md`:
1. Kiểm tra môi trường ảo `.venv` cục bộ trong workspace:
   - Nếu thư mục `.venv` (hoặc `backend/.venv`) đã tồn tại, trực tiếp sử dụng.
   - Nếu chưa có, tạo mới môi trường ảo cục bộ:
     ```powershell
     uv venv .venv
     ```
2. Cài đặt các gói phụ thuộc tối thiểu cần thiết từ `requirements.txt`:
   ```powershell
   uv pip install -r paper-translation/requirements.txt
   ```
*(Lưu ý: Nếu dùng môi trường `backend/.venv`, luôn thực thi lệnh Python với cờ `--python backend/.venv/Scripts/python.exe`)*

---

## 2. Quy trình dịch thuật 4 bước (4-Step Pipeline)

Khi người dùng yêu cầu dịch một bài báo và chỉ định đường dẫn tệp PDF (`<duong_dan_pdf>`), Agent **BẮT BUỘC** thực hiện tuần tự đúng 4 bước:

```
[PDF Gốc]
    │
    ▼ (Bước 1: Chạy Script OCR & Batching)
[output/<tên-paper>/]
    ├── figures/ (hình vẽ, biểu đồ đã crop 200 DPI)
    ├── batches/ (batch_01.txt, batch_02.txt, ... ≤ 2200 từ/batch)
    └── metadata.json (công thức toán đã cô lập <<<MATH_TOKEN_XXXX>>>)
    │
    ▼ (Bước 2: Agent trực tiếp dịch từng batch)
[batches/translated_batch_01.md, translated_batch_02.md, ...]
    │
    ▼ (Bước 3: Agent đọc PDF gốc qua VLM & Chạy Script Verify)
[Kiểm tra chéo VLM: Sửa lệch cột bảng biểu, xóa rác OCR sơ đồ, chuẩn hóa KaTeX, thêm References]
    │
    ▼ (Bước 4: Chạy Script Assembly)
[translated_paper.html] (Tài liệu chuẩn A4, render KaTeX sắc nét, 1 nút Tải PDF)
```

---

### BƯỚC 1: Chạy OCR, Cô lập công thức & Phân lô thích ứng

Thực thi script phân tích bằng lệnh:
```powershell
uv run python paper-translation/scripts/ocr_and_batch.py --pdf "<duong_dan_pdf>"
```

**Kết quả sinh ra tại thư mục:** `<thu_muc_chua_pdf>/output/<ten_bai_bao>/`
- `figures/`: Chứa tất cả hình ảnh, sơ đồ khoa học (Academic Figures) được crop tự động độ phân giải cao 200 DPI (`figure_01.png`, `figure_02.png`,...).
- `batches/batch_01.txt`, `batch_02.txt`,...: Mỗi batch chứa tối đa 2000 - 2200 từ tiếng Anh để đảm bảo Agent giữ trọn vẹn context, kèm sẵn các thẻ ảnh Markdown `![Hình X](figures/figure_XX.png)`.
- `metadata.json`: Chứa tiêu đề, danh sách hình ảnh, và bảng tra cứu công thức toán đã cô lập dưới dạng mã `<<<MATH_TOKEN_XXXX>>>`.

---

### BƯỚC 2: Agent trực tiếp dịch tuần tự từng batch

Agent đọc file `metadata.json` để biết tổng số batch, sau đó thực hiện quy trình lặp:
1. Đọc file `batches/batch_XX.txt`.
2. Trực tiếp suy luận và dịch toàn bộ nội dung sang tiếng Việt theo chuẩn văn phong học thuật.
3. Ghi kết quả vào file `batches/translated_batch_XX.md`.
4. **BẮT BUỘC hoàn thành và ghi xong batch hiện tại rồi mới tiếp tục đọc và dịch batch tiếp theo.**

#### Nguyên tắc dịch thuật học thuật bắt buộc:
1. **BẢO TOÀN NGUYÊN VẸN CÁC TOKEN TOÁN HỌC:**
   - Mọi chuỗi có dạng `<<<MATH_TOKEN_XXXX>>>` (ví dụ `<<<MATH_TOKEN_0001>>>`) **PHẢI giữ nguyên 100%**, không được dịch, không xóa dấu ngoặc, không chèn thêm khoảng trắng.
2. **BẢO TOÀN MÃ KHỐI VÀ HÌNH ẢNH:**
   - Giữ nguyên các đường dẫn hình ảnh dạng `![Chú thích](figures/figure_XX.png)` (hoặc `![Hình X: Chú thích](figures/figure_XX.png)`).
   - Nếu viết caption dạng `Hình X.` / `Figure X.`, trình biên dịch sẽ tự động bắt cặp và hiển thị sơ đồ tương ứng `figures/figure_XX.png`.
   - Giữ nguyên cấu trúc bảng biểu Markdown `| ... |`.
3. **CHUẨN HÓA THUẬT NGỮ CHUYÊN NGÀNH (IT & AI):**
   - Áp dụng chuẩn thuật ngữ học thuật:
     - *attention mechanism* -> cơ chế chú ý (attention mechanism)
     - *transformer* -> Transformer
     - *latent space* -> không gian tiềm ẩn (latent space)
     - *fine-tuning* -> tinh chỉnh (fine-tuning)
     - *backpropagation* -> lan truyền ngược (backpropagation)
     - *gradient descent* -> hạ độ dốc (gradient descent)
     - *ablation study* -> nghiên cứu loại trừ (ablation study)
     - *ground truth* -> dữ liệu chuẩn thực tế (ground truth)
     - *embedding* -> vector nhúng (embedding)
     - *state-of-the-art* -> hiện đại nhất (SOTA)
     - *benchmark* -> bộ tiêu chuẩn đánh giá (benchmark)

---

### BƯỚC 3: Kiểm tra chéo bằng VLM trực tiếp trên PDF gốc (Verification Loop)

Sau khi hoàn tất dịch các batch, Agent **BẮT BUỘC** kích hoạt khả năng đọc đa phương thức (VLM) của chính mình để đọc lại file PDF paper gốc và rà soát các vấn đề sau:

#### 1. Tiêu đề bài báo & Thông tin tác giả:
- Kiểm tra `metadata.json`: Nếu OCR nhận diện nhầm danh sách tác giả thành tiêu đề (dấu hiệu: chứa số mũ `1†`, nhiều dấu phẩy), Agent cập nhật lại tiêu đề chính xác của bài báo và tiêu đề tiếng Việt.

#### 2. Triệt tiêu rác OCR từ sơ đồ khối:
- Khi OCR quét các trang có sơ đồ khối kiến trúc (như Hình 2), các chữ trong các hộp hình chữ nhật (`LOL Stage`, `Deblur Stage`, `Upsampling`, `SG`, `SCA`, `1x1 conv`, `LNorm`, `ModulePhase`,...) thường bị rớt vào luồng văn bản chính.
- Agent đối chiếu với hình vẽ gốc và **xóa bỏ hoàn toàn các chuỗi rác này** khỏi văn bản dịch.

#### 3. Kiểm tra từng ô trong bảng biểu định lượng:
- **Phát hiện lỗi lệch cột:** Indra OCR rất hay bỏ qua các ô có dấu gạch ngang (`-`), ô trống, hoặc ký hiệu ghi chú, làm toàn bộ các cột phía sau bị dồn sang trái (ví dụ: mất cột khiến chỉ số SOTA của mô hình đề xuất bị gán cho mô hình khác).
- Agent đọc bảng biểu gốc trên PDF và rà soát từng ô số liệu (PSNR, SSIM, LPIPS, Params, MACs).
- Định dạng in đậm (`**bold**`) cho kết quả tốt nhất và gạch chân (`<u>underline</u>`) cho kết quả tốt nhì theo đúng chuẩn bài báo gốc.

#### 4. Bảo toàn số thứ tự và dạng biểu diễn công thức toán:
- Đảm bảo các số đánh dấu phương trình (ví dụ `(1)`, `(2)`, ..., `(9)`) gắn liền với công thức, không bị OCR tách rời và trôi dạt thành số thứ tự các mục bên dưới.
- Khắc phục các công thức LaTeX bị lệch ngoặc nhọn hoặc thiếu dấu phân cách.

#### 5. Bổ sung Danh mục Tài liệu tham khảo (References):
- Kiểm tra phần cuối bài báo: Nếu quá trình phân lô batch bỏ sót danh sách trích dẫn `[1]...[N]`, Agent đối chiếu trang cuối của PDF gốc và bổ sung đầy đủ danh mục References.

#### 6. Chạy các công cụ kiểm tra tự động tích hợp:
Agent thực thi script kiểm tra chéo tự động:
```powershell
uv run python paper-translation/scripts/verify_translation.py --output-dir "<thu_muc_output>"
```
Nếu cần tra cứu nhanh danh sách và cú pháp các token toán học:
```powershell
uv run python paper-translation/scripts/inspect_tokens.py --metadata "<thu_muc_output>"
```

---

### BƯỚC 4: Ghép nối & Kết xuất HTML Canvas Khổ A4

Sau khi bản dịch đã được xác minh sạch sẽ và kiểm tra chéo hoàn tất, thực thi script kết xuất:
```powershell
uv run python paper-translation/scripts/compile_html_canvas.py --output-dir "<thu_muc_output>"
```

**Đầu ra cuối cùng:**
- Tệp `<thu_muc_output>/translated_paper.html`.
- Định dạng: Khung canvas A4 học thuật (210mm x 297mm), render công thức KaTeX sắc nét, bảng biểu booktabs và hình ảnh base64 tích hợp trọn gói.
- Trên giao diện có một nút duy nhất: **"Tải PDF (In A4)"** kích hoạt `window.print()` chuẩn in ấn không vỡ trang.

Agent thông báo hoàn tất và gửi đường dẫn tệp HTML cho người dùng.
