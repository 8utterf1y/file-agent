# Creator Pipeline

Start every skill from 2-3 concrete use cases. Do not begin from an abstract wish like "make this agent better"; write the repeated user requests the skill should handle.

## Discovery

- Input: user goal, examples of repeated requests, target agent, target workspace, existing skill files.
- Actions: collect 2-3 use cases, non-goals, inputs, outputs, required tools, permissions, and safety limits.
- Output: skill brief draft.
- Common failures: vague target user, no non-trigger cases, trying to cover unrelated workflows.

## Design + Evals

- Input: skill brief and representative user prompts.
- Actions: define should-trigger, should-not-trigger, near-miss trigger queries, and output-quality evals.
- Output: `eval_queries.json` draft and task eval cases.
- Common failures: only positive examples, no near misses, evals that check style but not task completion.

## Architecture

- Input: brief, evals, expected assets, expected scripts.
- Actions: choose instruction-only, references, templates, scripts, skillset, or adapter notes.
- Output: directory plan and resource map.
- Common failures: stuffing everything into `SKILL.md`, adding scripts where instructions are enough, platform-specific clutter.

## Build

- Input: approved directory plan and templates.
- Actions: create `SKILL.md`, references, templates, and lightweight scripts.
- Output: first usable skill package.
- Common failures: weak description, long tutorials in core instructions, unsafe default actions.

## Validate

- Input: skill files and eval queries.
- Actions: lint frontmatter, review trigger behavior, run sample output evals, check docs and script usage.
- Output: validation report and bounded fix list.
- Common failures: no testable acceptance criteria, overfitting description to one eval set.

## Security Scan

- Input: full skill directory.
- Actions: scan for destructive commands, credential handling, untrusted downloads, network access, and upload/exfiltration behavior.
- Output: security findings with severity and file locations.
- Common failures: trusting third-party skills, hiding risky commands in examples, missing shell snippets.

## Iterate

- Input: validation and security findings.
- Actions: prune, replace, split, move detail into references/templates, clarify outputs, add eval coverage.
- Output: improved skill version with change rationale.
- Common failures: endless content growth, fixing examples but not the trigger description.

## Package

- Input: validated skill directory.
- Actions: verify minimal required files, platform notes, permissions, script usage, and final file list.
- Output: portable skill package ready to move or install.
- Common failures: platform lock-in, missing resource references, unreviewed generated files.
