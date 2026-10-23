# KẾ HOẠCH TRIỂN KHAI: TỐI ƯU GOM LÔ LOCAL LLM, TÁI TẠO CANVAS WORD TRÊN TRANG TRẮNG & GIAO DIỆN CUỘN LIÊN TỤC

> **Phiên bản**: 1.0  
> **Trạng thái**: Chờ duyệt (Pending Review)  
> **Mục tiêu**: Khắc phục triệt để 3 vấn đề cốt lõi khi chạy thực tế bài báo khoa học:
> 1. Giảm số batch dịch từ 27 xuống **dưới 5 batch** (tối ưu 2–4 batch), loại bỏ References & Watermark, thiết kế prompt chuyên biệt với skill `prompt-engineer`.
> 2. Tái cấu trúc Canvas theo phong cách **Trang Word Trống** (không đè lên ảnh gốc gây lem chữ/chồng chéo), nhúng trực tiếp ảnh gốc đã crop, chuẩn hóa Typography & KaTeX.
> 3. Nâng cấp trải nghiệm đọc sang **Continuous Vertical Scroll** (cuộn mượt như trang landing page, cố định header & toolbar).

---

## 1. Mục tiêu & Bối cảnh Thực tế

Khi chạy thử nghiệm với bài báo thực tế (ví dụ 11 trang, 2 cột):
- **Vấn đề 1 (Thời gian dịch quá lâu do chia 27 batch)**: Các khối văn bản thực tế trong bài báo chỉ khoảng 4,000 – 6,000 token translatable (sau khi trừ bảng, hình ảnh, và 3 trang References cuối). Hệ thống cũ chia nhỏ thành 27 batch (mỗi batch 8 khối), mỗi batch gọi Qwen3 trên CPU mất 1.5–2 phút dẫn tới tổng thời gian dịch lên tới 40–45 phút. References và watermark rác (CVPR, IEEE, arXiv...) bị đưa vào dịch vô ích.
- **Vấn đề 2 (Chữ chồng lấn trên Canvas & Lỗi Font/LaTeX)**: Cơ chế phủ hộp trắng lên ảnh nền gốc (`page_image_url`) khiến chữ tiếng Anh bị lộ hoặc chữ tiếng Việt tràn viền, đè lên nhau không đọc được. Kích thước font bị lệch (tiêu đề nhỏ hơn body text, không in đậm). Công thức toán học `$ ... $` không được KaTeX render hoặc render cỡ chữ quá to. Text trong hình vẽ bị dịch đè lên hình thay vì lấy ảnh gốc chèn vào.
- **Vấn đề 3 (Điều hướng trang gián đoạn)**: Nút bấm chuyển từng trang gây ngắt quãng trải nghiệm đọc báo cáo khoa học.

---

## 2. Phân tích Kỹ thuật & Giải pháp Chi tiết

### 2.1. Vấn đề 1: Tối ưu Phân Lô Thích Ứng & Prompt Engineering (Backend)

#### A. Thuật toán Lọc Khối Không Dịch (Smart Pre-filtering)
1. **Phát hiện & Loại bỏ Watermark / Header / Footer Rác**:
   - Khối có nhãn `page header`, `page footer`.
   - Khối chứa chuỗi đặc trưng nhận diện qua Regex: `arXiv:\d{4}\.\d+`, `IEEE TRANSACTIONS`, `CVPR`, `ICCV`, `Conference`, `Copyright ©`, số trang đơn lẻ (`^\d+$`).
   - Đánh dấu `is_translatable = False`, không đưa vào danh sách gửi LLM.
2. **Nhận diện Vùng References / Bibliography**:
   - Phát hiện khối có label `section header` hoặc text chứa: `References`, `REFERENCES`, `Bibliography`, `Tài liệu tham khảo`.
   - Toàn bộ các khối đọc sau tiêu đề References sẽ tự động được gán `is_translatable = False`, tự động sao chép `translated_text = original_text` để giữ nguyên trên Canvas mà không tốn 1 token dịch nào!
3. **Bỏ qua Text nằm bên trong Bounding Box của Hình ảnh (Figures)**:
   - Các khối nằm lọt bên trong hoặc trùng tọa độ với khối `figure` sẽ không dịch, tránh việc render chữ dịch đè lên biểu đồ.

#### B. Thuật toán Gom Lô Hướng Ngưỡng $\le 5$ Batch
- Mô hình Qwen3-1.7B chạy với ngữ cảnh `n_ctx = 8192` (~2.8GB RAM).
- Ngân sách Token cho mỗi batch:
  - System Prompt + Rules: ~700 tokens.
  - Dự trữ Completion Token tối đa: ~2,500 tokens.
  - Ngân sách Text đầu vào (Input Budget): ~4,000 tokens / batch.
