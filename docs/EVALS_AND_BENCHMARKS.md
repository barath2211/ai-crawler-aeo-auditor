# Evals and Benchmarks

## Two layers

1. **Checklist score (deterministic).** Tests the auditor itself: each check has unit tests with small HTML snippets (`tests/test_auditor.py`).
2. **Answerability (model-based).** Tests the *page*: can an assistant answer real questions using only what a crawler sees?

## Current results on fixtures

| Page | Score | Grade | Answerable (mock) |
|---|---|---|---|
| `before.html` (iframe + JS widgets) | 15 | F | 0 / 6 |
| `after.html` (native, JSON-LD, semantic table) | 94 | A | 6 / 6 |

`after.html` loses points on S1 because it's 195 words and still has one empty chart mount point. That's intentional: it shows partial credit working.

Answer matching is strict: a reply containing "NOT FOUND" is always wrong, and the expected value must appear after normalising number formatting (`1,204.6` = `1204.6` = `1 204.6`). This stops a model from scoring by hedging or by listing every number on the page.

The mock answerer finds sentences containing the expected value, so it measures whether the fact is *present* in crawler-visible text. A real model also tests whether it's *understandable* in context (e.g. the right year's figure from a table). Run both.

## Running with a real model

```bash
LLM_PROVIDER=ollama python src/cli.py data/fixtures/after.html --questions data/fixtures/questions.json --json out.json
```

Things to watch:
- **False positives:** the model answers from its own training data instead of the page. The prompt forbids it, and the fixture company is fictional so there's nothing to recall.
- **Table reading:** smaller models sometimes pick the wrong column. The `<caption>` and `<th scope>` markup measurably helps; try removing them and re-running.

## Writing a good question set

- Use questions your audience actually asks (search console queries, support tickets, IR inbox).
- Each question needs one unambiguous expected value.
- Include at least one question per key figure, one date and one "who/what" question.
- Keep the set fixed across a migration so before/after is comparable.

## Suggested gates

| Stage | Gate |
|---|---|
| PR to a component | Score ≥ 75, no new FAIL on I1, S1, D1 |
| Release | Answerability ≥ 90% on the standard question set |
