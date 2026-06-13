#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DANGEROUS_PATTERNS = [
    (r"\brm\s+-rf\b", "destructive shell deletion"),
    (r"自动删除|automatically delete", "automatic deletion"),
    (r"覆盖|overwrite", "overwrite behavior"),
    (r"上传密钥|upload.*(?:secret|token|key|password)", "credential upload"),
    (r"(?:curl|wget).*\|\s*(?:sh|bash)", "remote script execution"),
]


def parse_frontmatter(text: str) -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    if not text.startswith("---\n"):
        return {}, ["SKILL.md is missing YAML frontmatter"]
    end = text.find("\n---", 4)
    if end == -1:
        return {}, ["SKILL.md frontmatter is not closed"]
    raw = text[4:end].strip()
    data: dict[str, str] = {}
    for line in raw.splitlines():
        if not line.strip():
            continue
        if ":" not in line:
            errors.append(f"Invalid frontmatter line: {line}")
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data, errors


def lint_skill(skill_dir: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    skill_md = skill_dir / "SKILL.md"

    if not skill_md.exists():
        return {
            "ok": False,
            "skill_dir": str(skill_dir),
            "errors": ["SKILL.md does not exist"],
            "warnings": [],
        }

    text = skill_md.read_text(encoding="utf-8", errors="replace")
    frontmatter, fm_errors = parse_frontmatter(text)
    errors.extend(fm_errors)

    for required in ("name", "description"):
        if required not in frontmatter:
            errors.append(f"frontmatter missing required key: {required}")

    name = frontmatter.get("name", "")
    description = frontmatter.get("description", "")
    if name and not NAME_RE.match(name):
        errors.append("name must use lowercase letters, numbers, and hyphens only")
    if not description.strip():
        errors.append("description is empty")
    elif len(description) < 80:
        warnings.append("description may be too short for reliable triggering")
    elif len(description) > 800:
        warnings.append("description may be too long and costly for triggering")

    for pattern, message in DANGEROUS_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            warnings.append(f"possible risk in SKILL.md: {message}")

    return {
        "ok": not errors,
        "skill_dir": str(skill_dir),
        "frontmatter": {
            "name": name,
            "description_length": len(description),
            "keys": sorted(frontmatter),
        },
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint an agent skill directory.")
    parser.add_argument("skill_dir", help="Path to a skill directory")
    args = parser.parse_args()
    result = lint_skill(Path(args.skill_dir))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
