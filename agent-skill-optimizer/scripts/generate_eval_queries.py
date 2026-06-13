#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


DEFAULT_PLATFORMS = ["Codex", "ChatGPT", "Claude", "OpenCode", "Cursor", "Gemini CLI"]


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    data: dict[str, str] = {}
    for line in text[4:end].strip().splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def words_from_text(text: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", text)
    seen: set[str] = set()
    result: list[str] = []
    for word in words:
        lower = word.lower()
        if lower not in seen:
            seen.add(lower)
            result.append(word)
    return result[:12]


def generate_queries(source: Path) -> dict[str, Any]:
    text = source.read_text(encoding="utf-8", errors="replace")
    frontmatter = parse_frontmatter(text)
    name = frontmatter.get("name") or source.stem.replace("_", "-").lower()
    description = frontmatter.get("description", "")
    keywords = words_from_text(description or text)
    main_topic = " ".join(keywords[:3]) if keywords else name

    positives = [
        f"Create a reusable {platform} skill for {main_topic}."
        for platform in DEFAULT_PLATFORMS[:4]
    ]
    positives.extend(
        [
            f"Improve the SKILL.md trigger description for {name}.",
            f"Audit and optimize this agent skill package: {name}.",
            f"Generate eval cases and trigger queries for {name}.",
            f"Write an implementation prompt for building the {name} skill.",
            f"Package this reusable AI workflow as an agent skill.",
        ]
    )

    negatives = [
        "Fix this one Python bug without creating a reusable workflow.",
        "Summarize this document for me.",
        "Write a one-off prompt for today's task only.",
        "Create a README for my app.",
        "Run tests and report failures.",
        "Explain what agent skills are in general.",
        "Edit this single config file for the current project.",
        "Draft an email response.",
    ]

    near_misses = [
        "Make a prompt better, but do not turn it into a reusable skill.",
        "Use a skill if one already exists, but do not create or audit one.",
        "Design a workflow for this task one time only.",
        "Compare Codex and Claude without creating SKILL.md files.",
    ]

    return {
        "skill_name": name,
        "positive_queries": positives,
        "negative_queries": negatives,
        "near_miss_queries": near_misses,
        "validation_split": {"train_ratio": 0.7, "validation_ratio": 0.3},
        "notes": "Draft generated locally from source text; review and add domain-specific near misses.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate draft trigger eval queries.")
    parser.add_argument("source", help="Path to a skill brief markdown file or SKILL.md")
    parser.add_argument("-o", "--output", help="Optional output JSON path")
    args = parser.parse_args()
    result = generate_queries(Path(args.source))
    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
