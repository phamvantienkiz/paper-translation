import gc
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

import fitz

from app.core.logging import logger


@dataclass
class ParsedBlock:
    reading_order: int
    page_number: int
    block_code: str
    label: str
    bbox_norm: tuple[float, float, float, float]  # (x0, y0, x1, y1) in [0.0, 1.0]
    text: str
    is_translatable: bool = True
    figure_image_path: str | None = None


@dataclass
class ParsedPage:
    page_number: int
    width_pt: float
    height_pt: float
    rotation: int = 0
    skew: float = 0.0
    page_image_path: str = ""
    blocks: list[ParsedBlock] = field(default_factory=list)


@dataclass
class ParsedDocument:
    title: str | None = None
    total_pages: int = 0
    pages: list[ParsedPage] = field(default_factory=list)
    blocks: list[ParsedBlock] = field(default_factory=list)


def normalize_bbox(
    box: Sequence[float], width: float, height: float
) -> tuple[float, float, float, float]:
    """
    Chuẩn hóa tọa độ Bounding Box về hệ tọa độ tương đối bất biến [0.0 .. 1.0].
    Đảm bảo 0.0 <= x0 <= x1 <= 1.0 và 0.0 <= y0 <= y1 <= 1.0.
    """
    if width <= 0 or height <= 0:
        return 0.0, 0.0, 1.0, 1.0

    x0 = max(0.0, min(1.0, float(box[0]) / width))
    y0 = max(0.0, min(1.0, float(box[1]) / height))
    x1 = max(0.0, min(1.0, float(box[2]) / width))
    y1 = max(0.0, min(1.0, float(box[3]) / height))

    if x0 > x1:
        x0, x1 = x1, x0
    if y0 > y1:
        y0, y1 = y1, y0

    return round(x0, 4), round(y0, 4), round(x1, 4), round(y1, 4)


