import gc
from pathlib import Path

import fitz

from app.core.config import settings
from app.core.logging import logger
from app.services.parser.indra_ocr_service import ParsedPage


class PageAssetService:
    """
    Dịch vụ kết xuất ảnh chụp toàn trang gốc (Layer 0 cho HTML Canvas)
    và crop ảnh các khối hình vẽ (figure) theo Bounding Box chuẩn hóa.
    Độ phân giải: 200 DPI (sắc nét trên cả màn hình Retina).
    """

    TARGET_DPI = 200.0

    @classmethod
    def get_zoom_matrix(cls) -> fitz.Matrix:
        scale = cls.TARGET_DPI / 72.0
        return fitz.Matrix(scale, scale)

    def render_page_snapshots(
        self, session_id: str, pdf_path: Path, pages: list[ParsedPage]
    ) -> dict[int, str]:
        """
        Kết xuất ảnh chụp toàn bộ từng trang bài báo gốc (Layer 0) thành PNG 200 DPI.
        Trả về dictionary ánh xạ: {page_number: file_path_str}.
        """
        pdf_path = Path(pdf_path)
        session_pages_dir = settings.pages_dir / session_id
        session_pages_dir.mkdir(parents=True, exist_ok=True)

        page_paths: dict[int, str] = {}
        doc = fitz.open(str(pdf_path))
        matrix = self.get_zoom_matrix()

        try:
            for parsed_p in pages:
                p_idx = parsed_p.page_number - 1
                if p_idx < len(doc):
                    page = doc[p_idx]
                    pix = page.get_pixmap(matrix=matrix, alpha=False)
                    out_file = session_pages_dir / f"page_{parsed_p.page_number}.png"
                    pix.save(str(out_file))
                    del pix

                    rel_path = f"storage/pages/{session_id}/page_{parsed_p.page_number}.png"
                    page_paths[parsed_p.page_number] = str(out_file)
                    parsed_p.page_image_path = rel_path
                    logger.debug(f"[{session_id}] Đã kết xuất Layer 0 trang #{parsed_p.page_number}: {out_file}")
        finally:
            doc.close()
            del doc
            gc.collect()

        return page_paths

    def crop_figure_blocks(
        self, session_id: str, pdf_path: Path, pages: list[ParsedPage]
    ) -> None:
        """
        Crop ảnh độ nét cao riêng cho các khối có nhãn 'figure' theo tọa độ chuẩn hóa [0.0 .. 1.0].
        Lưu vào storage/figures/{session_id}/page_{n}_fig_{k}.png.
        """
        pdf_path = Path(pdf_path)
        session_figs_dir = settings.figures_dir / session_id
        session_figs_dir.mkdir(parents=True, exist_ok=True)

        doc = fitz.open(str(pdf_path))
        matrix = self.get_zoom_matrix()

        try:
            for parsed_p in pages:
                p_idx = parsed_p.page_number - 1
                if p_idx >= len(doc):
                    continue
                page = doc[p_idx]
                w = parsed_p.width_pt
                h = parsed_p.height_pt

                fig_count = 1
                for block in parsed_p.blocks:
                    if block.label == "figure":
                        x0, y0, x1, y1 = block.bbox_norm
                        # Quy đổi tọa độ chuẩn hóa [0..1] sang đơn vị point của PDF
                        clip_rect = fitz.Rect(x0 * w, y0 * h, x1 * w, y1 * h)
                        if clip_rect.width > 5 and clip_rect.height > 5:
                            pix = page.get_pixmap(matrix=matrix, clip=clip_rect, alpha=False)
                            fig_filename = f"page_{parsed_p.page_number}_fig_{fig_count}.png"
                            fig_file = session_figs_dir / fig_filename
                            pix.save(str(fig_file))
                            del pix

                            block.figure_image_path = f"storage/figures/{session_id}/{fig_filename}"
                            fig_count += 1
        finally:
            doc.close()
            del doc
            gc.collect()
