from __future__ import annotations

from app.services.citations import extract_sids


def run_citation_check(
    content: str,
    allowed_sids: list[str],
    cited_file_ids: list[str],
    paper_reference_file_ids: list[str],
) -> dict:
    allowed = set(allowed_sids)
    paper_refs = set(paper_reference_file_ids)
    cited = extract_sids(content)
    issues: list[dict] = []
    for sid in cited:
        if sid not in allowed:
            issues.append({"kind": "unknown_sid", "sid": sid})
    for file_id in cited_file_ids:
        if file_id not in paper_refs:
            issues.append({"kind": "missing_paper_reference", "fileId": file_id})
    return {
        "ok": len(issues) == 0,
        "citedSids": cited,
        "citedFileIds": cited_file_ids,
        "issues": issues,
    }
