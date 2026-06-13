# Implementation Prompt

You are implementing or upgrading an agent skill.

## Goal

Create or revise the skill so it supports the recurring workflow described below.

## Directory

- Target directory:
- Existing files to preserve:

## Files To Create Or Update

- `SKILL.md`
- `references/`
- `templates/`
- `scripts/`

## Constraints

- Do not delete existing files.
- Do not overwrite existing files without explicit confirmation.
- Do not move or rename existing files without explicit confirmation.
- Keep `SKILL.md` concise.
- Move long examples and platform-specific details into references or templates.
- Prefer standard-library scripts for the first version.

## Tests And Checks

- Run lint checks for frontmatter and description quality.
- Run security scans for destructive commands and credential risks.
- Run any included unit tests or script smoke tests.

## Acceptance Criteria

- Required files exist.
- The skill has clear trigger and non-trigger behavior.
- Outputs are testable with eval cases.
- Safety rules are explicit.
- The package can be moved to a formal skill location without hidden dependencies.

## Skill Brief

Paste the completed brief here.
