from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SUPPORTED_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs", ".c", ".cpp", ".h", ".hpp",
    ".cs", ".php", ".rb", ".swift", ".kt", ".scala", ".sh", ".sql", ".yaml", ".yml", ".json", ".toml",
}
EXCLUDE_DIRS = {
    ".git", "node_modules", "dist", "build", "target", ".venv", "venv", "__pycache__",
    ".pytest_cache", "coverage", ".next", ".nuxt", ".turbo", ".cache", "vendor", "out", "bin",
    "obj", ".idea", ".vscode", ".opencode", ".agents", ".codex",
}
EXCLUDE_FILES = {
    "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "Cargo.lock", "go.sum",
    "*.min.js", "*.map", "*.generated.*", "*.pb.go", "*.lock", "*.pyc",
}
CONFIG_EXTENSIONS = {".yaml", ".yml", ".json", ".toml", ".sql", ".sh"}
TEST_PARTS = {"test", "tests", "__tests__", "fixtures", "fixture", "examples", "example"}
PROD_PARTS = {"src", "packages", "apps", "app", "lib"}
SCHEMA_VERSION = "1.1"
TOOL_NAME = "code-dedup"
TOOL_VERSION = "0.2.0"
TOOL_MODE = "read_only_analysis"


@dataclass(frozen=True)
class CodeFile:
    path: Path
    rel_path: str
    ext: str
    text: str
    size: int


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    path: str
    ext: str
    language: str
    kind: str
    symbol: str | None
    line_start: int
    line_end: int
    raw_text: str
    normalized_text: str
    raw_hash: str
    normalized_hash: str
    line_count: int


@dataclass(frozen=True)
class Pair:
    left: str
    right: str
    similarity: float
    duplicate_type: str


class UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, item: str) -> str:
        self.parent.setdefault(item, item)
        if self.parent[item] != item:
            self.parent[item] = self.find(self.parent[item])
        return self.parent[item]

    def union(self, left: str, right: str) -> None:
        root_left = self.find(left)
        root_right = self.find(right)
        if root_left != root_right:
            self.parent[root_right] = root_left

    def groups(self) -> list[list[str]]:
        grouped: dict[str, list[str]] = defaultdict(list)
        for item in list(self.parent):
            grouped[self.find(item)].append(item)
        return [sorted(items) for items in grouped.values() if len(items) > 1]


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def stable_id(prefix: str, raw: str) -> str:
    return f"{prefix}_{sha256_text(raw)[:16]}"


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t\f\v]+", " ", line.rstrip()).strip() for line in text.split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def language_for(ext: str) -> str:
    return {
        ".py": "python", ".js": "javascript", ".jsx": "javascript", ".ts": "typescript",
        ".tsx": "typescript", ".go": "go", ".java": "java", ".cs": "csharp", ".cpp": "cpp",
        ".c": "c", ".h": "c", ".hpp": "cpp", ".rs": "rust", ".rb": "ruby", ".php": "php",
        ".swift": "swift", ".kt": "kotlin", ".scala": "scala", ".sh": "shell", ".sql": "sql",
        ".yaml": "yaml", ".yml": "yaml", ".json": "json", ".toml": "toml",
    }.get(ext, "text")


def should_exclude_file(rel_path: str, name: str, patterns: set[str]) -> bool:
    return any(fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(rel_path, pattern) for pattern in patterns)


def should_report_ignored_file(name: str) -> bool:
    return not fnmatch.fnmatch(name, "*.pyc")


