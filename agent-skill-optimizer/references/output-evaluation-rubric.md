# Output Evaluation Rubric

Output evals measure what happens after the skill triggers. A good eval includes the user prompt, expected output, input files, and assertions.

## Eval Shape

- `prompt`: the user request to test.
- `expected_output`: concise description of the desired answer or artifact.
- `input_files`: files or fixture snippets the agent may inspect.
- `assertions`: checks that decide whether the result passed.

## Assertion Types

- Program-verifiable assertions: valid JSON, required files created, frontmatter keys present, script exits with code 0, no forbidden file operations.
- Human or LLM-judged assertions: explanation quality, correct architecture choice, useful risk assessment, practical implementation prompt.

## Comparison

Use with-skill / without-skill or v1 / v2 comparisons for meaningful improvements. Hold out validation prompts so optimization does not only fit the training examples.

## Scoring Dimensions

- Task completion: produced the requested artifact or review.
- Format compliance: followed requested structure, JSON schema, or template.
- Evidence: cites files, lines, examples, or findings when auditing.
- Reproducibility: commands and steps can be rerun.
- Safety: avoids destructive actions and flags risky behavior.
- Cost: keeps context concise and loads only needed resources.
- User usefulness: recommendations are concrete, bounded, and actionable.
