from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class Passage:
    id: UUID
    document_id: UUID
    attachment_id: UUID
    section_id: UUID
    section_title: str
    section_chunk_index: int
    text: str
    content_type: str
    content_hash: str
    source_span: list[dict]
    source_hash: str
    page_start: int
    page_end: int
    document_type: str
    document_revision: int
    is_primary: bool
    document_status: str
    file_name: str
    index_attempt_id: UUID
    incomplete: bool = False


@dataclass(frozen=True)
class Candidate:
    passage: Passage
    score: float
