---
name: code-dedup
description: Find duplicate code, near-duplicate code, copy-paste code, repeated functions/classes/modules/config/scripts, folder-level duplication, 重复代码, 近重复, 合并建议, and 抽公共函数 opportunities; produce evidence-based dry-run merge/refactor suggestions with manual-review guardrails.
license: MIT
compatibility: opencode
metadata:
  category: code-quality
  safety: read-only-analysis
  output: json-and-markdown
---

# Code Dedup

## Purpose

Use this skill to analyze a code repository or selected directories for duplicate and near-duplicate implementation. The bundled script creates deterministic evidence, then the agent reviews the reported source context and produces cautious dry-run recommendations.

`scripts/code_dedup.py` is an evidence generator, not the final answer. The final response must combine script output with source reading, context checks, and engineering judgment.

## When to use

Use this skill when the user asks to:

- Find duplicate code, near-duplicate code, copy-paste code, or repeated logic.
- Analyze repeated functions, classes, modules, configs, scripts, or helper utilities.
- Compare folder-level duplication inside one directory or across subdirectories.
- Produce safe merge/refactor suggestions, such as extracting shared functions or shared modules.
- Explain why a scan found no duplicates or why only a few files were analyzed.

Trigger keywords include: `duplicate code`, `near-duplicate code`, `copy-paste code`, `repeated functions`, `repeated classes`, `folder-level duplication`, `safe merge/refactor suggestions`, `重复代码`, `近重复`, `合并建议`, `抽公共函数`.

## When not to use

Do not use this skill as the primary tool for:

- Image, video, audio, archive, model-weight, generated-result, or other binary asset deduplication.
- Data asset cleanup for folders such as `backgrounds/`, `objects/`, `merged/`, or `depth_gray/`, unless the user explicitly asks for data asset deduplication.
- Runtime profiling, dead-code detection, dependency vulnerability scanning, or API governance.
- Automatic file modification, deletion, moving, renaming, overwriting, or patch generation in the current analysis workflow.

## Safety model

The default mode for this skill is **read-only analysis + dry-run suggestions**.

- It does not actively modify files.
- It does not automatically generate patches.
- It does not delete, move, rename, overwrite, or consolidate files.
- Near-duplicate code is not semantic equivalence.
- Every merge/refactor recommendation must require manual review.
- Every recommendation must include `requires_manual_review=true`, `dry_run_only=true`, `risk`, `validation`, and `blockers`.

If the user later explicitly approves a specific recommendation, that is a separate patch/refactor workflow, not part of the default scan.

## Standard workflow

1. Identify the requested scope: full repository, selected directories, selected languages, directory-level duplication, or merge recommendations only.
2. Run the bundled script to generate deterministic evidence.
3. Read the JSON and Markdown reports as candidate evidence.
4. Inspect `quality_warnings`, `coverage`, `directory_summary`, and `clusters` before making claims.
5. For high/medium priority clusters or user-focused findings, read the affected source snippets directly.
6. Review whether the script candidate is a real duplicate, a boilerplate match, a generated/config artifact, or a domain-specific divergence.
7. Produce a Chinese response that starts with the conclusion and states that no files were modified.

## Script usage

Full repository scan:

```bash
python skills/code-dedup/scripts/code_dedup.py --root . --output .opencode/reports
```

Selected directories:

```bash
python skills/code-dedup/scripts/code_dedup.py --root . --include src packages --output .opencode/reports
```

Useful tuning options:

```bash
python skills/code-dedup/scripts/code_dedup.py \
  --root . \
  --include src packages \
  --exclude tests fixtures \
  --threshold 0.86 \
  --min-lines 12 \
  --output .opencode/reports
```

The script is read-only and writes only reports:

- `.opencode/reports/code-dedup-report.json`
- `.opencode/reports/code-dedup-report.md`

Default scans skip dependency/build/cache/agent-metadata directories such as `.git`, `node_modules`, `dist`, `build`, `.venv`, `.opencode`, `.agents`, and `.codex`.