def scan_files(root: Path, include: list[str], exclude: list[str], max_file_size_kb: int) -> tuple[list[CodeFile], dict[str, list[str]], dict[str, Any]]:
    ignored = {"directories": [], "files": []}
    coverage: dict[str, Any] = {
        "scan_roots": [],
        "directories_seen": [],
        "supported_files_by_directory": defaultdict(int),
        "unsupported_files_by_extension": defaultdict(int),
    }
    roots = [root / item for item in include] if include else [root]
    files: list[CodeFile] = []
    exclude_patterns = set(EXCLUDE_FILES) | set(exclude)

    for scan_root in roots:
        coverage["scan_roots"].append(scan_root.as_posix())
        if not scan_root.exists():
            ignored["files"].append(f"{scan_root} (missing)")
            continue
        if scan_root.is_file():
            candidates = [scan_root]
        else:
            for path in scan_root.rglob("*"):
                if path.is_dir():
                    try:
                        rel_dir = path.relative_to(root).as_posix()
                        parts = set(path.relative_to(root).parts)
                    except ValueError:
                        rel_dir = path.as_posix()
                        parts = set(path.parts)
                    if not (parts & EXCLUDE_DIRS):
                        coverage["directories_seen"].append(rel_dir)
            candidates = [path for path in scan_root.rglob("*") if path.is_file()]
        for path in candidates:
            try:
                rel_path = path.relative_to(root).as_posix()
                parts = set(path.relative_to(root).parts)
            except ValueError:
                rel_path = path.as_posix()
                parts = set(path.parts)
            if parts & EXCLUDE_DIRS:
                ignored["directories"].append(rel_path)
                continue
            if should_exclude_file(rel_path, path.name, exclude_patterns):
                if should_report_ignored_file(path.name):
                    ignored["files"].append(rel_path)
                continue
            ext = path.suffix.lower()
            if ext not in SUPPORTED_EXTENSIONS:
                coverage["unsupported_files_by_extension"][ext or "(no extension)"] += 1
                continue
            try:
                stat = path.stat()
                if stat.st_size > max_file_size_kb * 1024:
                    ignored["files"].append(f"{rel_path} (too large)")
                    continue
                raw = path.read_bytes()
            except OSError:
                ignored["files"].append(f"{rel_path} (unreadable)")
                continue
            if b"\x00" in raw[:4096]:
                ignored["files"].append(f"{rel_path} (binary)")
                continue
            coverage["supported_files_by_directory"][directory(rel_path)] += 1
            files.append(CodeFile(path, rel_path, ext, raw.decode("utf-8", errors="ignore"), stat.st_size))

    ignored["directories"] = sorted(set(ignored["directories"]))
    ignored["files"] = sorted(set(ignored["files"]))
    coverage["scan_roots"] = sorted(set(coverage["scan_roots"]))
    coverage["directories_seen"] = sorted(set(coverage["directories_seen"]))
    coverage["supported_files_by_directory"] = [
        {"path": path, "files": count}
        for path, count in sorted(coverage["supported_files_by_directory"].items())
    ]
    coverage["unsupported_files_by_extension"] = [
        {"extension": ext, "files": count}
        for ext, count in sorted(coverage["unsupported_files_by_extension"].items(), key=lambda item: (-item[1], item[0]))
    ]
    return sorted(files, key=lambda item: item.rel_path), ignored, coverage


def count_lines(text: str) -> int:
    return len([line for line in text.splitlines() if line.strip()])


def make_chunk(code_file: CodeFile, kind: str, symbol: str | None, start: int, end: int, raw_text: str) -> Chunk:
    normalized = normalize_text(raw_text)
    raw_id = f"{code_file.rel_path}|{kind}|{symbol or ''}|{start}|{end}|{sha256_text(normalized)}"
    return Chunk(
        chunk_id=stable_id("chunk", raw_id),
        path=code_file.rel_path,
        ext=code_file.ext,
        language=language_for(code_file.ext),
        kind=kind,
        symbol=symbol,
        line_start=start,
        line_end=end,
        raw_text=raw_text,
        normalized_text=normalized,
        raw_hash=sha256_text(raw_text),
        normalized_hash=sha256_text(normalized),
        line_count=count_lines(raw_text),
    )


def file_chunk(code_file: CodeFile) -> Chunk:
    lines = code_file.text.splitlines()
    return make_chunk(code_file, "file", None, 1, max(1, len(lines)), code_file.text)


def symbol_match(line: str, language: str) -> tuple[str, str] | None:
    checks = [
        ({"python"}, r"^def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", "function"),
        ({"python"}, r"^class\s+([A-Za-z_][A-Za-z0-9_]*)\b", "class"),
        ({"javascript", "typescript"}, r"^(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*\(", "function"),
        ({"javascript", "typescript"}, r"^(?:export\s+)?(?:default\s+)?class\s+([A-Za-z_$][A-Za-z0-9_$]*)\b", "class"),
        ({"javascript", "typescript"}, r"^(?:export\s+)?const\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*=.*=>", "function"),
        ({"go"}, r"^func\s+(?:\([^)]*\)\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*\(", "function"),
        ({"java", "csharp", "cpp", "c"}, r"^(?:public|private|protected|static|final|async|virtual|override|\s)+.*\s+([A-Za-z_][A-Za-z0-9_]*)\s*\([^;]*\)\s*\{?\s*$", "function"),
        ({"java", "csharp", "cpp", "c"}, r"^(?:public|private|protected|static|final|abstract|\s)*(?:class|interface|enum|struct)\s+([A-Za-z_][A-Za-z0-9_]*)\b", "class"),
    ]
    for languages, pattern, kind in checks:
        if language in languages:
            match = re.match(pattern, line.strip())
            if match:
                return kind, match.group(1)
    return None


