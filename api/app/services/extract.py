from __future__ import annotations

import io
import zipfile

KIND_MIME = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "txt": "text/plain",
}


class UnsupportedFileType(ValueError):
    pass


def detect_kind(data: bytes) -> str:
    if data.startswith(b"%PDF"):
        return "pdf"
    if data.startswith(b"PK\x03\x04") and _zip_has_word_document(data):
        return "docx"
    if _looks_like_text(data):
        return "txt"
    raise UnsupportedFileType("Unsupported file type")


def extract_pages(data: bytes, kind: str) -> list[str]:
    """One string per page (1-based index = list index + 1). TXT is a single page."""
    if kind == "pdf":
        return _extract_pdf_pages(data)
    if kind == "docx":
        return [_extract_docx(data)]
    if kind == "txt":
        return [_decode_text(data)]
    raise UnsupportedFileType("Unsupported file type")


def extract_text(data: bytes, kind: str) -> str:
    return "\n".join(extract_pages(data, kind)).strip()


def _zip_has_word_document(data: bytes) -> bool:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            return "word/document.xml" in zf.namelist()
    except zipfile.BadZipFile:
        return False


def _looks_like_text(data: bytes) -> bool:
    if not data:
        return False
    if data.count(b"\x00") / len(data) > 0.01:
        return False
    try:
        data.decode("utf-8")
        return True
    except UnicodeDecodeError:
        try:
            data.decode("cp1252")
            return True
        except UnicodeDecodeError:
            return False


def _decode_text(data: bytes) -> str:
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("cp1252")


def _extract_pdf_pages(data: bytes) -> list[str]:
    try:
        import fitz

        doc = fitz.open(stream=data, filetype="pdf")
        try:
            pages = [page.get_text("text") or "" for page in doc]
        finally:
            doc.close()
        if any(p.strip() for p in pages):
            return pages
    except Exception:
        pass
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    return [(page.extract_text() or "") for page in reader.pages]


def _extract_docx(data: bytes) -> str:
    from docx import Document

    document = Document(io.BytesIO(data))
    lines: list[str] = []
    for paragraph in document.paragraphs:
        style = (paragraph.style.name or "") if paragraph.style else ""
        text = paragraph.text.strip()
        if not text:
            continue
        if style.lower().startswith("heading"):
            lines.append(text)
        else:
            lines.append(text)
    return "\n".join(lines).strip()
