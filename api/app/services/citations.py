from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

CITE = re.compile(r"\[S\d+\]")


@dataclass
class NumberedSource:
    sid: str
    vector_id: UUID
    file_id: UUID
    chunk_text: str


def number_sources(passages: list) -> list[NumberedSource]:
    return [
        NumberedSource(
            sid=f"S{index + 1}",
            vector_id=passage.vector_id,
            file_id=passage.file_id,
            chunk_text=passage.chunk_text,
        )
        for index, passage in enumerate(passages)
    ]


def format_sources_for_prompt(sources: list[NumberedSource]) -> str:
    if not sources:
        return "No retrieved sources. Do not invent citations."
    return "\n\n".join(f"[{s.sid}] {s.chunk_text}" for s in sources)


def allowed_sid_set(sources: list[NumberedSource]) -> set[str]:
    return {s.sid for s in sources}


def strip_unknown_citations(text: str, allowed: set[str]) -> str:
    def keep(token: re.Match[str]) -> str:
        sid = token.group(0)[1:-1]
        return token.group(0) if sid in allowed else ""

    stripped = CITE.sub(keep, text)
    stripped = re.sub(r"[ \t]+\n", "\n", stripped)
    stripped = re.sub(r"  +", " ", stripped)
    stripped = re.sub(r" +([.,;:])", r"\1", stripped)
    return stripped.strip()
