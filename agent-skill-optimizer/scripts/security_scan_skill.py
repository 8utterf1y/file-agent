#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


SCAN_EXTENSIONS = {".md", ".py", ".sh", ".bash", ".zsh"}
RISK_PATTERNS = [
    ("rm_rf", re.compile(r"\brm\s+-rf\b", re.IGNORECASE), "high"),
    ("curl_pipe_sh", re.compile(r"\bcurl\b.*\|\s*(?:sh|bash)\b", re.IGNORECASE), "high"),
    ("wget_pipe_sh", re.compile(r"\bwget\b.*\|\s*(?:sh|bash)\b", re.IGNORECASE), "high"),
    ("sudo", re.compile(r"\bsudo\b", re.IGNORECASE), "medium"),
    ("chmod_777", re.compile(r"\bchmod\s+777\b", re.IGNORECASE), "high"),
    ("credential_field", re.compile(r"\b(secret|token|password|api[_-]?key|private[_-]?key)\b\s*[:=]", re.IGNORECASE), "medium"),
    ("auto_upload", re.compile(r"自动上传|自动外传|auto(?:matic)? upload|exfiltrat", re.IGNORECASE), "high"),
    ("auto_delete", re.compile(r"自动删除|auto(?:matic)? delete", re.IGNORECASE), "high"),
    ("auto_overwrite", re.compile(r"自动覆盖|auto(?:matic)? overwrite", re.IGNORECASE), "high"),
]
DOCUMENTATION_MARKERS = (
    "flag ",
    "flags ",
    "scan for ",
    "detect",
    "pattern",
    "rule",
    "example",
    "such as",
    "高风险",
)
RULE_DEFINITION_MARKERS = ("re.compile", "RISK_PATTERNS", "DANGEROUS_PATTERNS")


def iter_scannable_files(skill_dir: Path) -> list[Path]:
    files: list[Path] = []
    for path in skill_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in SCAN_EXTENSIONS:
            files.append(path)
    return sorted(files)


def is_documentation_line(line: str) -> bool:
    lower = line.lower()
    stripped = line.strip()
    tuple_rule_definition = stripped.startswith("(r\"") and stripped.endswith("),")
    return tuple_rule_definition or any(marker.lower() in lower for marker in DOCUMENTATION_MARKERS + RULE_DEFINITION_MARKERS)


def finding_severity(base_severity: str, line: str) -> str:
    if is_documentation_line(line):
        return "info"
    return base_severity


def scan_skill(skill_dir: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    for path in iter_scannable_files(skill_dir):
        rel = path.relative_to(skill_dir).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        for line_no, line in enumerate(text.splitlines(), start=1):
            for rule_id, pattern, base_severity in RISK_PATTERNS:
                if pattern.search(line):
                    severity = finding_severity(base_severity, line)
                    findings.append(
                        {
                            "rule_id": rule_id,
                            "severity": severity,
                            "file": rel,
                            "line": line_no,
                            "snippet": line.strip()[:240],
                        }
                    )
    return {
        "ok": not any(item["severity"] == "high" for item in findings),
        "skill_dir": str(skill_dir),
        "files_scanned": len(iter_scannable_files(skill_dir)),
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Security-scan an agent skill directory.")
    parser.add_argument("skill_dir", help="Path to a skill directory")
    args = parser.parse_args()
    result = scan_skill(Path(args.skill_dir))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
