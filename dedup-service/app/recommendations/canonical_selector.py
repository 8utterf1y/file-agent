from __future__ import annotations

import re
from datetime import datetime

from app.models.chunk import Chunk
from app.models.document import Document


POSITIVE_PATH_TERMS = ("official", "current", "latest", "规范", "标准", "正式", "发布")
NEGATIVE_PATH_TERMS = ("old", "backup", "archive", "deprecated", "历史", "旧版", "备份")


def select_canonical_chunk(chunks: list[Chunk], documents_by_id: dict[str, Document]) -> tuple[str | None, str]:
    if not chunks:
        return None, "没有可选 chunk。"
    scored = sorted(
        ((_score_chunk(chunk, documents_by_id[chunk.doc_id]), chunk) for chunk in chunks if chunk.doc_id in documents_by_id),
        key=lambda item: item[0],
        reverse=True,
    )
    if not scored:
        return None, "缺少文档元数据，无法选择主版本。"
    best_score, best_chunk = scored[0]
    doc = documents_by_id[best_chunk.doc_id]
    return (
        best_chunk.chunk_id,
        f"选择 {doc.filename} 作为主版本候选，综合路径关键词、更新时间、版本号、格式和内容完整度得分 {best_score:.2f}。",
    )


def _score_chunk(chunk: Chunk, document: Document) -> float:
    path = document.path.lower()
    score = 0.0
    score += sum(5.0 for term in POSITIVE_PATH_TERMS if term in path)
    score -= sum(5.0 for term in NEGATIVE_PATH_TERMS if term in path)
    score += _mtime_score(document.mtime)
    score += _version_score(document.filename)
    score += min(len(chunk.text) / 1000.0, 2.0)
    if document.file_ext == ".md":
        score += 1.5
    elif document.file_ext == ".docx":
        score += 1.2
    elif document.file_ext == ".pdf":
        score += 0.5
    return score


def _mtime_score(mtime: datetime) -> float:
    return mtime.timestamp() / 1_000_000_000


def _version_score(filename: str) -> float:
    matches = re.findall(r"[vV](\d+(?:\.\d+)*)", filename)
    if not matches:
        return 0.0
    version = matches[-1]
    parts = [int(part) for part in version.split(".")]
    return sum(part / (10 ** index) for index, part in enumerate(parts))
