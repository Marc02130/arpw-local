from __future__ import annotations

from dataclasses import dataclass, asdict

from app.services.citations import NumberedSource, cited_sids


@dataclass
class SentenceAttribution:
    sentence: str
    section: str
    citedSids: list[str]
    vectorIds: list[str]
    fileIds: list[str]
    uncited: bool


def split_sentences(text: str) -> list[str]:
    cleaned = " ".join(text.split()).strip()
    if not cleaned:
        return []
    parts: list[str] = []
    buf = ""
    in_quote = False
    for i, ch in enumerate(cleaned):
        buf += ch
        if ch in "\"“”":
            in_quote = not in_quote
        if not in_quote and ch in ".!?":
            nxt = cleaned[i + 1] if i + 1 < len(cleaned) else None
            if nxt is None or nxt == " ":
                sentence = buf.strip()
                if sentence and not sentence.startswith("#"):
                    parts.append(sentence)
                buf = ""
    tail = buf.strip()
    if tail and not tail.startswith("#"):
        parts.append(tail)
    return parts


def attribute_sentences(
    text: str, section: str, sources: list[NumberedSource]
) -> list[SentenceAttribution]:
    allowed = {s.sid for s in sources}
    by_sid = {s.sid: s for s in sources}
    rows: list[SentenceAttribution] = []
    for sentence in split_sentences(text):
        sids = cited_sids(sentence, allowed)
        vector_ids = [str(by_sid[s].vector_id) for s in sids if s in by_sid]
        file_ids = [str(by_sid[s].file_id) for s in sids if s in by_sid]
        rows.append(
            SentenceAttribution(
                sentence=sentence,
                section=section,
                citedSids=sids,
                vectorIds=vector_ids,
                fileIds=file_ids,
                uncited=len(sids) == 0,
            )
        )
    return rows


def uncited_sentences(rows: list[SentenceAttribution]) -> list[SentenceAttribution]:
    return [row for row in rows if row.uncited]


def attribution_as_json(rows: list[SentenceAttribution]) -> list[dict]:
    return [asdict(row) for row in rows]
