"""Source-preserving sections and bounded chunks. No model-generated source content."""

import hashlib
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid5

from app.models.document_index import DocumentChunk, DocumentSection

CHUNKING_VERSION = "sections-chunks-v1"
MAX_CHUNK_CHARS = 1200


@dataclass(frozen=True)
class PageSource:
    page_index: int
    text: str
    source_hash: str
    extraction_version: str
    state: str


@dataclass
class ChunkPlan:
    sections: list[DocumentSection]
    chunks: list[DocumentChunk]
    warnings: list[str]


def build_chunks(document_id: UUID, pages: list[PageSource], outline: list) -> ChunkPlan:
    pages = sorted(pages, key=lambda page: page.page_index)
    if not pages:
        return ChunkPlan([], [], ["no_completed_text_pages"])
    by_page = {page.page_index: page for page in pages}
    last_page = max(by_page)
    sections, anchors, warnings = [], [], []
    stack = []
    entries = []
    for item in outline:
        if (
            len(item) >= 3
            and isinstance(item[0], int)
            and item[0] > 0
            and isinstance(item[1], str)
            and isinstance(item[2], int)
            and 0 <= item[2] - 1 <= last_page
        ):
            entries.append((item[0], item[1], item[2] - 1))
    if any(entries[i][2] > entries[i + 1][2] for i in range(len(entries) - 1)):
        entries = []
        warnings.append("outline_not_in_page_order")
    counts = defaultdict(int)
    for _, _, page in entries:
        counts[page] += 1

    def section(title, page, parent, method):
        row = DocumentSection(
            id=uuid5(document_id, f"{CHUNKING_VERSION}:section:{len(sections)}:{title}:{page}"),
            document_id=document_id,
            parent_section_id=parent,
            section_title=title,
            section_order=len(sections),
            start_page=page,
            end_page=page,
            source_method=method,
        )
        sections.append(row)
        return row

    ambiguous = set()
    for level, title, page in entries:
        while stack and stack[-1][0] >= level:
            stack.pop()
        text = by_page[page].text if page in by_page else ""
        matches = list(re.finditer(re.escape(title.strip()), text, re.I)) if title.strip() else []
        exact = len(matches) == 1
        row = section(
            title,
            page,
            stack[-1][1].id if stack else None,
            "pdf_outline" if exact else "pdf_outline_page",
        )
        stack.append((level, row))
        if not exact and counts[page] > 1:
            ambiguous.add(page)
        anchors.append((page, matches[0].start() if exact else 0, row))
    if not entries:
        numbered = {}
        for page in pages:
            if page.state != "completed":
                continue
            # A conservative fallback; explicitly labeled heuristic, never a PDF bookmark.
            for match in re.finditer(r"(?m)^(\d+(?:\.\d+)*)(?:\.?\s+)([^\n]{3,90})$", page.text):
                number, title = match.group(1), match.group(2).strip()
                if not title[0].isalpha() or title.endswith((".", ":")):
                    continue
                parent = numbered.get(number.rpartition(".")[0])
                row = section(
                    match.group(0).strip(),
                    page.page_index,
                    parent.id if parent else None,
                    "numbered_heading_heuristic",
                )
                numbered[number] = row
                anchors.append((page.page_index, match.start(), row))
    # Conflicting destination order within a page cannot establish an exact section boundary.
    for i in range(len(anchors) - 1):
        if anchors[i][:2] >= anchors[i + 1][:2] and anchors[i][0] == anchors[i + 1][0]:
            ambiguous.add(anchors[i][0])
    if ambiguous:
        warnings.append("ambiguous_outline_pages_use_page_fallback")
    anchors.sort(key=lambda item: item[:2])
    chunks = []
    per_section = defaultdict(int)
    section_map = {row.id: row for row in sections}

    def add_range(page, start, end, row):
        while start < end:
            while start < end and page.text[start].isspace():
                start += 1
            stop = min(end, start + MAX_CHUNK_CHARS)
            if stop < end:
                boundary = page.text.rfind(" ", start + MAX_CHUNK_CHARS // 2, stop)
                newline = page.text.rfind("\n", start + MAX_CHUNK_CHARS // 2, stop)
                stop = max(boundary, newline) if max(boundary, newline) > start else stop
            trimmed = stop
            while trimmed > start and page.text[trimmed - 1].isspace():
                trimmed -= 1
            if trimmed > start:
                text = page.text[start:trimmed]
                kind = (
                    "table_candidate"
                    if re.search(r"\btable\b", text, re.I)
                    else "diagram_candidate"
                    if re.search(r"\b(figure|diagram)\b", text, re.I)
                    else "text"
                )
                chunks.append(
                    DocumentChunk(
                        id=uuid5(
                            document_id,
                            f"{CHUNKING_VERSION}:{page.source_hash}:{page.page_index}:{start}:{trimmed}",
                        ),
                        document_id=document_id,
                        section_id=row.id,
                        page_start=page.page_index,
                        page_end=page.page_index,
                        chunk_index=len(chunks),
                        section_chunk_index=per_section[row.id],
                        cleaned_text=text,
                        content_type=kind,
                        source_span=[
                            {
                                "page_index": page.page_index,
                                "start_char": start,
                                "end_char": trimmed,
                                "extraction_version": page.extraction_version,
                            }
                        ],
                        source_hash=page.source_hash,
                        content_hash=hashlib.sha256(text.encode()).hexdigest(),
                        chunking_version=CHUNKING_VERSION,
                        embedding=None,
                        embedding_model=None,
                        embedding_version=None,
                        created_at=datetime.now(UTC),
                    )
                )
                per_section[row.id] += 1
                parent = row
                while parent:
                    parent.end_page = max(parent.end_page, page.page_index)
                    parent = section_map.get(parent.parent_section_id)
            start = stop

    for page in pages:
        if page.state != "completed" or not page.text.strip():
            continue
        local = [a for a in anchors if a[0] == page.page_index]
        previous = [a for a in anchors if a[0] < page.page_index]
        current = previous[-1][2] if previous else None
        if page.page_index in ambiguous:
            local = []
            current = None
        start = 0
        for _, offset, row in local + [(page.page_index, len(page.text), None)]:
            if offset > start:
                if current is None:
                    current = section(
                        f"Page {page.page_index + 1}", page.page_index, None, "page_fallback"
                    )
                    section_map[current.id] = current
                add_range(page, start, offset, current)
            start, current = offset, row
    if any(page.state != "completed" for page in pages):
        warnings.append("incomplete_pages_excluded")
    sections.sort(key=lambda row: (row.start_page, row.section_order))
    for index, row in enumerate(sections):
        row.section_order = index
    return ChunkPlan(sections, chunks, warnings)