## Evidence review workflow

Treat script output as evidence, not as the final judgment.

Always check:

- `run`: actual root, include/exclude filters, thresholds, and generated time.
- `summary`: scanned files, chunks, clusters, and high-priority count.
- `quality_warnings`: low coverage, too many unsupported files, max comparison limits, or test-only scans.
- `coverage`: recursive directories seen, supported files by directory, unsupported extensions.
- `directory_summary`: folder-level and cross-folder duplication.
- `clusters`: concrete duplicate candidates and merge plans.

For each important cluster, read the relevant source files and verify:

- Whether the logic is actually duplicated.
- Whether differences reflect business domain, permissions, validation, environment, error handling, or boundary behavior.
- Whether the suggested merge target is realistic.
- Whether the candidate should be downgraded to `manual_review_required` or `keep_separate_with_note`.

## Output contract

Recommended response structure:

```text
结论：
- 发现 N 类重复问题。
- 最值得处理的是 A、B、C。
- 未修改任何文件。

扫描覆盖：
- 根目录/范围：<root/include>
- 递归看到的子目录数：<N>
- 命中可分析代码的目录：<dir: file_count>
- 质量提醒：<quality_warnings summary>

目录级重复：
- <目录或目录对>：重复程度、原因、风险。

重点重复簇：
1. cluster_001，type=symbol_near，priority=high，risk=medium
   - path/to/a.ts:10-44，symbol=foo
   - path/to/b.ts:12-46，symbol=bar
   - 脚本证据：similarity=0.91，directory pair=src/a ↔ src/b
   - AI 复核：两处逻辑相似，但第二处多了权限边界判断，不能直接合并整个函数。

合并建议：
- 目标：src/shared/xxx
- 步骤：抽取最小公共逻辑；原函数保留领域入口；差异逻辑留在原模块。
- 阻断点：近重复不能证明语义等价。
- 验证：运行相关测试，检查调用方和边界条件。
- requires_manual_review=true
- dry_run_only=true
```

## Low coverage / zero result handling

If `duplicate_clusters=0` or very few files were scanned, do not directly conclude that the project has no duplicate code.

First explain:

- Which scan roots were used.
- How many subdirectories were recursively seen.
- Which directories contained supported code files.
- Which extensions were unsupported.
- Which files were ignored by exclude rules, size limits, binary detection, or missing paths.
- Whether `quality_warnings` indicates low confidence.

If the user says a folder was missed, use `rg --files <folder>` or an equivalent file listing to verify the folder contents, then rerun with corrected `--include`, `--exclude`, threshold, min-lines, or supported extension logic when appropriate.

## Recommendation rules

- `file_exact`: suggest a canonical file only after reference, ownership, and release-path review.
- `file_normalized_exact`: review comments, formatting, generated status, and intent before merging.
- `symbol_exact`: prefer extracting a shared function, class, or module when behavior contracts match.
- `symbol_near`: only extract the smallest confirmed-equivalent shared logic.
- `window_near`: consider extracting a helper, or keep separate with a note when flow similarity is not semantic equivalence.
- `config_duplicate`: extract shared templates only when environment differences remain explicit overrides.

Every recommendation must include:

- `candidate_target`
- `steps`
- `blockers`
- `validation`
- `risk`
- `requires_manual_review=true`
- `dry_run_only=true`

## Future patch/refactor workflow

This skill may be used as evidence for a later refactor. If the user explicitly approves a recommendation in a later conversation, the agent may enter a separate patch-planning workflow. That workflow must re-read the affected files, produce a minimal patch plan, ask for confirmation if risk is medium/high, run tests where available, and keep changes narrowly scoped.

Do not implement patches during the default scan/report workflow.

## References

Load only the reference needed for the current request:

- Read `references/detection-and-merge.md` for duplicate types, merge rules, low-coverage handling, risk, and performance guidance.
- Read `references/examples.md` for natural-language usage and output examples.