def infer_end(lines: list[str], start: int, next_start: int | None) -> int:
    if next_start is not None:
        return max(start, next_start - 1)
    if lines[start].lstrip().startswith(("def ", "class ")):
        indent = len(lines[start]) - len(lines[start].lstrip(" \t"))
        end = start
        for index in range(start + 1, len(lines)):
            line = lines[index]
            if line.strip() and len(line) - len(line.lstrip(" \t")) <= indent:
                break
            end = index
        return end
    depth = 0
    seen_open = False
    for index in range(start, len(lines)):
        depth += lines[index].count("{") - lines[index].count("}")
        seen_open = seen_open or "{" in lines[index]
        if seen_open and depth <= 0:
            return index
    return len(lines) - 1


def symbol_chunks(code_file: CodeFile, min_lines: int) -> list[Chunk]:
    lines = code_file.text.splitlines()
    language = language_for(code_file.ext)
    starts: list[tuple[int, str, str]] = []
    for index, line in enumerate(lines):
        match = symbol_match(line, language)
        if match:
            kind, symbol = match
            starts.append((index, kind, symbol))
    chunks: list[Chunk] = []
    for idx, (start, kind, symbol) in enumerate(starts):
        end = infer_end(lines, start, starts[idx + 1][0] if idx + 1 < len(starts) else None)
        raw = "\n".join(lines[start : end + 1])
        if count_lines(raw) >= min_lines:
            chunks.append(make_chunk(code_file, kind, symbol, start + 1, end + 1, raw))
    return chunks


def window_chunks(code_file: CodeFile, min_lines: int, window_lines: int, window_step: int) -> list[Chunk]:
    useful = [(idx + 1, line) for idx, line in enumerate(code_file.text.splitlines()) if line.strip()]
    if len(useful) < min_lines:
        return []
    chunks: list[Chunk] = []
    size = min(window_lines, len(useful))
    for start in range(0, len(useful), window_step):
        subset = useful[start : start + size]
        if len(subset) < min_lines:
            continue
        raw = "\n".join(line for _, line in subset)
        chunks.append(make_chunk(code_file, "window", None, subset[0][0], subset[-1][0], raw))
        if start + size >= len(useful):
            break
    return chunks


def config_chunks(code_file: CodeFile, min_lines: int) -> list[Chunk]:
    blocks: list[Chunk] = []
    current: list[tuple[int, str]] = []
    for index, line in enumerate(code_file.text.splitlines(), start=1):
        if line.strip():
            current.append((index, line))
        elif current:
            blocks.extend(make_config_block(code_file, current, min_lines))
            current = []
    if current:
        blocks.extend(make_config_block(code_file, current, min_lines))
    return blocks


def make_config_block(code_file: CodeFile, block: list[tuple[int, str]], min_lines: int) -> list[Chunk]:
    if len(block) < min_lines:
        return []
    raw = "\n".join(line for _, line in block)
    return [make_chunk(code_file, "config", None, block[0][0], block[-1][0], raw)]


def build_chunks(files: list[CodeFile], min_lines: int, window_lines: int, window_step: int) -> list[Chunk]:
    chunks: list[Chunk] = []
    for code_file in files:
        chunks.append(file_chunk(code_file))
        symbols = symbol_chunks(code_file, min_lines)
        chunks.extend(symbols)
        if code_file.ext in CONFIG_EXTENSIONS:
            chunks.extend(config_chunks(code_file, min_lines))
        elif not symbols:
            chunks.extend(window_chunks(code_file, min_lines, window_lines, window_step))
    return chunks


def char_ngrams(text: str, n: int = 5) -> set[str]:
    text = normalize_text(text).lower()
    if not text:
        return set()
    if len(text) <= n:
        return {text}
    return {text[idx : idx + n] for idx in range(len(text) - n + 1)}


def jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def exact_pairs(chunks: list[Chunk]) -> list[Pair]:
    result: list[Pair] = []
    specs = [
        ("raw_hash", "file_exact", {"file"}),
        ("normalized_hash", "file_normalized_exact", {"file"}),
        ("normalized_hash", "symbol_exact", {"function", "class"}),
        ("normalized_hash", "config_duplicate", {"config"}),
    ]
    for attr, duplicate_type, kinds in specs:
        buckets: dict[str, list[Chunk]] = defaultdict(list)
        for chunk in chunks:
            if chunk.kind in kinds:
                buckets[getattr(chunk, attr)].append(chunk)
        for group in buckets.values():
            for left_idx, left in enumerate(group):
                for right in group[left_idx + 1 :]:
                    if left.path != right.path and left.kind == right.kind:
                        result.append(Pair(left.chunk_id, right.chunk_id, 1.0, duplicate_type))
    return result


