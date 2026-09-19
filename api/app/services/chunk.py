from __future__ import annotations

import re
from dataclasses import dataclass

from app.config import settings

UNKNOWN_SECTION = "Unknown"
OTHER_SECTION = "Other"
CANONICAL_SECTIONS = (
    "Abstract",
    "Introduction",
    "Literature Review",
    "Methods",
    "Results",
    "Discussion",
    "Conclusion",
    "References",
)

HEADING_ALIASES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^abstracts?$"), "Abstract"),
    (re.compile(r"^intro(duction)?$"), "Introduction"),
    (re.compile(r"^background$"), "Introduction"),
    (re.compile(r"^related\s+works?$"), "Literature Review"),
    (re.compile(r"^literature\s+review$"), "Literature Review"),
    (re.compile(r"^prior\s+works?$"), "Literature Review"),
    (re.compile(r"^methods?$"), "Methods"),
    (re.compile(r"^methodology$"), "Methods"),
    (re.compile(r"^materials\s+and\s+methods$"), "Methods"),
    (re.compile(r"^experimental(\s+(setup|procedure|methods?))?$"), "Methods"),
    (re.compile(r"^results?$"), "Results"),
    (re.compile(r"^findings$"), "Results"),
    (re.compile(r"^results?\s+and\s+discussions?$"), "Results"),
    (re.compile(r"^discussion$"), "Discussion"),
    (re.compile(r"^conclusions?$"), "Conclusion"),
    (re.compile(r"^concluding\s+remarks$"), "Conclusion"),
    (re.compile(r"^references$"), "References"),
    (re.compile(r"^bibliography$"), "References"),
    (re.compile(r"^works\s+cited$"), "References"),
    (re.compile(r"^literature\s+cited$"), "References"),
]

OTHER_HEADING_RES = [
    re.compile(r"^appendix(\s+[a-z0-9]+)?$"),
    re.compile(r"^supplementary(\s+materials?)?$"),
    re.compile(r"^acknowledg(e)?ments?$"),
    re.compile(r"^funding$"),
    re.compile(r"^data\s+availability$"),
    re.compile(r"^author\s+contributions?$"),
    re.compile(r"^conflicts?\s+of\s+interest"),
    re.compile(r"^ethics"),
    re.compile(r"^keywords?$"),
]


@dataclass
class TextChunk:
    text: str
    chunk_index: int
    section: str
    page: int | None
    chunk_role: str | None = None


def _heading_candidates(line: str) -> list[str]:
    trimmed = line.strip()
    if not trimmed:
        return []
    stripped = [
        trimmed,
        re.sub(r"^#{1,6}\s+", "", trimmed),
        re.sub(r"^\d+(\.\d+)*\.?\s+", "", trimmed),
        re.sub(r"^[ivxlcdm]{1,6}\.\s+", "", trimmed, flags=re.I),
        re.sub(r"^[A-H]\.\s+", "", trimmed),
    ]
    return list(dict.fromkeys(stripped))


def parse_heading(line: str) -> str | None:
    trimmed = line.strip()
    if len(trimmed) < 2 or len(trimmed) > 80:
        return None
    if len(trimmed.split()) > 12:
        return None
    if re.search(r"[,;]$", trimmed):
        return None
    for candidate in _heading_candidates(trimmed):
        normalized = re.sub(r"[:.\s]+$", "", candidate).lower()
        normalized = re.sub(r"\s+", " ", normalized).strip()
        if not normalized:
            continue
        for pattern, section in HEADING_ALIASES:
            if pattern.match(normalized):
                return section
        for pattern in OTHER_HEADING_RES:
            if pattern.match(normalized):
                return OTHER_SECTION
    if re.match(r"^#{1,6}\s+\S", trimmed):
        return OTHER_SECTION
    return None


def _window_chunks(text: str, chunk_size: int, overlap: int, min_chars: int) -> list[str]:
    cleaned = re.sub(r"\n{3,}", "\n\n", text.replace("\r\n", "\n")).strip()
    if not cleaned:
        return []
    out: list[str] = []
    offset = 0
    while offset < len(cleaned):
        end = min(offset + chunk_size, len(cleaned))
        slice_ = cleaned[offset:end].strip()
        if len(slice_) >= min_chars:
            out.append(slice_)
        if end >= len(cleaned):
            break
        offset += max(chunk_size - overlap, 1)
    return out


def chunk_pages(pages: list[str]) -> list[TextChunk]:
    chunk_size = settings.CHUNK_SIZE
    overlap = settings.CHUNK_OVERLAP
    min_chars = settings.MIN_CHUNK_CHARS
    chunks: list[TextChunk] = []
    chunk_index = 0
    section = UNKNOWN_SECTION
    section_page: int | None = None
    buf: list[str] = []

    def flush() -> None:
        nonlocal chunk_index, buf
        text = "\n".join(buf)
        for piece in _window_chunks(text, chunk_size, overlap, min_chars):
            chunks.append(
                TextChunk(
                    text=piece,
                    chunk_index=chunk_index,
                    section=section,
                    page=section_page,
                )
            )
            chunk_index += 1
        buf = []

    for page_index, page_text in enumerate(pages, start=1):
        for line in page_text.replace("\r\n", "\n").split("\n"):
            heading = parse_heading(line)
            if heading:
                flush()
                section = heading
                section_page = page_index
                if line.strip():
                    buf = [line.strip()]
                continue
            if section_page is None:
                section_page = page_index
            buf.append(line)
    flush()
    return chunks
