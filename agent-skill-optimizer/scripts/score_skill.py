#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path
from typing import Any


DIMENSIONS = [
    "trigger_clarity",
    "scope_control",
    "procedural_usefulness",
    "output_specificity",
    "context_efficiency",
    "safety",
    "testability",
    "maintainability",
    "cross_agent_portability",
]


def load_lint_module() -> Any:
    path = Path(__file__).with_name("lint_skill.py")
    spec = importlib.util.spec_from_file_location("lint_skill_local", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load lint_skill.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_skill(skill_dir: Path) -> str:
    path = skill_dir / "SKILL.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def has_any(text: str, terms: list[str]) -> bool:
    lower = text.lower()
    return any(term.lower() in lower for term in terms)


def score_dimension(text: str, skill_dir: Path, lint_result: dict[str, Any], name: str) -> tuple[int, list[str]]:
    suggestions: list[str] = []
    score = 3

    if name == "trigger_clarity":
        desc_len = lint_result.get("frontmatter", {}).get("description_length", 0)
        if 120 <= desc_len <= 600 and has_any(text, ["when to use", "non-trigger", "when not"]):
            score = 4
        if has_any(text, ["should-trigger", "should-not-trigger", "near-miss"]):
            score = 5
        if desc_len < 80:
            score = 2
            suggestions.append("Expand the frontmatter description with concrete trigger phrases.")
    elif name == "scope_control":
        if has_any(text, ["when not", "non-trigger", "do not use"]):
            score = 4
        if has_any(text, ["prune", "split", "references", "templates"]):
            score = 5
        else:
            suggestions.append("Add explicit non-goals and context-control guidance.")
    elif name == "procedural_usefulness":
        numbered_steps = len(re.findall(r"^\d+\.", text, flags=re.MULTILINE))
        score = 5 if numbered_steps >= 6 else 4 if numbered_steps >= 3 else 2
        if score < 4:
            suggestions.append("Add a concrete step-by-step workflow.")
    elif name == "output_specificity":
        if has_any(text, ["output format", "report", "json", "template"]):
            score = 4
        if (skill_dir / "templates").exists():
            score = min(5, score + 1)
        if score < 4:
            suggestions.append("Define expected output sections or templates.")
    elif name == "context_efficiency":
        length = len(text.split())
        if length <= 700 and (skill_dir / "references").exists():
            score = 5
        elif length <= 1200:
            score = 4
        else:
            score = 2
            suggestions.append("Move long guidance into references or templates.")
    elif name == "safety":
        if has_any(text, ["destructive", "confirmation", "delete", "overwrite", "move", "rename"]):
            score = 5
        elif lint_result.get("warnings"):
            score = 2
            suggestions.append("Clarify destructive-operation and permission rules.")
        else:
            score = 3
    elif name == "testability":
        if has_any(text, ["eval", "lint", "security", "test"]):
            score = 4
        if (skill_dir / "scripts").exists():
            score = min(5, score + 1)
        if score < 4:
            suggestions.append("Add trigger and output eval guidance.")
    elif name == "maintainability":
        dirs = sum(1 for child in skill_dir.iterdir() if child.is_dir())
        score = 5 if dirs >= 2 else 3
        if "resource navigation" not in text.lower():
            suggestions.append("Add resource navigation so future agents load only relevant files.")
    elif name == "cross_agent_portability":
        if has_any(text, ["codex", "chatgpt", "claude", "opencode", "cursor", "gemini"]):
            score = 5
        else:
            score = 3
            suggestions.append("Name supported agent platforms or add cross-platform notes.")

    return score, suggestions


def score_skill(skill_dir: Path) -> dict[str, Any]:
    lint_module = load_lint_module()
    lint_result = lint_module.lint_skill(skill_dir)
    text = read_skill(skill_dir)
    scores: dict[str, int] = {}
    suggestions: list[str] = []

    for dimension in DIMENSIONS:
        score, dimension_suggestions = score_dimension(text, skill_dir, lint_result, dimension)
        scores[dimension] = score
        suggestions.extend(dimension_suggestions)

    if lint_result.get("errors"):
        suggestions.append("Fix lint errors before packaging.")
    if lint_result.get("warnings"):
        suggestions.append("Review lint warnings and document intentional exceptions.")

    average = round(sum(scores.values()) / len(scores), 2)
    return {
        "ok": lint_result.get("ok", False),
        "skill_dir": str(skill_dir),
        "average_score": average,
        "scores": scores,
        "lint": lint_result,
        "suggestions": sorted(set(suggestions)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Score an agent skill directory.")
    parser.add_argument("skill_dir", help="Path to a skill directory")
    args = parser.parse_args()
    result = score_skill(Path(args.skill_dir))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