def near_pairs(chunks: list[Chunk], threshold: float, min_lines: int, max_comparisons: int) -> tuple[list[Pair], dict[str, int]]:
    candidates = [c for c in chunks if c.kind in {"function", "class", "window", "config"} and c.line_count >= min_lines]
    grouped: dict[tuple[str, str, int], list[Chunk]] = defaultdict(list)
    for chunk in candidates:
        bucket = chunk.line_count // 20
        for offset in (-1, 0, 1):
            grouped[(chunk.ext, chunk.kind, bucket + offset)].append(chunk)

    shingle_cache = {chunk.chunk_id: char_ngrams(chunk.normalized_text) for chunk in candidates}
    seen: set[frozenset[str]] = set()
    result: list[Pair] = []
    candidate_pairs = 0
    comparisons = 0
    skipped_length = 0
    skipped_same_path = 0

    for group in grouped.values():
        unique = sorted({chunk.chunk_id: chunk for chunk in group}.values(), key=lambda item: item.chunk_id)
        for left_idx, left in enumerate(unique):
            for right in unique[left_idx + 1 :]:
                key = frozenset((left.chunk_id, right.chunk_id))
                if key in seen:
                    continue
                seen.add(key)
                candidate_pairs += 1
                if left.path == right.path:
                    skipped_same_path += 1
                    continue
                if min(left.line_count, right.line_count) / max(left.line_count, right.line_count) < 0.55:
                    skipped_length += 1
                    continue
                if comparisons >= max_comparisons:
                    return result, {
                        "candidate_pairs": candidate_pairs,
                        "jaccard_comparisons": comparisons,
                        "skipped_same_path": skipped_same_path,
                        "skipped_length": skipped_length,
                        "max_comparisons_reached": 1,
                    }
                comparisons += 1
                score = jaccard(shingle_cache[left.chunk_id], shingle_cache[right.chunk_id])
                if score >= threshold:
                    if left.kind in {"function", "class"} and right.kind in {"function", "class"}:
                        duplicate_type = "symbol_near"
                    elif left.kind == "config" or right.kind == "config":
                        duplicate_type = "config_duplicate"
                    else:
                        duplicate_type = "window_near"
                    result.append(Pair(left.chunk_id, right.chunk_id, round(score, 4), duplicate_type))
    return result, {
        "candidate_pairs": candidate_pairs,
        "jaccard_comparisons": comparisons,
        "skipped_same_path": skipped_same_path,
        "skipped_length": skipped_length,
        "max_comparisons_reached": 0,
    }


def dedupe_pairs(pairs: list[Pair]) -> list[Pair]:
    priority = {
        "file_exact": 6,
        "file_normalized_exact": 5,
        "symbol_exact": 4,
        "config_duplicate": 3,
        "symbol_near": 2,
        "window_near": 1,
    }
    best: dict[frozenset[str], Pair] = {}
    for pair in pairs:
        key = frozenset((pair.left, pair.right))
        old = best.get(key)
        if old is None or priority[pair.duplicate_type] > priority[old.duplicate_type]:
            best[key] = pair
    return list(best.values())


def path_parts(path: str) -> set[str]:
    return {part.lower() for part in Path(path).parts}


def directory(path: str, depth: int = 2) -> str:
    parent = Path(path).parent
    if parent.as_posix() in {".", ""}:
        return "."
    return Path(*parent.parts[:depth]).as_posix()


def is_test_path(path: str) -> bool:
    return bool(path_parts(path) & TEST_PARTS)


def is_prod_path(path: str) -> bool:
    return bool(path_parts(path) & PROD_PARTS)


def cross_domain(chunks: list[Chunk]) -> bool:
    return len({directory(chunk.path, 2) for chunk in chunks}) > 1


def cluster_score(chunks: list[Chunk], duplicate_type: str, similarity: float) -> float:
    score = min(30.0, sum(chunk.line_count for chunk in chunks) / 3)
    score += min(20.0, (len(chunks) - 1) * 8)
    score += similarity * 20
    if duplicate_type in {"file_exact", "symbol_exact"}:
        score += 18
    elif duplicate_type in {"file_normalized_exact", "config_duplicate"}:
        score += 12
    elif duplicate_type == "symbol_near":
        score += 10
    if any(is_prod_path(chunk.path) for chunk in chunks):
        score += 12
    if all(is_test_path(chunk.path) for chunk in chunks):
        score -= 20
    return round(max(0.0, min(100.0, score)), 1)