class IndraOcrService:
    """
    Dịch vụ phân tích bố cục văn bản khoa học, nhận diện 2 cột, thứ tự đọc (reading order)
    và chuẩn hóa tọa độ hộp [0.0 .. 1.0].
    Sử dụng thư viện indra_ocr (ONNX CPU) kèm cơ chế dự phòng thông minh (PyMuPDF layout fallback)
    khi chạy trong môi trường kiểm thử hoặc khi chưa tải mô hình ngoại tuyến.
    """

    def __init__(self, threads: int = 4):
        self.threads = threads
        self._converter = None
        self._init_attempted = False

    def _get_converter(self):
        if not self._init_attempted:
            self._init_attempted = True
            try:
                import indra_ocr

                # Chỉ tải mô hình nếu biến môi trường hoặc thư mục đã được cấu hình hợp lệ
                self._converter = indra_ocr.load(
                    threads=self.threads, math=True, mode="auto"
                )
                logger.info("Khởi tạo thành công Indra OCR Converter với 4 threads.")
            except Exception as e:
                logger.warning(
                    f"Không thể khởi tạo mô hình Indra OCR ({e}). Sử dụng PyMuPDF layout fallback."
                )
                self._converter = None
        return self._converter

    def unload(self) -> None:
        """
        Thu hồi toàn bộ tài nguyên phần cứng sau khi hoàn thành OCR:
        - Tắt ThreadPoolExecutor worker threads để giải phóng 100% CPU.
        - Hủy tham chiếu tất cả ONNX Runtime InferenceSessions (det, rec, order, orient, mask, math) để giải phóng RAM.
        - Kích hoạt Garbage Collection để thu hồi bộ nhớ C++ / Python ngay lập tức.
        """
        if self._converter is not None:
            try:
                ocr = getattr(self._converter, "ocr", None)
                if ocr is not None:
                    pool = getattr(ocr, "pool", None)
                    if pool is not None:
                        try:
                            pool.shutdown(wait=False, cancel_futures=True)
                        except Exception:
                            pool.shutdown(wait=False)
                        ocr.pool = None

                    for attr in ("det", "rec", "mask", "order", "orient", "script", "math"):
                        if hasattr(ocr, attr):
                            setattr(ocr, attr, None)

                    if hasattr(ocr, "groups") and isinstance(ocr.groups, dict):
                        ocr.groups.clear()
                    if hasattr(ocr, "lms") and isinstance(ocr.lms, dict):
                        ocr.lms.clear()

                logger.info("Đã thu hồi thành công tài nguyên Indra OCR (ThreadPool + ONNX InferenceSessions).")
            except Exception as e:
                logger.warning(f"Lỗi khi thu hồi tài nguyên Indra OCR: {e}")
            finally:
                self._converter = None
                self._init_attempted = False
                gc.collect()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.unload()

    def parse_pdf(self, pdf_path: Path) -> ParsedDocument:
        """
        Phân tích tệp PDF bài báo, trích xuất cấu trúc từng trang và khối bố cục.
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.is_file():
            raise FileNotFoundError(f"Tệp PDF không tồn tại: {pdf_path}")

        converter = self._get_converter()
        if converter:
            try:
                return self._parse_with_indra(pdf_path, converter)
            except Exception as exc:
                logger.warning(
                    f"Xảy ra lỗi khi chạy Indra OCR ({exc}). Tự động fallback sang PyMuPDF layout parser."
                )

        return self._parse_with_pymupdf(pdf_path)

    def _map_indra_label(self, label: str) -> str:
        cleaned = label.lower().strip()
        if "section" in cleaned or "heading" in cleaned:
            return "section header"
        elif "title" in cleaned:
            return "title"
        elif "header" in cleaned:
            return "page header"
        elif "footer" in cleaned:
            return "page footer"
        elif "caption" in cleaned:
            return "caption"
        elif "footnote" in cleaned:
            return "footnote"
        elif "table" in cleaned:
            return "table"
        elif "picture" in cleaned or "figure" in cleaned:
            return "figure"
        elif "list" in cleaned:
            return "list"
        return "text"

    def _parse_with_indra(self, pdf_path: Path, converter) -> ParsedDocument:
        doc_fitz = fitz.open(str(pdf_path))
        total_pages = len(doc_fitz)

        parsed_pages: list[ParsedPage] = []
        all_blocks: list[ParsedBlock] = []
        global_block_idx = 1
        extracted_title: str | None = None

        try:
            for page_idx, indra_page in converter.convert(str(pdf_path)):
                page_num = page_idx + 1
                fitz_page = doc_fitz[page_idx] if page_idx < total_pages else None
                width_pt = fitz_page.rect.width if fitz_page else 595.27
                height_pt = fitz_page.rect.height if fitz_page else 841.89

                page_blocks: list[ParsedBlock] = []

                # indra_page.blocks: list of {"label": str, "bbox": [x0, y0, x1, y1], "text": str}
                raw_blocks = getattr(indra_page, "blocks", [])
                
                # Nếu không có blocks từ layout model, fallback sang line boxes
                if not raw_blocks and hasattr(indra_page, "lines"):
                    raw_blocks = [
                        {"label": "Text", "bbox": ln.box, "text": ln.text}
                        for ln in indra_page.lines
                        if ln.text.strip()
                    ]

                for raw_b in raw_blocks:
                    label = self._map_indra_label(raw_b.get("label", "text"))
                    bbox_raw = raw_b.get("bbox", [0, 0, width_pt, height_pt])
                    text = raw_b.get("text", "").strip()

                    # Ước lượng width/height gốc của OCR để chuẩn hóa
                    # indra box tọa độ theo pixel render (mặc định 200 DPI hoặc fitz_page)
                    # Nếu max(bbox_raw) > width_pt * 1.5, đó là DPI pixel
                    max_x = max(bbox_raw[0], bbox_raw[2])
                    max_y = max(bbox_raw[1], bbox_raw[3])
                    ref_w = max(width_pt, max_x)
                    ref_h = max(height_pt, max_y)

                    bbox_norm = normalize_bbox(bbox_raw, ref_w, ref_h)
                    block_code = f"BLK_{global_block_idx:04d}"

                    is_translatable = label not in ("page header", "page footer", "figure")
                    if not text and label != "figure":
                        continue

                    if not extracted_title and (label == "title" or (page_num == 1 and global_block_idx <= 2)):
                        if len(text) > 5 and "\n" not in text:
                            extracted_title = text

                    pb = ParsedBlock(
                        reading_order=global_block_idx - 1,
                        page_number=page_num,
                        block_code=block_code,
                        label=label,
                        bbox_norm=bbox_norm,
                        text=text,
                        is_translatable=is_translatable,
                    )
                    page_blocks.append(pb)
                    all_blocks.append(pb)
                    global_block_idx += 1

                parsed_pages.append(
                    ParsedPage(
                        page_number=page_num,
                        width_pt=width_pt,
                        height_pt=height_pt,
                        rotation=getattr(indra_page, "rotation", 0),
                        skew=getattr(indra_page, "skew", 0.0),
                        blocks=page_blocks,
                    )
                )
        finally:
            doc_fitz.close()

        return ParsedDocument(
            title=extracted_title,
            total_pages=len(parsed_pages),
            pages=parsed_pages,
            blocks=all_blocks,
        )

    def _parse_with_pymupdf(self, pdf_path: Path) -> ParsedDocument:
        """
        Trình bóc tách dự phòng thông minh dựa trên PyMuPDF:
        Nhận diện bố cục 2 cột bằng sắp xếp tọa độ X-Y Cut và phân loại nhãn.
        """
        doc = fitz.open(str(pdf_path))
        parsed_pages: list[ParsedPage] = []
        all_blocks: list[ParsedBlock] = []
        global_block_idx = 1
        extracted_title: str | None = None

        try:
            for page_idx, page in enumerate(doc):
                page_num = page_idx + 1
                w = page.rect.width
                h = page.rect.height

                # Lấy text blocks: (x0, y0, x1, y1, text, block_no, block_type)
                raw_blocks = page.get_text("blocks")

                # Sắp xếp theo thứ tự đọc 2 cột (reading order):
                # Phân loại khối theo nửa trái / nửa phải nếu trang có 2 cột
                mid_x = w / 2.0
                left_col = []
                right_col = []
                full_width = []

                for b in raw_blocks:
                    x0, y0, x1, y1, text, bno, btype = b
                    bw = x1 - x0
                    # Nếu khối trải rộng qua 65% chiều rộng trang -> full-width header/title
                    if bw > w * 0.65:
                        full_width.append((y0, b))
                    elif x1 <= mid_x + 30:
                        left_col.append((y0, b))
                    else:
                        right_col.append((y0, b))

                full_width.sort(key=lambda item: item[0])
                left_col.sort(key=lambda item: item[0])
                right_col.sort(key=lambda item: item[0])

                sorted_raw = [b for _, b in full_width if _ < h * 0.3]
                sorted_raw.extend([b for _, b in left_col])
                sorted_raw.extend([b for _, b in right_col])
                sorted_raw.extend([b for _, b in full_width if _ >= h * 0.3])

                page_blocks: list[ParsedBlock] = []

                for b in sorted_raw:
                    x0, y0, x1, y1, text, bno, btype = b
                    clean_text = text.strip()
                    if not clean_text and btype == 0:
                        continue

                    # Phân loại nhãn ngữ nghĩa
                    label = "text"
                    if btype == 1:
                        label = "figure"
                    elif y0 < h * 0.06:
                        label = "page header"
                    elif y1 > h * 0.94:
                        label = "page footer"
                    elif page_num == 1 and global_block_idx == 1 and len(clean_text) < 150:
                        label = "title"
                        if not extracted_title:
                            extracted_title = clean_text
                    elif re.match(r"^(?:[0-9IVX]+\.?|[A-Z]\.)\s+[A-Z]", clean_text) or (
                        len(clean_text) < 80 and clean_text.isupper()
                    ):
                        label = "section header"
                    elif clean_text.lower().startswith("table ") or "\t" in clean_text:
                        label = "table"
                    elif clean_text.lower().startswith("figure ") or clean_text.lower().startswith("fig."):
                        label = "caption"

                    bbox_norm = normalize_bbox((x0, y0, x1, y1), w, h)
                    block_code = f"BLK_{global_block_idx:04d}"
                    is_translatable = label not in ("page header", "page footer", "figure")

                    pb = ParsedBlock(
                        reading_order=global_block_idx - 1,
                        page_number=page_num,
                        block_code=block_code,
                        label=label,
                        bbox_norm=bbox_norm,
                        text=clean_text,
                        is_translatable=is_translatable,
                    )
                    page_blocks.append(pb)
                    all_blocks.append(pb)
                    global_block_idx += 1

                parsed_pages.append(
                    ParsedPage(
                        page_number=page_num,
                        width_pt=w,
                        height_pt=h,
                        blocks=page_blocks,
                    )
                )
        finally:
            doc.close()

        return ParsedDocument(
            title=extracted_title or "Untitled Scientific Paper",
            total_pages=len(parsed_pages),
            pages=parsed_pages,
            blocks=all_blocks,
        )


