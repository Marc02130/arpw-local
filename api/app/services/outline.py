from __future__ import annotations

import re
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import User, UserPaper
from app.services import chat as chat_service
from app.services import citations as citations_service
from app.services import llm_keys
from app.services import retrieve as retrieve_service
from app.services.chat import MissingLlmKey
from app.services.templates import PAPER_SECTIONS, is_known_paper_type


def outline_for_section(outline: str, section: str) -> str:
    text = outline.strip()
    if not text:
        return ""
    heading = re.compile(rf"^##\s+{re.escape(section)}\s*$", re.I | re.M)
    match = heading.search(text)
    if not match:
        return text
    start = match.end()
    rest = text[start:]
    nxt = re.search(r"^##\s+", rest, re.M)
    block = (rest if nxt is None else rest[: nxt.start()]).strip()
    return f"## {section}\n{block}" if block else f"## {section}"


def build_outline_prompt(
    paper_type: str, sections: list[str], research_prompt: str, source_block: str
) -> str:
    headings = [s for s in sections if s != "References"]
    heading_list = "\n".join(f"## {s}" for s in headings)
    return (
        f"Write an outline for a {paper_type} using only the retrieved sources.\n"
        f"Research prompt:\n{research_prompt}\n\n"
        f"Use exactly these markdown headings, in this order:\n{heading_list}\n"
        "Under each heading, write 2–6 short bullets for what that section should cover.\n"
        "Cite retrieved sources as [S#] where a bullet depends on a source. "
        "Do not invent studies, n, or outcomes.\n"
        "Do not write the full paper. Do not add extra ## headings.\n\n"
        f"Retrieved sources (cite only these ids, like [S1]):\n{source_block}\n\n"
        "If you cite a source, use the [S#] id exactly. Do not invent ids."
    )


def generate_outline(
    session: Session,
    user: User,
    paper: UserPaper,
    paper_type: str,
    sections: list[str],
    research_prompt: str,
) -> str:
    if not is_known_paper_type(paper_type):
        raise ValueError("Unknown paper type")
    if not sections:
        raise ValueError("Select at least one section")
    unknown = [s for s in sections if s not in PAPER_SECTIONS]
    if unknown:
        raise ValueError("Unknown paper section")
    topic = research_prompt.strip()
    if not topic:
        raise ValueError("Enter a research prompt")
    row = llm_keys.get_or_create_settings(session, user)
    if not llm_keys.resolve_key(row, row.chat_provider):
        raise MissingLlmKey(row.chat_provider)
    first = next((s for s in sections if s != "References"), sections[0])
    passages = retrieve_service.retrieve_for_section(
        session, user.id, paper_type, first, topic, paper_id=paper.paper_id
    )
    numbered = citations_service.number_sources(passages)
    prompt = build_outline_prompt(
        paper_type, sections, topic, citations_service.format_sources_for_prompt(numbered)
    )
    raw = chat_service.complete(prompt, user, row)
    outline = citations_service.strip_unknown_citations(
        raw, citations_service.allowed_sid_set(numbered)
    )
    paper.outline = outline
    session.commit()
    return outline