def priority(score: float) -> str:
    if score >= 75:
        return "high"
    if score >= 45:
        return "medium"
    return "low"


def risk(chunks: list[Chunk], duplicate_type: str) -> str:
    if duplicate_type in {"symbol_near", "window_near", "config_duplicate"}:
        return "high" if cross_domain(chunks) else "medium"
    return "medium" if cross_domain(chunks) else "low"


def action_for(chunks: list[Chunk], duplicate_type: str) -> str:
    if duplicate_type == "file_exact":
        return "remove_exact_duplicate_file"
    if duplicate_type == "symbol_exact":
        return "keep_separate_with_note" if all(is_test_path(chunk.path) for chunk in chunks) else "extract_shared_function"
    if duplicate_type == "config_duplicate":
        return "consolidate_config"
    if duplicate_type == "window_near":
        return "extract_helper"
    return "manual_review_required"


def merge_plan(chunks: list[Chunk], duplicate_type: str, action: str, risk_level: str) -> dict[str, Any]:
    if action == "extract_shared_function":
        target = f"src/shared/{chunks[0].language}_shared"
        steps = ["确认输入输出、副作用和边界条件一致。", f"抽取公共实现到 `{target}`。", "原函数保留领域入口并调用共享实现。", "补充或保留回归测试。"]
        blockers = ["合并前仍需人工确认调用方和行为契约。"]
    elif action == "consolidate_config":
        target = "shared config/template reviewed by maintainers"
        steps = ["确认重复配置不是环境分叉。", "抽公共配置模板。", "环境差异保留为 override。", "验证最终展开配置。"]
        blockers = ["配置重复可能代表不同部署环境，不能自动合并。"]
    elif action == "remove_exact_duplicate_file":
        target = "keep one canonical file after import/reference review"
        steps = ["确认文件引用、发布路径和所有权。", "选择 canonical 文件。", "拟定引用更新方案。", "运行测试和构建。"]
        blockers = ["本工具不会删除文件；只能作为人工审核建议。"]
    elif action == "extract_helper":
        target = f"src/shared/{chunks[0].language}_helper"
        steps = ["确认重复窗口不是偶然流程相似。", f"抽取最小公共 helper 到 `{target}`。", "保留原模块差异逻辑。", "运行相关测试。"]
        blockers = ["窗口近重复不能证明语义等价。"]
    else:
        target = None
        steps = ["逐行比较相同逻辑和差异逻辑。", "只抽取确认等价的最小公共逻辑。", "保留领域差异。", "补充差异测试。"]
        blockers = ["近重复或跨目录重复需要人工审核。"]
    if risk_level == "high":
        blockers.append("风险为 high，禁止直接合并。")
    return {
        "candidate_target": target,
        "steps": steps,
        "blockers": blockers,
        "validation": ["运行相关单元测试和集成测试。", "检查导入路径、公共 API、配置加载顺序和调用方行为。"],
        "requires_manual_review": True,
        "dry_run_only": True,
    }


def member(chunk: Chunk) -> dict[str, Any]:
    preview = " ".join(line.strip() for line in chunk.raw_text.splitlines() if line.strip())
    return {
        "chunk_id": chunk.chunk_id,
        "path": chunk.path,
        "language": chunk.language,
        "kind": chunk.kind,
        "symbol": chunk.symbol,
        "line_start": chunk.line_start,
        "line_end": chunk.line_end,
        "line_count": chunk.line_count,
        "preview": preview[:177] + "..." if len(preview) > 180 else preview,
    }


def build_clusters(pairs: list[Pair], chunks_by_id: dict[str, Chunk]) -> list[dict[str, Any]]:
    uf = UnionFind()
    pair_lookup: dict[frozenset[str], Pair] = {}
    for pair in pairs:
        uf.union(pair.left, pair.right)
        pair_lookup[frozenset((pair.left, pair.right))] = pair
    clusters: list[dict[str, Any]] = []
    type_rank = {"file_exact": 6, "file_normalized_exact": 5, "symbol_exact": 4, "config_duplicate": 3, "symbol_near": 2, "window_near": 1}
    for index, ids in enumerate(sorted(uf.groups()), start=1):
        cluster_pairs = [pair for key, pair in pair_lookup.items() if all(item in ids for item in key)]
        chunks = [chunks_by_id[item] for item in ids]
        duplicate_type = max((pair.duplicate_type for pair in cluster_pairs), key=lambda item: type_rank[item], default="window_near")
        similarity = round(sum(pair.similarity for pair in cluster_pairs) / len(cluster_pairs), 4) if cluster_pairs else 1.0
        score = cluster_score(chunks, duplicate_type, similarity)
        action = action_for(chunks, duplicate_type)
        risk_level = risk(chunks, duplicate_type)
        clusters.append(
            {
                "cluster_id": f"cluster_{index:03d}",
                "type": duplicate_type,
                "similarity": similarity,
                "priority": priority(score),
                "priority_score": score,
                "members": [member(chunk) for chunk in sorted(chunks, key=lambda item: (item.path, item.line_start))],
                "recommendation": {
                    "action": action,
                    "risk": risk_level,
                    "reason": recommendation_reason(duplicate_type),
                    "merge_plan": merge_plan(chunks, duplicate_type, action, risk_level),
                    "requires_manual_review": True,
                    "dry_run_only": True,
                },
            }
        )
    return sorted(clusters, key=lambda item: (-item["priority_score"], item["cluster_id"]))


