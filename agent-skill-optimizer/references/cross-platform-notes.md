# Cross-Platform Notes

Keep `SKILL.md` standardized and portable. Put platform-specific behavior in notes, adapters, templates, or separate references so the core skill remains reusable.

## Codex

- Useful for repository-aware editing, scripts, tests, and local file workflows.
- Keep permissions and destructive-operation confirmation explicit.

## ChatGPT

- Good for conceptual skill design, templates, and review.
- Avoid assuming direct filesystem or shell access unless the environment provides it.

## Claude

- Works well with long-form references and artifacts.
- Keep the trigger description concise and put longer policy or examples into references.

## OpenCode

- Often benefits from clear compatibility notes, command examples, and deterministic scripts.
- Keep generated reports and script outputs separate from core skill instructions.

## Cursor

- Useful for codebase-local skill editing and refactors.
- Keep instructions clear about when not to modify existing files.

## Gemini CLI

- Favor plain markdown, portable scripts, and explicit command usage.
- Avoid platform-only assumptions in the core workflow.

## Portability Rule

Core skill: standard frontmatter, purpose, workflow, resources, output, safety.

Adapters or notes: platform-specific commands, installation details, metadata conventions, or UI behavior.
