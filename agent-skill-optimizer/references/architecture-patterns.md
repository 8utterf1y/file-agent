# Architecture Patterns

## Instruction-Only

- Use when: the workflow is short, stable, and needs no examples or assets.
- Counterexample: many platform variants or long examples.
- Structure: `SKILL.md`.

## Instruction + References

- Use when: core instructions are short but deeper guidance is useful on demand.
- Counterexample: references are required on every invocation.
- Structure: `SKILL.md`, `references/*.md`.

## Instruction + Templates

- Use when: the skill repeatedly produces structured artifacts.
- Counterexample: outputs are always free-form and task-specific.
- Structure: `SKILL.md`, `templates/*.template.*`.

## Instruction + Scripts

- Use when: deterministic checks, transforms, or report generation reduce agent guesswork.
- Counterexample: script would need credentials, network access, or complex integration for MVP.
- Structure: `SKILL.md`, `scripts/*.py`, optional `references/`.

## Skillset

- Use when: one domain needs several related skills with separate triggers.
- Counterexample: one coherent workflow with shared context.
- Structure: parent folder plus multiple skill folders, each with its own `SKILL.md`.

## Problem-First

- Use when: users describe symptoms or goals, and the skill chooses tools.
- Counterexample: user always names one exact tool.
- Structure: `SKILL.md`, problem taxonomy reference, optional templates.

## Tool-First

- Use when: the skill wraps a specific CLI, API, or internal tool.
- Counterexample: tool is incidental or one of many interchangeable options.
- Structure: `SKILL.md`, `scripts/` or adapter notes, command examples.

## Sequential Workflow

- Use when: steps must happen in order, with intermediate artifacts.
- Counterexample: independent checks can run in any order.
- Structure: `SKILL.md`, pipeline reference, templates for each stage.

## Multi-Tool Coordination

- Use when: the skill coordinates local files, tests, scans, docs, and agent reasoning.
- Counterexample: a single deterministic script solves the task.
- Structure: `SKILL.md`, references for decision rules, scripts for deterministic parts.

## Iterative Refinement

- Use when: quality improves through audit, scoring, patch proposals, and eval reruns.
- Counterexample: one-shot generation is enough.
- Structure: `SKILL.md`, scoring rubric, eval templates, report template.