def recommendation_reason(duplicate_type: str) -> str:
    return {
        "file_exact": "文件内容完全相同，但删除前必须确认引用关系和所有权。",
        "file_normalized_exact": "规范化后相同，但注释或格式可能包含意图。",
        "symbol_exact": "符号级实现相同，可考虑抽取共享实现。",
        "symbol_near": "符号级近重复，可能存在边界或领域差异。",
        "window_near": "连续逻辑片段相似，可评估是否抽 helper。",
        "config_duplicate": "配置或脚本片段重复，但环境差异需要人工确认。",
    }.get(duplicate_type, "重复证据需要人工审核。")


def directory_summary(files: list[CodeFile], clusters: list[dict[str, Any]]) -> dict[str, Any]:
    folders: dict[str, dict[str, Any]] = defaultdict(lambda: {"files_scanned": 0, "affected_files": set(), "clusters": set(), "duplicate_lines": 0, "max_priority_score": 0.0})
    for code_file in files:
        folders[directory(code_file.rel_path)]["files_scanned"] += 1
    pairs: dict[tuple[str, str], dict[str, Any]] = defaultdict(lambda: {"clusters": set(), "duplicate_lines": 0, "max_similarity": 0.0})
    for cluster in clusters:
        dirs = sorted({directory(item["path"]) for item in cluster["members"]})
        for item in cluster["members"]:
            folder = folders[directory(item["path"])]
            folder["affected_files"].add(item["path"])
            folder["clusters"].add(cluster["cluster_id"])
            folder["duplicate_lines"] += item["line_count"]
            folder["max_priority_score"] = max(folder["max_priority_score"], cluster["priority_score"])
        for left_idx, left in enumerate(dirs):
            for right in dirs[left_idx:]:
                pair = pairs[(left, right)]
                pair["clusters"].add(cluster["cluster_id"])
                pair["duplicate_lines"] += sum(item["line_count"] for item in cluster["members"] if directory(item["path"]) in {left, right})
                pair["max_similarity"] = max(pair["max_similarity"], cluster["similarity"])
    return {
        "folders": sorted(
            [
                {
                    "path": folder,
                    "files_scanned": data["files_scanned"],
                    "affected_files": len(data["affected_files"]),
                    "duplicate_clusters": len(data["clusters"]),
                    "duplicate_lines": data["duplicate_lines"],
                    "duplicate_density": round(len(data["affected_files"]) / data["files_scanned"], 4) if data["files_scanned"] else 0,
                    "max_priority_score": round(data["max_priority_score"], 1),
                }
                for folder, data in folders.items()
            ],
            key=lambda item: (-item["duplicate_clusters"], -item["duplicate_lines"], item["path"]),
        ),
        "folder_pairs": sorted(
            [
                {
                    "left": left,
                    "right": right,
                    "scope": "internal" if left == right else "cross_directory",
                    "duplicate_clusters": len(data["clusters"]),
                    "duplicate_lines": data["duplicate_lines"],
                    "max_similarity": round(data["max_similarity"], 4),
                }
                for (left, right), data in pairs.items()
            ],
            key=lambda item: (-item["duplicate_clusters"], -item["duplicate_lines"], item["left"], item["right"]),
        ),
    }


def total_unsupported_files(coverage: dict[str, Any]) -> int:
    return sum(item["files"] for item in coverage.get("unsupported_files_by_extension", []))


