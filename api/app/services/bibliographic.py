from __future__ import annotations

import re
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Reference, ReferenceVector

DOI_RE = re.compile(r"\b10\.\d{4,}/[^\s\]>)+,'\"]+", re.I)
PMID_RE = re.compile(r"\bPMID[:\s]+(\d{4,9})\b", re.I)
CROSSREF_UA = "arpw-local/1.0 (https://github.com/Marc02130/arpw-local)"


def extract_doi(text: str) -> str | None:
    match = DOI_RE.search(text or "")
    if not match:
        return None
    return match.group(0).rstrip(").,;")


def extract_pmid(text: str) -> str | None:
    match = PMID_RE.search(text or "")
    return match.group(1) if match else None


def _sample_text(session: Session, file_id: UUID) -> str:
    rows = session.scalars(
        select(ReferenceVector)
        .where(ReferenceVector.file_id == file_id)
        .order_by(ReferenceVector.chunk_index)
        .limit(8)
    ).all()
    return "\n".join(r.chunk_text for r in rows)


def lookup_crossref(doi: str) -> tuple[dict | None, str | None]:
    try:
        with httpx.Client(timeout=12.0, follow_redirects=True) as client:
            res = client.get(
                f"https://api.crossref.org/works/{doi}",
                headers={"User-Agent": CROSSREF_UA},
            )
            if res.status_code >= 400:
                return None, None
            work = (res.json() or {}).get("message") or {}
            title = ""
            if isinstance(work.get("title"), list) and work["title"]:
                title = str(work["title"][0])
            year = None
            issued = work.get("issued") or {}
            parts = issued.get("date-parts") or []
            if parts and parts[0]:
                year = parts[0][0]
            authors = []
            for row in work.get("author") or []:
                family = (row.get("family") or "").strip()
                given = (row.get("given") or "").strip()
                if family and given:
                    authors.append(f"{family}, {given[0]}.")
                elif family:
                    authors.append(family)
            container = ""
            if isinstance(work.get("container-title"), list) and work["container-title"]:
                container = str(work["container-title"][0])
            record = {
                "doi": doi,
                "title": title,
                "year": year,
                "authors": authors,
                "container": container,
            }
            who = ", ".join(authors) if authors else "Unknown"
            when = f"({year})" if year else "(n.d.)"
            where = f" {container}." if container else ""
            citation = f"{who} {when}. {title}.{where} https://doi.org/{doi}"
            return record, citation.replace("  ", " ").strip()
    except OSError:
        return None, None


def fill_citation(session: Session, doc: Reference) -> None:
    if doc.citation_text:
        return
    sample = _sample_text(session, doc.file_id)
    doi = extract_doi(sample)
    if not doi:
        return
    record, citation = lookup_crossref(doi)
    if not citation:
        return
    doc.bibliographic = record
    doc.citation_text = citation
    session.commit()


def lookup_for_file(session: Session, user_id: UUID, file_id: UUID | None, doi: str | None) -> Reference:
    if file_id is None:
        raise ValueError("file_id is required")
    doc = session.get(Reference, file_id)
    if doc is None or doc.user_id != user_id:
        raise ValueError("Reference not found")
    target_doi = (doi or "").strip() or extract_doi(_sample_text(session, doc.file_id))
    if not target_doi:
        raise ValueError("No DOI found")
    record, citation = lookup_crossref(target_doi)
    if not citation:
        raise ValueError("Lookup failed")
    doc.bibliographic = record
    doc.citation_text = citation
    session.commit()
    session.refresh(doc)
    return doc
