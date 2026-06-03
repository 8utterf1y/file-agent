from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup


@dataclass(frozen=True)
class ParsedDocument:
    title: str | None
    markdown: str


def parse_document(path: str) -> ParsedDocument:
    file_path = Path(path)
    ext = file_path.suffix.lower()
    if ext in {".txt", ".md"}:
        markdown = file_path.read_text(encoding="utf-8", errors="replace")
        return ParsedDocument(title=_first_markdown_title(markdown) or file_path.stem, markdown=markdown)
    if ext in {".html", ".htm"}:
        return _parse_html(file_path)
    if ext in {".pdf", ".docx", ".pptx"}:
        return _parse_with_docling(file_path)
    raise ValueError(f"Unsupported file extension: {ext}")


def _first_markdown_title(markdown: str) -> str | None:
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or None
    return None


def _parse_html(path: Path) -> ParsedDocument:
    html = path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else path.stem
    blocks: list[str] = []
    for element in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "pre", "code"]):
        text = " ".join(element.get_text(" ", strip=True).split())
        if not text:
            continue
        if element.name and element.name.startswith("h"):
            level = int(element.name[1])
            blocks.append(f"{'#' * level} {text}")
        elif element.name == "pre":
            blocks.append(f"```\n{element.get_text(strip=False).strip()}\n```")
        else:
            blocks.append(text)
    return ParsedDocument(title=title, markdown="\n\n".join(blocks))


def _parse_with_docling(path: Path) -> ParsedDocument:
    try:
        from docling.document_converter import DocumentConverter

        result = DocumentConverter().convert(str(path))
        markdown = result.document.export_to_markdown()
        return ParsedDocument(title=_first_markdown_title(markdown) or path.stem, markdown=markdown)
    except Exception as exc:
        raise RuntimeError(f"Docling failed to parse {path}: {exc}") from exc