- **Logic Tính Số Batch**:
  - Đếm tổng số token của các khối cần dịch: $T = \sum \text{estimate\_tokens}(block)$.
  - Nếu $T \le 3,500$: Gom toàn bộ bài báo vào **1 batch duy nhất**!
  - Nếu $3,500 < T \le 7,000$: Chia đều thành **2 batch** (~3,500 tokens/batch).
  - Nếu $7,000 < T \le 12,000$: Chia đều thành **3–4 batch**.
  - Trần tối đa: Không vượt quá **5 batch** (mỗi batch chứa tối đa 25–40 khối tùy độ dài).
  - Với 2–4 batch, tổng thời gian dịch trên CPU Qwen3 giảm từ 45 phút xuống chỉ còn **3 – 6 phút**!

#### C. Thiết kế Prompt Chuyên Biệt (Skill: `prompt-engineer`)
- **System Prompt**: Định danh chuyên gia dịch thuật bài báo khoa học chuẩn quốc tế, quy tắc bảo tồn block code `[[BLK_XXXX]]`, công thức LaTeX `$..$`, `$$..$$`, bảng HTML, và trả về định dạng Markdown tinh gọn không thêm lời dẫn.
- **User Prompt**: Gom các khối theo thứ tự đọc tự nhiên với phân cách rõ ràng, kèm chỉ thị dịch mượt ngữ cảnh học thuật Việt Nam.

---

### 2.2. Vấn đề 2: Tái Tạo Canvas Như Trang Word Trắng (Frontend Canvas Redesign)

#### A. Kiến trúc Trang Word Trắng (Clean White Document Canvas)
- **Loại bỏ việc vẽ ảnh scan gốc làm nền** ở chế độ Bản Dịch (`TRANSLATED` mode).
- Tạo mỗi trang như một **Tờ Giấy A4 Chuẩn** (trắng tinh `#FFFFFF`, đổ bóng nhẹ `shadow-paper`, viền `border border-slate-200`).
- Chế độ So sánh `SIDE_BY_SIDE`:
  - Bên trái: Ảnh chụp bài gốc (Original Snapshot) để đối chiếu nguyên bản.
  - Bên phải: Trang Word Trắng chứa bản dịch tái tạo sạch sẽ.

#### B. Xử lý Hình ảnh (Figures & Diagrams)
- Khi khối có nhãn `figure` hoặc có `figure_image_url`:
  - Render thẻ `<img>` hiển thị trực tiếp ảnh cắt sắc nét từ PDF gốc (200 DPI).
  - Không render bất kỳ text OCR nào bên trong vùng ảnh.
  - Caption của ảnh (nhãn `caption`) đặt ngay bên dưới với font chữ nghiêng, căn giữa hoặc căn đều.

#### C. Hệ thống Typography Chuẩn Văn Bản Khoa Học
- `title`: Font Serif (`font-serif`), cỡ `text-xl` hoặc `text-2xl`, in đậm `font-bold`, căn giữa, màu `text-slate-900`.
- `section header`: Font Sans/Serif, `font-bold` hoặc `font-semibold`, cỡ `text-base` hoặc `text-lg`, có khoảng cách lề trên (`mt-4 mb-2`).
- `paragraph` / `text`: Font Serif học thuật, cỡ chữ đồng đều 10.5–11pt, `leading-relaxed` (1.45–1.5), `text-slate-800`.
- Bỏ cơ chế auto-scaling thu nhỏ chữ quá mức; thay bằng bố cục dòng chảy tự nhiên theo tọa độ cột hoặc tỷ lệ trang chuẩn.

#### D. Nâng cấp Bộ Render Toán Học KaTeX (`MathRenderer.tsx`)
- Nâng cấp Regex để nhận diện đồng thời:
  1. Display Math: `$$...$$` hoặc `\[...\]` -> render block căn giữa.
  2. Inline Math: `$...$` hoặc `\(...\)` -> render inline với cỡ chữ kế thừa trực tiếp từ văn bản bao quanh.
  3. Legacy Token: `<<<MATH_TOKEN_\d+>>>`.
- Khắc phục triệt để lỗi hiện nguyên text LaTeX hoặc công thức quá khổ.

---

### 2.3. Vấn đề 3: Giao diện Cuộn Dọc Liên Tục (Continuous Vertical Scroll)

#### A. Cố định Khung Điều Khiển (Fixed Sticky Chrome)
- Thanh điều khiển (View Mode, Zoom, Nút Tải PDF, Badge Engine) được cố định ở đỉnh màn hình (`sticky top-0 z-30`).
- Container đọc tài liệu chiếm toàn bộ chiều cao còn lại (`flex-1 overflow-y-auto`).

