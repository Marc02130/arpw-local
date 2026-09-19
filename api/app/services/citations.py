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


def extract_sids(text: str) -> list[str]:
    found = CITE.findall(text)
    out: list[str] = []
    for token in found:
        sid = token[1:-1]
        if sid not in out:
            out.append(sid)
    return out


def cited_sids(text: str, allowed: set[str]) -> list[str]:
    return [sid for sid in extract_sids(text) if sid in allowed]


def file_ids_for_sids(sids: list[str], sources: list[NumberedSource]) -> list[UUID]:
    wanted = set(sids)
    out: list[UUID] = []
    for source in sources:
        if source.sid in wanted and source.file_id not in out:
            out.append(source.file_id)
    return out


def format_references_list(files: list[dict], citation_style: str = "APA") -> str:
    if not files:
        return (
            "No works were cited in earlier sections. References are catalog records "
            "for DOIs or PMIDs on the cited uploads."
        )
    lines: list[str] = []
    for file in files:
        stored = (file.get("citation_text") or "").replace("\n", " ").strip()
        if stored:
            lines.append(stored)
        else:
            name = file.get("file_name") or file.get("file_id") or "Untitled"
            lines.append(f"{name} ({citation_style}).")
    return "\n\n".join(lines)


def strip_unknown_citations(text: str, allowed: set[str]) -> str:
    def keep(token: re.Match[str]) -> str:
        sid = token.group(0)[1:-1]
        return token.group(0) if sid in allowed else ""

    stripped = CITE.sub(keep, text)
    stripped = re.sub(r"[ \t]+\n", "\n", stripped)
    stripped = re.sub(r"  +", " ", stripped)
    stripped = re.sub(r" +([.,;:])", r"\1", stripped)
    return stripped.strip()