def quality_warnings(
    files: list[CodeFile],
    clusters: list[dict[str, Any]],
    ignored: dict[str, list[str]],
    performance: dict[str, int],
    coverage: dict[str, Any],
) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    files_scanned = len(files)
    duplicate_clusters = len(clusters)
    unsupported_count = total_unsupported_files(coverage)
    ignored_count = len(ignored.get("files", []))

    def add(code: str, message: str, suggested_action: str) -> None:
        warnings.append({"code": code, "message": message, "suggested_action": suggested_action})

    if files_scanned == 0:
        add(
            "NO_SUPPORTED_FILES",
            "No supported source/config files were scanned.",
            "Check run.include, coverage.unsupported_files_by_extension, and supported extensions before concluding there is no duplicate code.",
        )
    elif files_scanned < 3:
        add(
            "LOW_SUPPORTED_FILE_COUNT",
            f"Only {files_scanned} supported file(s) were scanned.",
            "Check coverage.supported_files_by_directory and rerun with a broader --include or additional supported extensions if needed.",
        )

    if duplicate_clusters == 0 and unsupported_count >= max(10, files_scanned * 3):
        add(
            "NO_DUPLICATES_WITH_MANY_UNSUPPORTED_FILES",
            f"No duplicate clusters were found, but {unsupported_count} unsupported file(s) were skipped by extension.",
            "Review coverage.unsupported_files_by_extension before treating the zero-result scan as complete.",
        )

    if performance.get("max_comparisons_reached") == 1:
        add(
            "MAX_COMPARISONS_REACHED",
            "The near-duplicate comparison limit was reached before all candidate pairs were checked.",
            "Increase --max-comparisons or narrow --include to a smaller source scope and rerun.",
        )

    if files and all(is_test_path(item.rel_path) for item in files):
        add(
            "ONLY_LOW_PRIORITY_PATHS_SCANNED",
            "Only tests, fixtures, or example paths were scanned.",
            "Include production source directories if the goal is production-code deduplication.",
        )

    if ignored_count >= max(10, files_scanned * 2):
        add(
            "MANY_IGNORED_FILES",
            f"{ignored_count} file(s) were ignored by exclude rules, size limits, binary detection, or missing paths.",
            "Review ignored.files and rerun with adjusted --exclude or --max-file-size-kb when appropriate.",
        )

    return warnings


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Code Dedup Report",
        "",
        "## Summary",
        "",
        f"- Schema version: {report['schema_version']}",
        f"- Tool: {report['tool']['name']} {report['tool']['version']} ({report['tool']['mode']})",
        f"- Root: `{report['run']['root']}`",
        f"- Include: {report['run']['include'] or 'all'}",
        f"- Exclude: {report['run']['exclude'] or 'defaults only'}",
        f"- Files scanned: {report['summary']['files_scanned']}",
        f"- Chunks scanned: {report['summary']['chunks_scanned']}",
        f"- Duplicate clusters: {report['summary']['duplicate_clusters']}",
        f"- High priority clusters: {report['summary']['high_priority_clusters']}",
        f"- Jaccard comparisons: {report['performance']['jaccard_comparisons']}",
        "",
        "## Quality Warnings",
        "",
    ]
    if report["quality_warnings"]:
        for warning in report["quality_warnings"]:
            lines.extend(
                [
                    f"- `{warning['code']}`: {warning['message']}",
                    f"  Suggested action: {warning['suggested_action']}",
                ]
            )
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
        "## Scan Coverage",
        "",
        f"- Scan roots: {', '.join(f'`{item}`' for item in report['coverage']['scan_roots']) or 'N/A'}",
        f"- Subdirectories seen: {len(report['coverage']['directories_seen'])}",
        f"- Ignored files: {report['summary']['files_ignored']}",
        "",
        "### Supported Files By Directory",
        "",
        "| Folder | Files |",
        "|---|---:|",
        ]
    )
    if report["coverage"]["supported_files_by_directory"]:
        for item in report["coverage"]["supported_files_by_directory"]:
            lines.append(f"| `{item['path']}` | {item['files']} |")
    else:
        lines.append("| N/A | 0 |")
    lines.extend(
        [
            "",
            "### Unsupported Files By Extension",
            "",
            "| Extension | Files |",
            "|---|---:|",
        ]
    )
    if report["coverage"]["unsupported_files_by_extension"]:
        for item in report["coverage"]["unsupported_files_by_extension"][:20]:
            lines.append(f"| `{item['extension']}` | {item['files']} |")
    else:
        lines.append("| N/A | 0 |")
    lines.extend(
        [
            "",
        "## Directory Duplicate Summary",
        "",
        "| Folder | Files | Affected | Clusters | Lines | Density |",
        "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for folder in report["directory_summary"]["folders"]:
        lines.append(f"| `{folder['path']}` | {folder['files_scanned']} | {folder['affected_files']} | {folder['duplicate_clusters']} | {folder['duplicate_lines']} | {folder['duplicate_density']:.2f} |")
    lines.extend(["", "## Duplicate Clusters", ""])
    if not report["clusters"]:
        lines.append("- No duplicate clusters found.")
    for cluster in report["clusters"]:
        rec = cluster["recommendation"]
        plan = rec["merge_plan"]
        lines.extend(
            [
                f"### {cluster['cluster_id']}",
                "",
                f"- Type: {cluster['type']}",
                f"- Similarity: {cluster['similarity']}",
                f"- Priority: {cluster['priority']} ({cluster['priority_score']})",
                f"- Action: {rec['action']}",
                f"- Risk: {rec['risk']}",
                f"- Candidate target: {plan['candidate_target'] or 'N/A'}",
                f"- Manual review: {rec['requires_manual_review']}",
                f"- Dry run only: {rec['dry_run_only']}",
                "",
                "Merge steps:",
            ]
        )
        lines.extend(f"- {step}" for step in plan["steps"])
        lines.append("")
        lines.append("Blockers:")
        lines.extend(f"- {blocker}" for blocker in plan["blockers"])
        lines.extend(["", "| File | Symbol/Kind | Lines | Preview |", "|---|---|---:|---|"])
        for item in cluster["members"]:
            symbol = item["symbol"] or item["kind"]
            preview = item["preview"].replace("|", "\\|")
            lines.append(f"| `{item['path']}` | {symbol} | {item['line_start']}-{item['line_end']} | {preview} |")
        lines.append("")
    return "\n".join(lines) + "\n"


def build_run_metadata(root: Path, args: argparse.Namespace, generated_at: str) -> dict[str, Any]:
    return {
        "root": root.as_posix(),
        "include": args.include,
        "exclude": args.exclude,
        "threshold": args.threshold,
        "min_lines": args.min_lines,
        "window_lines": args.window_lines,
        "window_step": args.window_step,
        "max_file_size_kb": args.max_file_size_kb,
        "max_comparisons": args.max_comparisons,
        "generated_at": generated_at,
    }


def build_report(args: argparse.Namespace, root: Path, files: list[CodeFile], chunks: list[Chunk], clusters: list[dict[str, Any]], ignored: dict[str, list[str]], performance: dict[str, int], coverage: dict[str, Any]) -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).isoformat()
    return {
        "schema_version": SCHEMA_VERSION,
        "tool": {
            "name": TOOL_NAME,
            "version": TOOL_VERSION,
            "mode": TOOL_MODE,
        },
        "run": build_run_metadata(root, args, generated_at),
        "summary": {
            "files_scanned": len(files),
            "files_ignored": len(ignored["files"]),
            "chunks_scanned": len(chunks),
            "duplicate_clusters": len(clusters),
            "high_priority_clusters": len([item for item in clusters if item["priority"] == "high"]),
        },
        "performance": performance,
        "coverage": coverage,
        "ignored": ignored,
        "directory_summary": directory_summary(files, clusters),
        "quality_warnings": quality_warnings(files, clusters, ignored, performance, coverage),
        "clusters": clusters,
    }


def write_reports(report: dict[str, Any], output: Path) -> tuple[Path, Path]:
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "code-dedup-report.json"
    md_path = output / "code-dedup-report.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, md_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only code duplicate scanner for OpenCode skills.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--include", nargs="*", default=[])
    parser.add_argument("--exclude", nargs="*", default=[])
    parser.add_argument("--threshold", type=float, default=0.86)
    parser.add_argument("--min-lines", type=int, default=12)
    parser.add_argument("--window-lines", type=int, default=40)
    parser.add_argument("--window-step", type=int, default=20)
    parser.add_argument("--max-file-size-kb", type=int, default=1024)
    parser.add_argument("--max-comparisons", type=int, default=200000)
    parser.add_argument("--output", default=".opencode/reports")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print(f"Root is not a directory: {root}")
        return 2
    files, ignored, coverage = scan_files(root, args.include, args.exclude, args.max_file_size_kb)
    chunks = build_chunks(files, args.min_lines, args.window_lines, args.window_step)
    exact = exact_pairs(chunks)
    near, performance = near_pairs(chunks, args.threshold, args.min_lines, args.max_comparisons)
    pairs = dedupe_pairs(exact + near)
    clusters = build_clusters(pairs, {chunk.chunk_id: chunk for chunk in chunks})
    report = build_report(args, root, files, chunks, clusters, ignored, performance, coverage)
    json_path, md_path = write_reports(report, Path(args.output))
    print(f"Code dedup scan complete: {len(files)} files, {len(chunks)} chunks, {len(clusters)} clusters.")
    print(f"JSON: {json_path}")
    print(f"Markdown: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
