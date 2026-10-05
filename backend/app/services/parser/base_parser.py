from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class ParsedBlock:
    order_index: int
    segment_type: str  # TITLE, HEADING, PARAGRAPH, TABLE, FIGURE
    content: str
    media_path: Optional[str] = None


@dataclass
class ParsedDocument:
    title: Optional[str] = None
    authors: List[str] = field(default_factory=list)
    abstract: Optional[str] = None
    blocks: List[ParsedBlock] = field(default_factory=list)


class BaseDocumentParser(ABC):
    @abstractmethod
    def parse(self, file_path: Path, session_id: str) -> ParsedDocument:
        """Parse the input document and return structured blocks."""
        pass
