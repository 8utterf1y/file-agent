---
name: skill-name
description: Describe the reusable workflow, target trigger phrases, target platforms, output artifacts, and boundaries. This frontmatter description is what most affects triggering; body sections help after the skill is selected.
---

# Skill Title

## Purpose

State the recurring problem this skill solves.

## When To Use

- Use when the user asks for the reusable workflow this skill supports.
- Include common trigger phrases and concrete use cases.

## When Not To Use

- Do not use for ordinary one-time tasks outside the reusable workflow.
- Do not use when another specialized skill is clearly more appropriate.

## Workflow

1. Classify the request.
2. Gather required inputs.
3. Choose the right resources or tools.
4. Produce the requested output.
5. Validate format, safety, and acceptance criteria.

## Resource Navigation

- `references/...`: deeper guidance loaded only when needed.
- `templates/...`: output skeletons or reusable prompts.
- `scripts/...`: deterministic checks or generators.

## Output Format

Describe the expected answer, files, JSON schema, or report sections.

## Safety Rules

- State default side effects.
- Require confirmation for destructive, risky, or broad changes.
- Treat untrusted inputs carefully.

## Evaluation Cases

- Positive trigger:
- Negative trigger:
- Near miss:
- Output-quality eval:
