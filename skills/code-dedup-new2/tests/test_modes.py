from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "code_dedup.py"
SAMPLE_PROJECT = SKILL_ROOT / "tests" / "sample_project"
SKILL_MD = SKILL_ROOT / "SKILL.md"


def run_scan(tmp_path: Path, mode: str) -> dict:
    output = tmp_path / mode
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--root",
            str(SAMPLE_PROJECT),
            "--mode",
            mode,
            "--output",
            str(output),
        ],
        cwd=REPO_ROOT,
        check=True,
    )
    assert (output / "code-dedup-report.json").exists()
    assert (output / "code-dedup-report.md").exists()
    return json.loads((output / "code-dedup-report.json").read_text(encoding="utf-8"))


def source_hashes() -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(SAMPLE_PROJECT.rglob("*")):
        if path.is_file():
            rel_path = path.relative_to(SAMPLE_PROJECT).as_posix()
            result[rel_path] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def cluster_types(report: dict) -> set[str]:
    return {cluster["type"] for cluster in report["clusters"]}


def cluster_paths(report: dict) -> set[str]:
    paths: set[str] = set()
    for cluster in report["clusters"]:
        for member in cluster["members"]:
            paths.add(member["path"])
    return paths


def test_skill_frontmatter_format() -> None:
    text = SKILL_MD.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    end = text.find("\n---\n", 4)
    assert end != -1
    frontmatter = text[4:end]
    body = text[end + len("\n---\n") :]
    assert "\nname: code-dedup\n" in f"\n{frontmatter}\n"
    assert "description:" in frontmatter
    assert body.lstrip().startswith("# Code Dedup")


def test_exact_mode_runs(tmp_path: Path) -> None:
    report = run_scan(tmp_path, "exact")
    assert report["run"]["mode"] == "exact"
    assert report["run"]["cost_level"] == "low"
    assert report["run"]["near_duplicate_enabled"] is False
    assert report["run"]["window_near_enabled"] is False
    assert report["performance"]["jaccard_comparisons"] == 0
    assert report["performance"]["candidate_pairs"] == 0


def test_exact_mode_detects_file_exact(tmp_path: Path) -> None:
    report = run_scan(tmp_path, "exact")
    assert cluster_types(report) & {"file_exact", "file_normalized_exact"}
    paths = cluster_paths(report)
    assert "src/common/exact_copy_a.py" in paths
    assert "src/common/exact_copy_b.py" in paths


def test_standard_mode_runs_near_analysis(tmp_path: Path) -> None:
    report = run_scan(tmp_path, "standard")
    assert report["run"]["mode"] == "standard"
    assert report["run"]["near_duplicate_enabled"] is True
    assert "jaccard_comparisons" in report["performance"]
    assert report["performance"]["candidate_pairs"] >= 0


def test_clusters_are_evidence_only(tmp_path: Path) -> None:
    report = run_scan(tmp_path, "standard")
    assert report["clusters"]
    for cluster in report["clusters"]:
        assert "recommendation" not in cluster
        assert "merge_plan" not in cluster
        assert "risk" not in cluster
        assert "requires_ai_review" in cluster
        assert "review_hints" in cluster
        assert "must_check" in cluster["review_hints"]
        assert "semantic_equivalence" in cluster["review_hints"]["must_check"]


def test_deep_mode_uses_high_recall_settings(tmp_path: Path) -> None:
    report = run_scan(tmp_path, "deep")
    assert report["run"]["mode"] == "deep"
    assert report["run"]["cost_level"] == "high"
    assert report["run"]["near_duplicate_enabled"] is True
    assert report["run"]["effective_max_comparisons"] >= 1_000_000
    assert report["run"]["effective_min_lines"] <= 8


def test_markdown_includes_mode(tmp_path: Path) -> None:
    output = tmp_path / "standard"
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--root",
            str(SAMPLE_PROJECT),
            "--mode",
            "standard",
            "--output",
            str(output),
        ],
        cwd=REPO_ROOT,
        check=True,
    )
    markdown = (output / "code-dedup-report.md").read_text(encoding="utf-8")
    assert "运行模式" in markdown
    assert "成本等级" in markdown
    assert "是否检测近重复" in markdown


def test_markdown_is_evidence_report(tmp_path: Path) -> None:
    output = tmp_path / "standard"
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--root",
            str(SAMPLE_PROJECT),
            "--mode",
            "standard",
            "--output",
            str(output),
        ],
        cwd=REPO_ROOT,
        check=True,
    )
    markdown = (output / "code-dedup-report.md").read_text(encoding="utf-8")
    assert "需要 AI 复核" in markdown
    assert "复核提示" in markdown
    assert "脚本未检查内容" in markdown
    assert "建议动作" not in markdown
    assert "合并或保留建议" not in markdown
    assert "候选目标" not in markdown


def test_exact_mode_warning(tmp_path: Path) -> None:
    report = run_scan(tmp_path, "exact")
    codes = {warning["code"] for warning in report["quality_warnings"]}
    assert "EXACT_MODE_SKIPPED_NEAR_DUPLICATES" in codes


def test_no_source_mutation(tmp_path: Path) -> None:
    before = source_hashes()
    for mode in ("exact", "standard", "deep"):
        run_scan(tmp_path, mode)
    assert source_hashes() == before
