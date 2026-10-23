from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ParsedBlock:
    order_index: int
    segment_type: str  # TITLE, HEADING, PARAGRAPH, TABLE, FIGURE
    content: str
    media_path: str | None = None


@dataclass
class ParsedDocument:
    title: str | None = None
    authors: list[str] = field(default_factory=list)
    abstract: str | None = None
    blocks: list[ParsedBlock] = field(default_factory=list)


class BaseDocumentParser(ABC):
    @abstractmethod
    def parse(self, file_path: Path, session_id: str) -> ParsedDocument:
        """Parse the input document and return structured blocks."""
        pass
