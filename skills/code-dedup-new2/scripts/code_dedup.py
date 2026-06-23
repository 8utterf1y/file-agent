from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
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
TOOL_LANGUAGE = "zh-CN"
MODES = ("exact", "standard", "deep")


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
    """维护重复候选之间的连通分量。"""

    def __init__(self) -> None:
        """初始化并查集父节点表。"""
        self.parent: dict[str, str] = {}

    def find(self, item: str) -> str:
        """查找元素所在集合的根节点。"""
        self.parent.setdefault(item, item)
        if self.parent[item] != item:
            self.parent[item] = self.find(self.parent[item])
        return self.parent[item]

    def union(self, left: str, right: str) -> None:
        """合并两个元素所在的集合。"""
        root_left = self.find(left)
        root_right = self.find(right)
        if root_left != root_right:
            self.parent[root_right] = root_left

    def groups(self) -> list[list[str]]:
        """返回包含多个元素的重复簇分组。"""
        grouped: dict[str, list[str]] = defaultdict(list)
        for item in list(self.parent):
            grouped[self.find(item)].append(item)
        return [sorted(items) for items in grouped.values() if len(items) > 1]


def sha256_text(text: str) -> str:
    """计算文本的 SHA-256 哈希。"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def stable_id(prefix: str, raw: str) -> str:
    """根据原始内容生成稳定短标识。"""
    return f"{prefix}_{sha256_text(raw)[:16]}"


def normalize_text(text: str) -> str:
    """规范化空白、换行和行尾格式。"""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t\f\v]+", " ", line.rstrip()).strip() for line in text.split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def language_for(ext: str) -> str:
    """根据文件扩展名推断语言名称。"""
    return {
        ".py": "python", ".js": "javascript", ".jsx": "javascript", ".ts": "typescript",
        ".tsx": "typescript", ".go": "go", ".java": "java", ".cs": "csharp", ".cpp": "cpp",
        ".c": "c", ".h": "c", ".hpp": "cpp", ".rs": "rust", ".rb": "ruby", ".php": "php",
        ".swift": "swift", ".kt": "kotlin", ".scala": "scala", ".sh": "shell", ".sql": "sql",
        ".yaml": "yaml", ".yml": "yaml", ".json": "json", ".toml": "toml",
    }.get(ext, "text")


def should_exclude_file(rel_path: str, name: str, patterns: set[str]) -> bool:
    """判断文件是否匹配默认或用户指定的排除模式。"""
    return any(fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(rel_path, pattern) for pattern in patterns)


def should_report_ignored_file(name: str) -> bool:
    """判断被排除文件是否需要写入 ignored 报告。"""
    return not fnmatch.fnmatch(name, "*.pyc")


def rel_to_root(path: Path, root: Path) -> str:
    """尽量把路径转换为相对扫描根目录的展示路径。"""
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def resolve_scan_root(root: Path, item: str) -> Path:
    """解析 include 条目，兼容相对路径、绝对路径和上级目录。"""
    path = Path(item).expanduser()
    if path.is_absolute():
        return path.resolve()
    return (root / path).resolve()


def mode_config(mode: str, args: argparse.Namespace) -> dict[str, Any]:
    """根据运行模式计算实际使用的分析参数。"""
    if mode == "exact":
        return {
            "cost_level": "low",
            "near_duplicate_enabled": False,
            "window_near_enabled": False,
            "effective_threshold": args.threshold,
            "effective_min_lines": args.min_lines,
            "effective_window_lines": args.window_lines,
            "effective_window_step": args.window_step,
            "effective_max_comparisons": 0,
            "top_k": args.top_k or 20,
        }
    if mode == "deep":
        return {
            "cost_level": "high",
            "near_duplicate_enabled": True,
            "window_near_enabled": True,
            "effective_threshold": min(args.threshold, 0.82),
            "effective_min_lines": min(args.min_lines, 8),
            "effective_window_lines": min(args.window_lines, 30),
            "effective_window_step": min(args.window_step, 10),
            "effective_max_comparisons": max(args.max_comparisons, 1_000_000),
            "top_k": args.top_k or 100,
        }
    return {
        "cost_level": "medium",
        "near_duplicate_enabled": True,
        "window_near_enabled": True,
        "effective_threshold": args.threshold,
        "effective_min_lines": args.min_lines,
        "effective_window_lines": args.window_lines,
        "effective_window_step": args.window_step,
        "effective_max_comparisons": args.max_comparisons,
        "top_k": args.top_k or 20,
    }


def empty_performance() -> dict[str, int]:
    """返回未执行近重复分析时的性能指标。"""
    return {
        "candidate_pairs": 0,
        "jaccard_comparisons": 0,
        "skipped_same_path": 0,
        "skipped_length": 0,
        "max_comparisons_reached": 0,
    }


def candidate_files_for(scan_root: Path, root: Path, ignored: dict[str, list[str]], coverage: dict[str, Any]) -> list[Path]:
    """遍历扫描根目录，并剪枝跳过默认排除目录。"""
    if scan_root.is_file():
        return [scan_root]

    candidates: list[Path] = []
    for current, dirs, filenames in os.walk(scan_root):
        current_path = Path(current)
        kept_dirs: list[str] = []
        for dirname in dirs:
            dir_path = current_path / dirname
            if dirname in EXCLUDE_DIRS:
                ignored["directories"].append(rel_to_root(dir_path, root))
            else:
                kept_dirs.append(dirname)
                coverage["directories_seen"].append(rel_to_root(dir_path, root))
        dirs[:] = kept_dirs
        candidates.extend(current_path / filename for filename in filenames)
    return candidates


def scan_files(root: Path, include: list[str], exclude: list[str], max_file_size_kb: int) -> tuple[list[CodeFile], dict[str, list[str]], dict[str, Any]]:
    """扫描受支持的源码/配置文件，并记录覆盖面与跳过原因。"""
    ignored = {"directories": [], "files": []}
    coverage: dict[str, Any] = {
        "scan_roots": [],
        "directories_seen": [],
        "supported_files_by_directory": defaultdict(int),
        "unsupported_files_by_extension": defaultdict(int),
    }
    roots = [resolve_scan_root(root, item) for item in include] if include else [root]
    files: list[CodeFile] = []
    exclude_patterns = set(EXCLUDE_FILES) | set(exclude)

    for scan_root in roots:
        coverage["scan_roots"].append(scan_root.as_posix())
        if not scan_root.exists():
            ignored["files"].append(f"{scan_root} (missing)")
            continue
        candidates = candidate_files_for(scan_root, root, ignored, coverage)
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
    """统计非空代码行数量。"""
    return len([line for line in text.splitlines() if line.strip()])


def make_chunk(code_file: CodeFile, kind: str, symbol: str | None, start: int, end: int, raw_text: str) -> Chunk:
    """把文件片段封装为可比对的代码块。"""
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
    """为整个文件创建文件级代码块。"""
    lines = code_file.text.splitlines()
    return make_chunk(code_file, "file", None, 1, max(1, len(lines)), code_file.text)


def symbol_match(line: str, language: str) -> tuple[str, str] | None:
    """识别一行是否是函数、类或类似符号入口。"""
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
    """根据缩进或括号深度推断符号代码块结束行。"""
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
    """从文件中提取函数、类等符号级代码块。"""
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
    """在无法提取符号时生成滑动窗口代码块。"""
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
    """按空行切分配置或脚本文件中的连续块。"""
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
    """把一个配置连续块转换为代码块。"""
    if len(block) < min_lines:
        return []
    raw = "\n".join(line for _, line in block)
    return [make_chunk(code_file, "config", None, block[0][0], block[-1][0], raw)]


def append_unique(chunks: list[Chunk], seen: set[str], new_chunks: list[Chunk]) -> None:
    """追加未出现过的代码块。"""
    for chunk in new_chunks:
        if chunk.chunk_id not in seen:
            chunks.append(chunk)
            seen.add(chunk.chunk_id)


def build_chunks(files: list[CodeFile], min_lines: int, window_lines: int, window_step: int, mode: str, window_near_enabled: bool) -> list[Chunk]:
    """按运行模式构建文件级、符号级、配置级和窗口级代码块。"""
    chunks: list[Chunk] = []
    seen: set[str] = set()
    for code_file in files:
        append_unique(chunks, seen, [file_chunk(code_file)])
        symbols = symbol_chunks(code_file, min_lines)
        append_unique(chunks, seen, symbols)
        if code_file.ext in CONFIG_EXTENSIONS:
            append_unique(chunks, seen, config_chunks(code_file, min_lines))
        elif window_near_enabled and (mode == "deep" or not symbols):
            append_unique(chunks, seen, window_chunks(code_file, min_lines, window_lines, window_step))
    return chunks


def char_ngrams(text: str, n: int = 5) -> set[str]:
    """把规范化文本转换为字符 n-gram 集合。"""
    text = normalize_text(text).lower()
    if not text:
        return set()
    if len(text) <= n:
        return {text}
    return {text[idx : idx + n] for idx in range(len(text) - n + 1)}


def jaccard(left: set[str], right: set[str]) -> float:
    """计算两个集合的 Jaccard 相似度。"""
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def exact_pairs(chunks: list[Chunk]) -> list[Pair]:
    """基于哈希查找精确重复和规范化重复。"""
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
    """基于分桶和 Jaccard 相似度查找近重复代码块。"""
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
    """对同一代码块对保留优先级最高的重复类型。"""
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
    """提取路径片段并统一转为小写。"""
    return {part.lower() for part in Path(path).parts}


def directory(path: str, depth: int = 2) -> str:
    """按指定深度返回文件所属目录。"""
    parent = Path(path).parent
    if parent.as_posix() in {".", ""}:
        return "."
    return Path(*parent.parts[:depth]).as_posix()


def is_test_path(path: str) -> bool:
    """判断路径是否属于测试、夹具或示例目录。"""
    return bool(path_parts(path) & TEST_PARTS)


def is_prod_path(path: str) -> bool:
    """判断路径是否看起来属于生产源码目录。"""
    return bool(path_parts(path) & PROD_PARTS)


def role_hint(path: str, ext: str) -> str:
    """根据路径和扩展名推断代码角色。"""
    parts = path_parts(path)
    if ext in CONFIG_EXTENSIONS:
        return "config"
    if {"fixture", "fixtures"} & parts:
        return "fixture"
    if {"example", "examples"} & parts:
        return "example"
    if {"test", "tests", "__tests__"} & parts:
        return "test"
    if is_prod_path(path):
        return "production"
    return "unknown"


def cross_domain(chunks: list[Chunk]) -> bool:
    """判断重复簇是否跨越多个顶层/二级目录。"""
    return len({directory(chunk.path, 2) for chunk in chunks}) > 1


def cluster_score(chunks: list[Chunk], duplicate_type: str, similarity: float) -> float:
    """根据重复规模、类型、相似度和路径角色计算优先级分。"""
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
    """把优先级分转换为 high、medium 或 low。"""
    if score >= 75:
        return "high"
    if score >= 45:
        return "medium"
    return "low"


def member(chunk: Chunk) -> dict[str, Any]:
    """把代码块转换为报告中的成员记录。"""
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
        "role_hint": role_hint(chunk.path, chunk.ext),
    }


def evidence_strength(duplicate_type: str, similarity: float) -> str:
    """根据重复类型和相似度评估证据强度。"""
    if duplicate_type in {"file_exact", "symbol_exact"}:
        return "strong"
    if duplicate_type == "file_normalized_exact":
        return "strong" if similarity >= 0.99 else "moderate"
    if duplicate_type == "config_duplicate":
        return "moderate"
    if similarity >= 0.93:
        return "strong"
    if similarity >= 0.86:
        return "moderate"
    return "weak"


def review_hints(chunks: list[Chunk], duplicate_type: str) -> dict[str, Any]:
    """生成中性的 AI 复核提示，不输出合并建议。"""
    flags: list[str] = [duplicate_type]
    if duplicate_type in {"symbol_near", "window_near"}:
        flags.append("near_duplicate")
    if cross_domain(chunks):
        flags.append("cross_directory")
    roles = {role_hint(chunk.path, chunk.ext) for chunk in chunks}
    if duplicate_type == "config_duplicate" or "config" in roles:
        flags.append("config_candidate")
    if roles & {"test", "fixture", "example"}:
        flags.append("low_priority_path")
    if roles & {"production"}:
        flags.append("production_path")
    if any(chunk.kind == "file" for chunk in chunks):
        flags.append("file_level_candidate")

    must_check = [
        "imports",
        "references",
        "callers",
        "semantic_equivalence",
        "module_boundary",
        "tests",
    ]
    if duplicate_type == "config_duplicate" or "config" in roles:
        must_check.extend(["environment_differences", "load_order", "deployment_overrides"])
    if any(chunk.kind == "file" for chunk in chunks):
        must_check.extend(["file_ownership", "published_path"])

    return {
        "flags": sorted(set(flags)),
        "must_check": sorted(set(must_check)),
        "not_checked_by_script": [
            "semantic_equivalence",
            "runtime_behavior",
            "import_reference_callers",
            "public_api_impact",
            "test_coverage",
            "security_permission_deployment_impact",
        ],
        "paths_to_review": sorted({chunk.path for chunk in chunks}),
    }


def evidence_tables(chunks: list[Chunk], cluster_pairs: list[Pair]) -> dict[str, Any]:
    """生成重复簇的成员、配对和目录证据表。"""
    return {
        "members": [member(chunk) for chunk in sorted(chunks, key=lambda item: (item.path, item.line_start))],
        "pairs": [
            {
                "left_chunk_id": pair.left,
                "right_chunk_id": pair.right,
                "similarity": pair.similarity,
                "type": pair.duplicate_type,
            }
            for pair in sorted(cluster_pairs, key=lambda item: (item.duplicate_type, item.left, item.right))
        ],
        "directories": sorted({directory(chunk.path) for chunk in chunks}),
    }


def build_clusters(pairs: list[Pair], chunks_by_id: dict[str, Chunk]) -> list[dict[str, Any]]:
    """把重复配对合并为只包含证据和复核提示的重复簇。"""
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
        strength = evidence_strength(duplicate_type, similarity)
        clusters.append(
            {
                "cluster_id": f"cluster_{index:03d}",
                "type": duplicate_type,
                "similarity": similarity,
                "evidence_strength": strength,
                "priority": priority(score),
                "priority_score": score,
                "requires_ai_review": True,
                "review_hints": review_hints(chunks, duplicate_type),
                "members": [member(chunk) for chunk in sorted(chunks, key=lambda item: (item.path, item.line_start))],
                "evidence_tables": evidence_tables(chunks, cluster_pairs),
            }
        )
    return sorted(clusters, key=lambda item: (-item["priority_score"], item["cluster_id"]))


def directory_summary(files: list[CodeFile], clusters: list[dict[str, Any]]) -> dict[str, Any]:
    """按目录汇总扫描文件数、受影响文件数和重复密度。"""
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
    """统计因扩展名不支持而跳过的文件数量。"""
    return sum(item["files"] for item in coverage.get("unsupported_files_by_extension", []))


def quality_warnings(
    files: list[CodeFile],
    clusters: list[dict[str, Any]],
    ignored: dict[str, list[str]],
    performance: dict[str, int],
    coverage: dict[str, Any],
    run: dict[str, Any],
) -> list[dict[str, str]]:
    """根据覆盖面和性能指标生成报告质量预警。"""
    warnings: list[dict[str, str]] = []
    files_scanned = len(files)
    duplicate_clusters = len(clusters)
    unsupported_count = total_unsupported_files(coverage)
    ignored_count = len(ignored.get("files", []))
    mode = run["mode"]

    def add(code: str, message: str, suggested_action: str) -> None:
        """追加一条质量预警。"""
        warnings.append({"code": code, "message": message, "suggested_action": suggested_action})

    if mode == "exact":
        add(
            "EXACT_MODE_SKIPPED_NEAR_DUPLICATES",
            "当前为 exact 快速模式，仅检测完全重复和规范化完全重复，未执行近重复分析。",
            "如需分析近重复函数、近重复配置或复制粘贴式逻辑，请使用 --mode standard 或 --mode deep。",
        )

    if files_scanned == 0:
        add(
            "NO_SUPPORTED_FILES",
            "没有扫描到受支持的源码或配置文件。",
            "先检查 run.include、coverage.unsupported_files_by_extension 和支持的扩展名，再判断是否需要重跑。",
        )
    elif files_scanned < 3:
        add(
            "LOW_SUPPORTED_FILE_COUNT",
            f"本次只扫描到 {files_scanned} 个受支持文件。",
            "检查 coverage.supported_files_by_directory；必要时扩大 --include 或增加受支持扩展名后重跑。",
        )

    if duplicate_clusters == 0 and unsupported_count >= max(10, files_scanned * 3):
        add(
            "NO_DUPLICATES_WITH_MANY_UNSUPPORTED_FILES",
            f"没有发现重复簇，但有 {unsupported_count} 个文件因扩展名不受支持而跳过。",
            "在把零结果视为完整结论前，先复核 coverage.unsupported_files_by_extension。",
        )

    if performance.get("max_comparisons_reached") == 1:
        add(
            "MAX_COMPARISONS_REACHED",
            "近重复候选尚未全部比对完就达到了比较上限。",
            "提高 --max-comparisons，或缩小 --include 范围后重跑。",
        )
        if mode == "deep":
            add(
                "DEEP_MODE_MAX_COMPARISONS_REACHED",
                "深度模式仍达到近重复比较上限，结果可能不完整。",
                "缩小 --include 范围，或提高 --max-comparisons 后重跑。",
            )

    if files and all(is_test_path(item.rel_path) for item in files):
        add(
            "ONLY_LOW_PRIORITY_PATHS_SCANNED",
            "本次只扫描到 tests、fixtures 或 examples 等低优先级路径。",
            "如果目标是生产代码去重，请 include 生产源码目录后重跑。",
        )

    if ignored_count >= max(10, files_scanned * 2):
        add(
            "MANY_IGNORED_FILES",
            f"有 {ignored_count} 个文件因排除规则、大小限制、二进制检测或路径缺失被忽略。",
            "复核 ignored.files；必要时调整 --exclude 或 --max-file-size-kb 后重跑。",
        )

    return warnings


def markdown_cell(value: Any) -> str:
    """转义 Markdown 表格单元格中的特殊字符。"""
    text = str(value if value is not None else "N/A")
    return text.replace("|", "\\|").replace("\n", "<br>")


def yes_no(value: bool) -> str:
    """把布尔值渲染为中文是否。"""
    return "是" if value else "否"


def cluster_count_by_priority(clusters: list[dict[str, Any]], priority_name: str) -> int:
    """统计指定优先级的重复簇数量。"""
    return len([cluster for cluster in clusters if cluster["priority"] == priority_name])


def render_markdown(report: dict[str, Any]) -> str:
    """把 JSON 报告渲染为中文 Markdown 表格报告。"""
    run = report["run"]
    summary = report["summary"]
    performance = report["performance"]
    lines = [
        "# 代码重复检测报告",
        "",
        "## 1. 扫描概览",
        "",
        "| 指标 | 数值 |",
        "|---|---:|",
        f"| schema_version | {report['schema_version']} |",
        f"| 工具 | {report['tool']['name']} {report['tool']['version']} |",
        f"| 模式 | {report['tool']['mode']} |",
        f"| 语言 | {report['tool']['language']} |",
        f"| 运行模式 | {run['mode']} |",
        f"| 成本等级 | {run['cost_level']} |",
        f"| 是否检测近重复 | {yes_no(run['near_duplicate_enabled'])} |",
        f"| 是否检测窗口级片段 | {yes_no(run['window_near_enabled'])} |",
        f"| 有效相似度阈值 | {run['effective_threshold']} |",
        f"| 有效最小行数 | {run['effective_min_lines']} |",
        f"| 有效最大比较次数 | {run['effective_max_comparisons']} |",
        f"| 展示上限 | {run['top_k']} |",
        f"| 扫描根目录 | `{markdown_cell(run['root'])}` |",
        f"| include | {markdown_cell(run['include'] or 'all')} |",
        f"| exclude | {markdown_cell(run['exclude'] or 'defaults only')} |",
        f"| 扫描文件数 | {summary['files_scanned']} |",
        f"| 忽略文件数 | {summary['files_ignored']} |",
        f"| 分析代码块数 | {summary['chunks_scanned']} |",
        f"| 重复簇数量 | {summary['duplicate_clusters']} |",
        f"| 高优先级重复簇 | {summary['high_priority_clusters']} |",
        f"| Jaccard 比对次数 | {performance['jaccard_comparisons']} |",
        "",
        "## 2. 质量预警",
        "",
        "| 预警码 | 说明 | 建议 |",
        "|---|---|---|",
    ]
    if report["quality_warnings"]:
        for warning in report["quality_warnings"]:
            lines.append(f"| `{warning['code']}` | {markdown_cell(warning['message'])} | {markdown_cell(warning['suggested_action'])} |")
    else:
        lines.append("| 无 | 未发现质量预警。 | 可继续复核重复簇证据。 |")

    lines.extend(
        [
            "",
            "## 3. 扫描覆盖",
            "",
            "| 目录 | 可分析文件数 |",
            "|---|---:|",
        ]
    )
    if report["coverage"]["supported_files_by_directory"]:
        for item in report["coverage"]["supported_files_by_directory"]:
            lines.append(f"| `{markdown_cell(item['path'])}` | {item['files']} |")
    else:
        lines.append("| N/A | 0 |")

    lines.extend(["", "| 未支持扩展名 | 文件数 |", "|---|---:|"])
    if report["coverage"]["unsupported_files_by_extension"]:
        for item in report["coverage"]["unsupported_files_by_extension"][:20]:
            lines.append(f"| `{markdown_cell(item['extension'])}` | {item['files']} |")
    else:
        lines.append("| 无 | 0 |")

    lines.extend(
        [
            "",
            "## 4. 重复项汇总",
            "",
            "| 簇ID | 类型 | 优先级 | 证据强度 | 相似度 | 涉及文件数 | 需要 AI 复核 |",
            "|---|---|---|---|---:|---:|---|",
        ]
    )
    if report["clusters"]:
        for cluster in report["clusters"][: run["top_k"]]:
            lines.append(
                f"| `{cluster['cluster_id']}` | {cluster['type']} | {cluster['priority']} | "
                f"{cluster['evidence_strength']} | {cluster['similarity']} | {len(cluster['members'])} | "
                f"{yes_no(cluster['requires_ai_review'])} |"
            )
    else:
        lines.append("| 无 | 无 | 无 | 无 | 0 | 0 | 否 |")

    lines.extend(
        [
            "",
            "## 5. 目录级重复",
            "",
            "| 目录 | 扫描文件 | 受影响文件 | 重复簇 | 重复行数 | 密度 |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for folder in report["directory_summary"]["folders"]:
        lines.append(
            f"| `{markdown_cell(folder['path'])}` | {folder['files_scanned']} | {folder['affected_files']} | "
            f"{folder['duplicate_clusters']} | {folder['duplicate_lines']} | {folder['duplicate_density']:.2f} |"
        )

    detail_clusters = [cluster for cluster in report["clusters"] if cluster["priority"] == "high"]
    if not detail_clusters:
        detail_clusters = [cluster for cluster in report["clusters"] if cluster["priority"] == "medium"][:5]
    detail_clusters = detail_clusters[: run["top_k"]]

    lines.extend(["", "## 6. 高/中优先级重复项详情", ""])
    if not detail_clusters:
        lines.append("- 本次扫描未发现需要默认展开的高/中优先级重复簇。")

    for cluster in detail_clusters:
        hints = cluster["review_hints"]
        lines.extend(
            [
                f"### {cluster['cluster_id']}",
                "",
                "#### 6.1 基本判断",
                "",
                "| 字段 | 内容 |",
                "|---|---|",
                f"| 重复类型 | {cluster['type']} |",
                f"| 相似度 | {cluster['similarity']} |",
                f"| 证据强度 | {cluster['evidence_strength']} |",
                f"| 优先级 | {cluster['priority']} ({cluster['priority_score']}) |",
                f"| 需要 AI 复核 | {yes_no(cluster['requires_ai_review'])} |",
                "",
                "#### 6.2 证据表",
                "",
                "| 文件 | 符号/代码块 | 行号 | 角色 | 预览 |",
                "|---|---|---:|---|---|",
            ]
        )
        for item in cluster["members"]:
            symbol = item["symbol"] or item["kind"]
            lines.append(
                f"| `{markdown_cell(item['path'])}` | {markdown_cell(symbol)} | "
                f"{item['line_start']}-{item['line_end']} | {item['role_hint']} | {markdown_cell(item['preview'])} |"
            )

        lines.extend(["", "#### 6.3 复核提示", ""])
        lines.extend(f"- 标记：`{markdown_cell(item)}`" for item in hints["flags"])
        lines.extend(["", "必须继续检查："])
        lines.extend(f"- `{markdown_cell(item)}`" for item in hints["must_check"])
        lines.extend(["", "脚本未检查内容："])
        lines.extend(f"- `{markdown_cell(item)}`" for item in hints["not_checked_by_script"])
        lines.append("")

    low_clusters = [cluster for cluster in report["clusters"] if cluster["priority"] == "low"]
    lines.extend(
        [
            "## 7. 低优先级重复项",
            "",
            f"- 低优先级重复簇数量：{len(low_clusters)}",
            "- 默认不展开低优先级重复项详情；如需复核，请指定具体重复簇编号或使用更大的 `--top-k` 重新生成报告。",
            "",
            "| 类型 | 数量 |",
            "|---|---:|",
        ]
    )
    low_by_type: dict[str, int] = defaultdict(int)
    for cluster in low_clusters:
        low_by_type[cluster["type"]] += 1
    if low_by_type:
        for duplicate_type, count in sorted(low_by_type.items()):
            lines.append(f"| {duplicate_type} | {count} |")
    else:
        lines.append("| 无 | 0 |")

    lines.extend(
        [
            "",
            "## 8. 下一步复核建议",
            "",
            f"- 高优先级重复簇：{cluster_count_by_priority(report['clusters'], 'high')} 个。",
            f"- 中优先级重复簇：{cluster_count_by_priority(report['clusters'], 'medium')} 个。",
            f"- 低优先级重复簇：{cluster_count_by_priority(report['clusters'], 'low')} 个。",
            "- 若用户关注某个重复簇，优先读取已有 JSON 报告并只复核该重复簇涉及的源码和引用。",
            "- 脚本不判断是否合并；AI 需要读取源码、调用关系和测试后再给出建议。",
            "- 若用户批准修改，进入单独补丁/重构工作流，重新读取源码并生成最小补丁计划。",
            "",
        ]
    )

    lines.append("## 9. 当前操作状态")
    lines.append("")
    lines.append("- 本报告仅由只读扫描生成；当前未修改任何文件。")
    return "\n".join(lines) + "\n"


def build_run_metadata(root: Path, args: argparse.Namespace, config: dict[str, Any], generated_at: str) -> dict[str, Any]:
    """记录本次扫描的参数和生成时间。"""
    return {
        "root": root.as_posix(),
        "include": args.include,
        "exclude": args.exclude,
        "mode": args.mode,
        "cost_level": config["cost_level"],
        "near_duplicate_enabled": config["near_duplicate_enabled"],
        "window_near_enabled": config["window_near_enabled"],
        "threshold": args.threshold,
        "effective_threshold": config["effective_threshold"],
        "min_lines": args.min_lines,
        "effective_min_lines": config["effective_min_lines"],
        "window_lines": args.window_lines,
        "effective_window_lines": config["effective_window_lines"],
        "window_step": args.window_step,
        "effective_window_step": config["effective_window_step"],
        "max_file_size_kb": args.max_file_size_kb,
        "max_comparisons": args.max_comparisons,
        "effective_max_comparisons": config["effective_max_comparisons"],
        "top_k": config["top_k"],
        "generated_at": generated_at,
    }


def build_report(args: argparse.Namespace, config: dict[str, Any], root: Path, files: list[CodeFile], chunks: list[Chunk], clusters: list[dict[str, Any]], ignored: dict[str, list[str]], performance: dict[str, int], coverage: dict[str, Any]) -> dict[str, Any]:
    """组装最终 JSON 报告结构。"""
    generated_at = datetime.now(timezone.utc).isoformat()
    run = build_run_metadata(root, args, config, generated_at)
    return {
        "schema_version": SCHEMA_VERSION,
        "tool": {
            "name": TOOL_NAME,
            "version": TOOL_VERSION,
            "mode": TOOL_MODE,
            "language": TOOL_LANGUAGE,
        },
        "run": run,
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
        "quality_warnings": quality_warnings(files, clusters, ignored, performance, coverage, run),
        "directory_summary": directory_summary(files, clusters),
        "clusters": clusters,
    }


def write_reports(report: dict[str, Any], output: Path) -> tuple[Path, Path]:
    """把 JSON 和 Markdown 报告写入输出目录。"""
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "code-dedup-report.json"
    md_path = output / "code-dedup-report.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, md_path


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="Read-only code duplicate scanner for OpenCode skills.",
        epilog=(
            "Examples:\n"
            "  python scripts/code_dedup.py --root . --mode exact --output .opencode/reports\n"
            "  python scripts/code_dedup.py --root . --include src packages --mode standard\n"
            "  python scripts/code_dedup.py --root . --mode deep --top-k 100"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--root", default=".", help="扫描根目录，默认当前目录。")
    parser.add_argument("--include", nargs="*", default=[], help="只扫描指定目录或文件；不传表示扫描 root 下全部可分析文件。")
    parser.add_argument("--exclude", nargs="*", default=[], help="额外排除的文件名、路径或 glob 模式。")
    parser.add_argument("--mode", choices=MODES, default="standard", help="运行模式：exact 快速精确重复，standard 默认分析，deep 高召回分析。")
    parser.add_argument("--threshold", type=float, default=0.86, help="近重复 Jaccard 相似度阈值，standard 默认 0.86。")
    parser.add_argument("--min-lines", type=int, default=12, help="参与符号、配置或窗口分析的最小非空行数。")
    parser.add_argument("--window-lines", type=int, default=40, help="窗口级近重复分析的窗口行数。")
    parser.add_argument("--window-step", type=int, default=20, help="窗口级近重复分析的滑动步长。")
    parser.add_argument("--max-file-size-kb", type=int, default=1024, help="单文件最大读取大小，超过后跳过。")
    parser.add_argument("--max-comparisons", type=int, default=200000, help="近重复 Jaccard 最大比较次数。")
    parser.add_argument("--top-k", type=int, default=None, help="Markdown 报告默认展开或展示的重复簇数量；exact/standard 默认 20，deep 默认 100。")
    parser.add_argument("--output", default=".opencode/reports", help="报告输出目录，会写入 JSON 和 Markdown。")
    return parser.parse_args()


def main() -> int:
    """执行扫描、比对、聚类和报告生成流程。"""
    args = parse_args()
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print(f"Root is not a directory: {root}")
        return 2
    config = mode_config(args.mode, args)
    files, ignored, coverage = scan_files(root, args.include, args.exclude, args.max_file_size_kb)
    chunks = build_chunks(
        files,
        config["effective_min_lines"],
        config["effective_window_lines"],
        config["effective_window_step"],
        args.mode,
        config["window_near_enabled"],
    )
    exact = exact_pairs(chunks)
    near: list[Pair] = []
    performance = empty_performance()
    if config["near_duplicate_enabled"]:
        near, performance = near_pairs(
            chunks,
            config["effective_threshold"],
            config["effective_min_lines"],
            config["effective_max_comparisons"],
        )
    pairs = dedupe_pairs(exact + near)
    clusters = build_clusters(pairs, {chunk.chunk_id: chunk for chunk in chunks})
    report = build_report(args, config, root, files, chunks, clusters, ignored, performance, coverage)
    json_path, md_path = write_reports(report, Path(args.output))
    print(f"Code dedup scan complete: {len(files)} files, {len(chunks)} chunks, {len(clusters)} clusters.")
    print(f"JSON: {json_path}")
    print(f"Markdown: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
