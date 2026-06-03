from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".html", ".htm", ".md", ".txt"}


@dataclass(frozen=True)
class FileItem:
    path: str
    filename: str
    file_ext: str
    file_size: int
    mtime: datetime


def scan_local_dir(root: str) -> list[FileItem]:
    root_path = Path(root).expanduser().resolve()
    if not root_path.exists():
        raise FileNotFoundError(f"Source path does not exist: {root}")
    if not root_path.is_dir():
        raise NotADirectoryError(f"Source path is not a directory: {root}")

    items: list[FileItem] = []
    for path in root_path.rglob("*"):
        if not path.is_file():
            continue
        if path.name.startswith("~$"):
            continue
        ext = path.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            continue
        stat = path.stat()
        items.append(
            FileItem(
                path=str(path),
                filename=path.name,
                file_ext=ext,
                file_size=stat.st_size,
                mtime=datetime.fromtimestamp(stat.st_mtime),
            )
        )
    return sorted(items, key=lambda item: item.path)
