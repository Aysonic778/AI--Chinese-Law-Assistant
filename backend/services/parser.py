from __future__ import annotations

from pathlib import Path


def extract_text(file_path: Path, content: bytes | None = None) -> str:
    suffix = file_path.suffix.lower()
    if suffix in {".txt", ".md"}:
        if content is not None:
            return content.decode("utf-8")
        return file_path.read_text(encoding="utf-8")

    if suffix == ".pdf":
        import fitz

        if content is not None:
            doc = fitz.open(stream=content, filetype="pdf")
        else:
            doc = fitz.open(file_path)
        try:
            return "\n".join(page.get_text() for page in doc)
        finally:
            doc.close()

    if suffix == ".docx":
        from io import BytesIO

        from docx import Document as DocxDocument

        source = BytesIO(content) if content is not None else file_path
        doc = DocxDocument(source)
        return "\n".join(paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip())

    raise ValueError(f"不支持的文件格式: {suffix}，请上传 .txt / .md / .pdf / .docx")
