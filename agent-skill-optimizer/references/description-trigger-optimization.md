# Description Trigger Optimization

The frontmatter `description` is the main trigger mechanism. Section titles and body text help the agent after activation, but the description should carry the phrases, intent, and boundaries that decide when the skill is selected.

## Query Sets

Create at least 20 trigger eval queries:

- 8-10 should-trigger positive queries.
- 8-10 should-not-trigger negative queries.
- Several near-miss negatives that mention related words but are ordinary one-time tasks.

Include direct terms, synonyms, platform names, artifact names, and user-intent phrases. For this skill, examples include `create a SKILL.md`, `optimize trigger descriptions`, `package an agent skill`, `generate eval cases`, and near misses like `write a one-off prompt`.

## Measurement

- Run trigger checks multiple times if the platform has nondeterminism.
- Track trigger rate for positive, negative, and near-miss sets.
- Split examples into train and validation groups before tuning.
- Avoid overfitting by preserving broad intent, not memorizing exact eval strings.
- Review false positives before adding more trigger words.

## Example `eval_queries.json`

```json
{
  "skill_name": "agent-skill-optimizer",
  "positive_queries": [
    "Create a reusable Codex skill with a SKILL.md and eval cases.",
    "Audit this Claude skill and improve its trigger description.",
    "Package an OpenCode agent skill with templates and safety checks."
  ],
  "negative_queries": [
    "Write a one-time shell script for this folder.",
    "Summarize this document.",
    "Fix this Python bug without making a reusable skill."
  ],
  "near_miss_queries": [
    "Write a prompt for today only, not a reusable workflow.",
    "Explain what skills are in general.",
    "Create a README for my project."
  ],
  "validation_split": {
    "train_ratio": 0.7,
    "validation_ratio": 0.3
  },
  "notes": "Tune for reusable skill creation and optimization, not ordinary task execution."
}
```
