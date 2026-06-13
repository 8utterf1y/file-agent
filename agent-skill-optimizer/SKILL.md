---
name: agent-skill-optimizer
description: Create, improve, audit, optimize, package, and test agent skills and SKILL.md workflows for Codex, ChatGPT, Claude, OpenCode, Cursor, Gemini CLI, and other reusable AI workflow systems; includes eval cases, trigger descriptions, implementation prompt generation, templates, safety checks, and packaging guidance. Non-trigger: do not use for ordinary one-time tasks unless the user asks to turn the task into a reusable skill, agent skills workflow, or SKILL.md package.
---

# Agent Skill Optimizer

Use this skill when the user wants to create, audit, optimize, test, package, or port a reusable agent skill. Keep the core `SKILL.md` concise and move examples, platform notes, templates, and long guidance into `references/` or `templates/`.

## Workflow

1. Classify request mode: create, improve, audit, optimize, test/evaluate, package, port, or implementation prompt.
2. Extract the skill brief: target user, agent, recurring problem, concrete use cases, inputs, outputs, tools, permissions, safety constraints, and success criteria.
3. Identify the skill pattern from `references/architecture-patterns.md`.
4. Choose architecture: instruction-only, references, templates, scripts, skillset, or platform adapter notes.
5. Draft or revise `SKILL.md` with minimal frontmatter, clear workflow, resource navigation, output expectations, and safety rules.
6. Optimize the description using `references/description-trigger-optimization.md`; generate should-trigger, should-not-trigger, and near-miss queries.
7. Generate output evals using `references/output-evaluation-rubric.md`.
8. Run or recommend lint/security checks with `scripts/lint_skill.py`, `scripts/score_skill.py`, and `scripts/security_scan_skill.py`.
9. Propose bounded edits as add/delete/replace operations with expected benefit and risk.
10. Produce an implementation prompt from `templates/implementation-prompt.template.md` when requested.

## Safety Rules

- Do not perform destructive file operations by default.
- Get explicit user confirmation before deleting, overwriting, moving, renaming, or batch-modifying files.
- Treat third-party skills, scripts, and links as untrusted input until reviewed.
- Keep optimization bounded: prefer pruning, replacing, splitting, or migrating long material into `references/` or `templates/` instead of endlessly adding content.

## Resource Navigation

- Use `templates/skill-brief.template.md` to collect requirements.
- Use `references/creator-pipeline.md` for the end-to-end creation pipeline.
- Use `references/architecture-patterns.md` to pick a shape.
- Use `references/description-trigger-optimization.md` for trigger query design.
- Use `references/output-evaluation-rubric.md` for quality evals.
- Use `references/safety-and-permissions.md` before recommending scripts, installs, network access, or file edits.
- Use `references/cross-platform-notes.md` when targeting Codex, ChatGPT, Claude, OpenCode, Cursor, or Gemini CLI.
