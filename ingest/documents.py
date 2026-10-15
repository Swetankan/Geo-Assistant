"""Offsets refer to decoded text, or each PDF page's extracted text, not PDF bytes."""
from pathlib import Path
from app.schemas import Chunk, stable_id


def load_document(path: Path, root: Path):
    source = path.resolve().relative_to(root.resolve()).as_posix()
    document_id = stable_id("doc", source)
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader
        for number, page in enumerate(PdfReader(path).pages, 1):
            yield document_id, source, number, page.extract_text() or ""
    elif path.suffix.lower() in {".md", ".txt"}:
        # newline='' preserves CRLF offsets in UTF-8 source text.
        with path.open(encoding="utf-8", newline="") as handle:
            yield document_id, source, None, handle.read()
    else:
        raise ValueError(f"Unsupported document extension: {path.suffix}")


def chunk_text(document_id, source, page, text, size=1000, overlap=150, synthetic=False):
    if not 0 <= overlap < size:
        raise ValueError("require 0 <= overlap < size")
    for start in range(0, len(text), size - overlap):
        end = min(len(text), start + size)
        segment = text[start:end]
        if segment.strip():
            yield Chunk(id=stable_id("chunk", document_id, page, start, end, segment),
                        document_id=document_id, source=source, page=page,
                        start=start, end=end, text=segment, synthetic=synthetic)
        if end == len(text):
            break


def load_corpus(root: Path, synthetic=False):
    for path in sorted(root.rglob("*")):
        if path.suffix.lower() in {".txt", ".md", ".pdf"}:
            for record in load_document(path, root):
                yield from chunk_text(*record, synthetic=synthetic)