#### B. Cuộn Mượt Từng Trang (Landing Page Document View)
- Thay vì `currentPageIndex` hiển thị 1 trang duy nhất, `CanvasPaperViewer` kết xuất toàn bộ các trang tuần tự theo trục dọc:
  ```tsx
  <div className="flex flex-col items-center gap-8 py-8 w-full">
    {canvasData.pages.map((page, index) => (
      <PaperPageSheet key={page.page_number} page={page} ... />
    ))}
  </div>
  ```
- Thêm **Page Indicator Badge** nổi ở góc dưới màn hình hoặc trên thanh công cụ (ví dụ: `Trang 3 / 11`) tự động cập nhật theo vị trí cuộn của người dùng (sử dụng `IntersectionObserver`).

---

## 3. Các File Cần Thay Đổi

### Backend (`backend/`)
1. **`backend/app/services/parser/indra_ocr_service.py`**:
   - Bổ sung logic tiền lọc: Nhận diện watermark / running headers / footers bằng regex và đánh dấu `is_translatable = False`.
   - Nhận diện vùng References / Bibliography để gán `is_translatable = False` và giữ nguyên text gốc.
   - Bỏ qua text lọt bên trong khối `figure`.
2. **`backend/app/services/translation/adaptive_batcher.py`**:
   - Viết lại logic `create_batches`: Tính tổng token $T$, tính toán số batch mục tiêu $\le 5$ (ưu tiên 2–4 batch), gom 20–40 khối/batch dựa trên ngân sách 3,500 tokens.
   - Cập nhật `build_prompt_messages` theo thiết kế prompt tối ưu của skill `prompt-engineer`.
3. **`backend/app/services/translation/translation_service.py`**:
   - Bỏ qua dịch các khối `is_translatable = False` hoặc thuộc phần References (gán thẳng `translated_text = original_text`).
   - Cập nhật thông báo tiến độ SSE chuẩn xác theo số batch mới (ví dụ: `Lô 1/3`, `Lô 2/3`).

### Frontend (`frontend/`)
1. **`frontend/src/components/MathRenderer.tsx`**:
   - Hỗ trợ toàn diện inline math `$ ... $` và display math `$$ ... $$` bằng KaTeX với font-size tự động kế thừa.
2. **`frontend/src/components/CanvasPaperViewer.tsx`**:
   - Tái cấu trúc thành **Continuous Vertical Scroll**: render toàn bộ danh sách trang theo chiều dọc.
   - Tái tạo bản dịch trên **Trang Trắng Sạch** (Word-like canvas) thay vì vẽ đè lên ảnh gốc.
   - Nhúng trực tiếp ảnh gốc của khối `figure` qua `figure_image_url`, loại bỏ chữ OCR rác trong ảnh.
   - Phân cấp Typography rõ ràng: Title (lớn, bold), Section Header (vừa, bold), Body (chuẩn serif).
   - Thêm floating page indicator hiển thị số trang hiện tại khi cuộn.
3. **`frontend/src/App.tsx`**:
   - Đảm bảo layout cố định header/toolbar và cuộn mượt vùng đọc canvas.

---

## 4. Kế Hoạch Kiểm Thử & Xác Minh (Verification Plan)

### Kiểm thử Tự động (Automated Tests)
- Chạy unit tests cho `AdaptiveBatcher` mới:
  - Kiểm tra số batch sinh ra cho bài báo 150 khối luôn $\le 5$ batch.
  - Kiểm tra logic lọc References và watermark.
- Chạy toàn bộ backend test suite:
  ```bash
  cd backend
  uv run pytest tests/ -v
  uv run ruff check .
  ```
- Kiểm thử build frontend:
  ```bash
  cd frontend
  npm run build
  ```

### Kiểm thử Thực tế (Manual Verification)
1. Nạp bài báo thực tế (11 trang) và theo dõi:
   - Số batch hiển thị trên thanh tiến độ: 2–4 batch (không còn 27 batch).
   - Thời gian dịch giảm mạnh từ ~45 phút xuống dưới 5 phút.
   - Phần References ở 3 trang cuối không bị dịch, giữ nguyên trích dẫn.
2. Kiểm tra giao diện đọc:
   - Cuộn chuột từ trang 1 đến trang 11 mượt mà như một trang landing page.
   - Các trang hiển thị trên nền trắng phẳng, không có chữ tiếng Anh bị lộ hay chồng lấn.
   - Hình ảnh hiển thị nguyên bản từ file gốc.
   - Tiêu đề in đậm, cỡ lớn; công thức toán học hiển thị chuẩn xác ký hiệu KaTeX.
