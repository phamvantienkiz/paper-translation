from pathlib import Path
from typing import List, Optional
import fitz  # PyMuPDF

from app.core.logging import logger
from app.services.parser.base_parser import BaseDocumentParser, ParsedBlock, ParsedDocument


class PdfParser(BaseDocumentParser):
    def parse(self, file_path: Path, session_id: str) -> ParsedDocument:
        logger.info(f"[{session_id}] Bắt đầu bóc tách tệp PDF: {file_path}")
        doc = fitz.open(str(file_path))

        total_pages = len(doc)
        if total_pages == 0:
            doc.close()
            raise ValueError("Tệp PDF rỗng không có trang nào.")

        total_chars = 0
        blocks: List[ParsedBlock] = []
        doc_title: Optional[str] = doc.metadata.get("title") or None
        order_index = 0

        for page_num in range(total_pages):
            page = doc[page_num]
            # page.get_text("blocks") returns tuples: (x0, y0, x1, y1, "text", block_no, block_type)
            # block_type == 0 is text, block_type == 1 is image
            page_blocks = page.get_text("blocks")

            for b in page_blocks:
                block_type = b[6]
                if block_type == 0:
                    text = b[4].strip()
                    if not text:
                        continue
                    
                    total_chars += len(text)

                    # Simple heuristic: If first page and short and not yet set title
                    if not doc_title and page_num == 0 and len(text) < 150 and "\n" not in text:
                        doc_title = text

                    # Detect if block is a heading or paragraph
                    is_heading = len(text) < 80 and not text.endswith(".") and ("\n" not in text or len(text.splitlines()) <= 2)
                    segment_type = "HEADING" if is_heading else "PARAGRAPH"

                    blocks.append(
                        ParsedBlock(
                            order_index=order_index,
                            segment_type=segment_type,
                            content=text,
                        )
                    )
                    order_index += 1

        doc.close()

        # Check for scanned PDF with no text layer
        if total_chars < 50:
            raise ValueError(
                "Tài liệu PDF là tệp scan hình ảnh không có lớp văn bản điện tử (text layer). "
                "Hệ thống hiện chưa hỗ trợ OCR scan."
            )

        logger.info(
            f"[{session_id}] Bóc tách PDF hoàn tất: {total_pages} trang, "
            f"{len(blocks)} phân đoạn, {total_chars} ký tự."
        )

        return ParsedDocument(
            title=doc_title,
            blocks=blocks,
        )
