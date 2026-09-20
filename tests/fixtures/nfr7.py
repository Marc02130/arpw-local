"""Synthetic NFR-7 corpus. Not a real paper; no PII."""

NFR7_PROBE = "nfr7probe"
NFR7_BIBLIOGRAPHY = (
    "Smith, A. (2020). Unrelated bibliography entry that must not mix into methods chunks."
)
NFR7_TEXT = "\n\n".join(
    [
        "Methods",
        f"We indexed a private reference corpus and retrieved passages for a known query token {NFR7_PROBE}.",
        "Each uploaded file was parsed, split on IMRaD headings, then windowed inside a section as 384-dimension hash embeddings.",
        "Additional methods detail: sampling, inclusion criteria, and how section labels come from headings rather than the first line of a mixed window.",
        "Results",
        f"A retrieval hit on {NFR7_PROBE} must return a chunk from this fixture, not an unrelated document.",
        "Generation must refuse citation ids that were not in the retrieved set.",
        "This paragraph exists so the fixture is longer than the minimum ingest chunk size used by upload_processor.",
        "Additional results detail: overlap with the probe token, embedding dimension, and that empty files are rejected before embed.",
        "References",
        f"{NFR7_BIBLIOGRAPHY} Extra filler so this section exceeds the minimum chunk length used at ingest.",
    ]
)


def build_fixture_pdf(text: str = NFR7_TEXT) -> bytes:
    lines = text.split("\n")

    def escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    ops = ["BT", "/F1 12 Tf", "72 720 Td"]
    for index, line in enumerate(lines):
        if index:
            ops.append("0 -14 Td")
        ops.append(f"({escape(line)}) Tj")
    ops.append("ET")
    stream = "\n".join(ops).encode("latin-1", errors="replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    parts = [b"%PDF-1.4\n"]
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(sum(len(p) for p in parts))
        parts.append(f"{i} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref_at = sum(len(p) for p in parts)
    xref = [b"xref\n0 6\n0000000000 65535 f \n"]
    for off in offsets[1:]:
        xref.append(f"{off:010d} 00000 n \n".encode())
    trailer = (
        b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n"
        + str(xref_at).encode()
        + b"\n%%EOF\n"
    )
    return b"".join(parts + xref + [trailer])
