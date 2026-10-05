from pathlib import Path
from typing import List, Optional
import docx
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.core.config import settings
from app.core.logging import logger
from app.services.parser.base_parser import BaseDocumentParser, ParsedBlock, ParsedDocument


class DocxParser(BaseDocumentParser):
    def parse(self, file_path: Path, session_id: str) -> ParsedDocument:
        logger.info(f"[{session_id}] Bắt đầu bóc tách tệp DOCX: {file_path}")
        try:
            doc = docx.Document(str(file_path))
        except Exception as e:
            raise ValueError(f"Không thể mở tệp DOCX hoặc tệp bị hỏng: {e}")

        # Ensure asset directory exists
        asset_dir = settings.STORAGE_DIR / "assets" / session_id
        asset_dir.mkdir(parents=True, exist_ok=True)

        doc_title: Optional[str] = doc.core_properties.title or None
        blocks: List[ParsedBlock] = []
        order_index = 0
        img_counter = 1

        # Trích xuất hình ảnh nhúng từ document relationships
        image_part_map = {}
        for rel in doc.part.rels.values():
            if "image" in rel.target_ref:
                try:
                    img_filename = f"img_{img_counter:03d}_{Path(rel.target_ref).name}"
                    img_path = asset_dir / img_filename
                    with open(img_path, "wb") as f:
                        f.write(rel.target_part.blob)
                    image_part_map[rel.rId] = f"/api/v1/assets/{session_id}/{img_filename}"
                    img_counter += 1
                except Exception as img_err:
                    logger.warning(f"[{session_id}] Không thể lưu ảnh nhúng: {img_err}")

        # Duyệt tuần tự các phần tử trong thân văn bản (Paragraphs và Tables)
        for child in doc.element.body:
            if isinstance(child, CT_P):
                p = Paragraph(child, doc)
                text = p.text.strip()
                if not text:
                    continue

                style_name = p.style.name.lower() if p.style else ""
                if "heading 1" in style_name or "title" in style_name:
                    segment_type = "TITLE" if not doc_title else "HEADING"
                    if not doc_title:
                        doc_title = text
                elif "heading" in style_name:
                    segment_type = "HEADING"
                else:
                    segment_type = "PARAGRAPH"

                blocks.append(
                    ParsedBlock(
                        order_index=order_index,
                        segment_type=segment_type,
                        content=text,
                    )
                )
                order_index += 1

            elif isinstance(child, CT_Tbl):
                tbl = Table(child, doc)
                table_rows = []
                for row in tbl.rows:
                    cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                    table_rows.append(" | ".join(cells))

                if table_rows:
                    # Chuyển đổi bảng thành định dạng bảng Markdown
                    header = table_rows[0]
                    num_cols = len(header.split(" | "))
                    separator = " | ".join(["---"] * num_cols)
                    body = "\n".join(table_rows[1:]) if len(table_rows) > 1 else ""
                    table_content = f"{header}\n{separator}\n{body}".strip()

                    blocks.append(
                        ParsedBlock(
                            order_index=order_index,
                            segment_type="TABLE",
                            content=table_content,
                        )
                    )
                    order_index += 1

        # Nếu có hình ảnh được trích xuất, thêm các block hình ảnh
        for r_id, web_path in image_part_map.items():
            blocks.append(
                ParsedBlock(
                    order_index=order_index,
                    segment_type="FIGURE",
                    content=f"[Hình ảnh minh họa kiến trúc bài báo {Path(web_path).name}]",
                    media_path=web_path,
                )
            )
            order_index += 1

        if not blocks:
            raise ValueError("Tệp DOCX rỗng không chứa văn bản hoặc nội dung hợp lệ.")

        logger.info(
            f"[{session_id}] Bóc tách DOCX hoàn tất: {len(blocks)} phân đoạn, "
            f"{len(image_part_map)} hình ảnh."
        )

        return ParsedDocument(
            title=doc_title,
            blocks=blocks,
        )
