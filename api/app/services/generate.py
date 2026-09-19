from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import PaperReference, Reference, User, UserPaper
from app.services import attribution as attribution_service
from app.services import chat as chat_service
from app.services import citation_check as citation_check_service
from app.services import citations as citations_service
from app.services import format_check as format_check_service
from app.services import llm_keys
from app.services import outline as outline_service
from app.services import retrieve as retrieve_service
from app.services.chat import MissingLlmKey
from app.services.templates import (
    PAPER_SECTIONS,
    build_generation_prompt,
    get_section_template,
    is_known_paper_type,
)

DRAFT_DISCLAIMER = (
    "AI-generated draft. Requires human review. Citations must match your uploaded sources. "
    "This is not a factual-accuracy score."
)


def _style_block(passages: list) -> str:
    if not passages:
        return ""
    samples = "\n\n".join(p.chunk_text for p in passages[:4])
    return (
        "Write in a similar voice and structure to these style examples "
        "(do not cite them as [S#]):\n"
        f"{samples}"
    )


def _section_prompt(
    paper_type: str,
    section: str,
    research_prompt: str,
    source_block: str,
    style_block: str,
    outline: str,
) -> str:
    style = f"\n\n{style_block.strip()}\n" if style_block.strip() else ""
    outline_block = outline_service.outline_for_section(outline, section)
    outline_note = (
        "\n\nApproved outline (follow the bullets for this section; do not add studies, n, "
        f"or outcomes that are not in retrieved sources):\n{outline_block}\n"
        if outline_block
        else ""
    )
    return (
        f"{build_generation_prompt(paper_type, section, research_prompt)}"
        f"{style}{outline_note}\n"
        f"Retrieved sources (cite only these ids, like [S1]):\n{source_block}\n\n"
        "Every sentence that states a finding, method, or claim must include a retrieved [S#]. "
        "If you cannot cite it from the retrieved set, omit that sentence. "
        "Do not write uncited claims.\n"
        "If you cite a source, use the [S#] id exactly. Do not invent ids. Do not cite style examples."
    )


def _repair_prompt(section: str, draft: str, uncited: list[str], source_block: str) -> str:
    listed = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(uncited))
    return (
        f"Rewrite only the {section} section so every finding, method, or claim includes a retrieved [S#].\n"
        f"Uncited sentences that must be cited from the retrieved set or removed:\n{listed}\n\n"
        "Keep the same meaning. Do not add studies, n, or outcomes that are not in retrieved sources.\n"
        "Do not invent [S#] ids. Cite only these retrieved sources:\n"
        f"{source_block}\n\nSection draft:\n{draft}"
    )


def generate_paper(
    session: Session,
    user: User,
    paper: UserPaper,
    *,
    paper_type: str,
    sections: list[str],
    research_prompt: str,
    citation_style: str | None,
    output_format: str | None,
) -> dict:
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

    style = citation_style or paper.citation_style
    fmt = output_format or paper.output_format
    generated: dict[str, dict] = {}
    all_file_ids: list[UUID] = []
    all_allowed: list[str] = []
    attribution_rows: list = []

    for section in sections:
        template = get_section_template(paper_type, section)
        if template.preferred_source_role == "none":
            continue
        passages = retrieve_service.retrieve_for_section(
            session, user.id, paper_type, section, topic, paper_id=paper.paper_id
        )
        numbered = citations_service.number_sources(passages)
        allowed = citations_service.allowed_sid_set(numbered)
        all_allowed.extend(sorted(allowed))
        examples = retrieve_service._match_examples(session, user.id, topic, 4)
        prompt = _section_prompt(
            paper_type,
            section,
            topic,
            citations_service.format_sources_for_prompt(numbered),
            _style_block(examples),
            paper.outline or "",
        )
        raw = chat_service.complete(prompt, user, row)
        text = citations_service.strip_unknown_citations(raw, allowed)
        section_attr = attribution_service.attribute_sentences(text, section, numbered)
        uncited = attribution_service.uncited_sentences(section_attr)
        if numbered and uncited:
            repaired = chat_service.complete(
                _repair_prompt(
                    section,
                    text,
                    [u.sentence for u in uncited],
                    citations_service.format_sources_for_prompt(numbered),
                ),
                user,
                row,
            )
            text = citations_service.strip_unknown_citations(repaired, allowed)
            section_attr = attribution_service.attribute_sentences(text, section, numbered)
        sids = citations_service.cited_sids(text, allowed)
        file_ids = citations_service.file_ids_for_sids(sids, numbered)
        for fid in file_ids:
            if fid not in all_file_ids:
                all_file_ids.append(fid)
        attribution_rows.extend(section_attr)
        generated[section] = {
            "name": section,
            "text": text,
            "cited_sids": sids,
        }

    if "References" in sections:
        files = []
        if all_file_ids:
            refs = session.scalars(
                select(Reference).where(
                    Reference.user_id == user.id, Reference.file_id.in_(all_file_ids)
                )
            ).all()
            by_id = {r.file_id: r for r in refs}
            files = [
                {
                    "file_id": str(fid),
                    "file_name": by_id[fid].file_name if fid in by_id else str(fid),
                    "citation_text": by_id[fid].citation_text if fid in by_id else None,
                }
                for fid in all_file_ids
            ]
        generated["References"] = {
            "name": "References",
            "text": citations_service.format_references_list(files, style),
            "cited_sids": [],
        }

    ordered = [generated[s] for s in sections if s in generated]
    content = "\n\n".join(f"## {s['name']}\n\n{s['text']}" for s in ordered)
    attr_json = attribution_service.attribution_as_json(attribution_rows)

    paper.content = content
    paper.sections = sections
    paper.research_prompt = topic
    if citation_style:
        paper.citation_style = citation_style
    if output_format:
        paper.output_format = output_format
    paper.status = "completed"
    paper.attribution = attr_json
    session.execute(delete(PaperReference).where(PaperReference.paper_id == paper.paper_id))
    for fid in all_file_ids:
        session.add(PaperReference(paper_id=paper.paper_id, file_id=fid))
    session.commit()
    session.refresh(paper)

    paper_ref_ids = [str(fid) for fid in all_file_ids]
    check = citation_check_service.run_citation_check(
        content, list(dict.fromkeys(all_allowed)), paper_ref_ids, paper_ref_ids
    )
    fmt_check = format_check_service.run_format_check(content, sections)
    uncited = [r for r in attribution_rows if r.uncited]
    warnings = []
    if not check["ok"]:
        for issue in check["issues"]:
            if issue["kind"] == "unknown_sid":
                warnings.append(
                    {"kind": "citation", "message": f"[{issue['sid']}] is not in the retrieved set"}
                )
    if not fmt_check["ok"]:
        for name in fmt_check["missing"]:
            warnings.append({"kind": "format", "message": f"Missing section heading: {name}"})
    for row_attr in uncited:
        snippet = row_attr.sentence[:80] + ("…" if len(row_attr.sentence) > 80 else "")
        warnings.append({"kind": "uncited", "message": f"{row_attr.section}: {snippet}"})

    return {
        "paper": {
            "paper_id": str(paper.paper_id),
            "title": paper.title,
            "content": paper.content,
            "sections": paper.sections,
            "paper_type": paper.paper_type,
            "citation_style": paper.citation_style,
            "output_format": paper.output_format,
            "status": paper.status,
            "attribution": paper.attribution,
        },
        "sections": ordered,
        "attribution": attr_json,
        "citation_check": check,
        "format_check": fmt_check,
        "warnings": warnings,
        "disclaimer": DRAFT_DISCLAIMER,
    }
