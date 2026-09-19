from __future__ import annotations

import re

ROLES = (
    "claim",
    "finding",
    "evaluation",
    "method",
    "context",
    "experience",
    "citation",
    "boilerplate",
)

DEFAULT_RETRIEVE = frozenset({"claim", "finding", "evaluation", "context"})
EXCLUDE_DEFAULT = frozenset({"citation", "boilerplate", "experience"})

_DOI = re.compile(r"\bdoi\.org\b|\b10\.\d{4,}/", re.I)
_ET_AL = re.compile(r"\bet al\.?\b", re.I)
_HTTP = re.compile(r"https?://", re.I)
_PUBMED = re.compile(r"\[pubmed:|\bpmid:\s*\d+", re.I)
_ZWSP = dict.fromkeys(map(ord, "\u200b\u200c\u200d\ufeff"), None)
_FIGURE_CAPTION = re.compile(
    r"\bfigure\s+\d+\b.*\b(illustrates|shows|flowchart|flow chart)\b",
    re.I | re.S,
)
_JUNK_PHRASES = (
    "substantial contributions to the conception",
    "final approval of the version to be published",
    "agreement to be accountable for all aspects",
    "competing interests",
    "data availability",
    "acknowledgements",
    "informed consent",
    "ethics committee",
)


def _norm(text: str) -> str:
    return (text or "").translate(_ZWSP).lower()


def classify_chunk(text: str, heading: str = "") -> str:
    blob = f"{heading}\n{text}"
    low = _norm(blob)
    head = _norm(heading)

    if any(k in head for k in ("reference", "bibliograph", "works cited", "literature cited")):
        return "citation"
    if any(
        k in head
        for k in (
            "acknowledg",
            "funding",
            "competing interest",
            "conflict of interest",
            "data availability",
        )
    ):
        return "boilerplate"
    if _DOI.search(blob) or _PUBMED.search(low):
        return "citation"
    if len(_ET_AL.findall(blob)) >= 3 and len(text) < 2500:
        return "citation"
    if low.startswith("http") or (len(_HTTP.findall(blob)) >= 3 and "we found" not in low):
        return "citation"
    if any(k in low for k in ("i felt", "i remember", "dear diary", "this morning i")):
        return "experience"
    if any(k in low for k in ("we hypothesize", "we propose", "it is hypothesized", "we argue")):
        return "claim"
    if any(
        k in low
        for k in ("we found", "was associated", "significantly", "these findings", "showed that")
    ):
        return "finding"
    if any(
        k in low
        for k in ("limitation", "cannot establish", "causal relationship cannot", "further studies")
    ):
        return "evaluation"
    if heading.lower() in {"methods", "methodology"}:
        return "method"
    if heading.lower() in {"results"}:
        return "finding"
    return "context"


def is_junk_chunk(text: str, heading: str = "") -> bool:
    piece = (text or "").strip()
    if len(piece) < 8:
        return True
    if re.fullmatch(r"[\d\s.\-]+", piece):
        return True
    low = _norm(f"{heading}\n{piece}")
    if any(p in low for p in _JUNK_PHRASES):
        return True
    if _FIGURE_CAPTION.search(piece):
        return True
    words = re.findall(r"[A-Za-z]{2,}", piece)
    digits = sum(1 for ch in piece if ch.isdigit())
    if digits / max(len(piece), 1) > 0.4 and len(words) < 40:
        return True
    return False
