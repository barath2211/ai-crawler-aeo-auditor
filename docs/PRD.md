# PRD: AI Crawler & AEO Auditor

| | |
|---|---|
| Author | Barath Kumar |
| Status | Reference implementation (public). Based on an internal migration I led. |
| Last updated | September 2026 |

## 1. Summary

Client websites were showing key financial content through a centrally hosted iframe. Humans saw it; AI assistants and search crawlers mostly didn't, and when they did they attributed it to the vendor's domain. This tool measures that gap page by page, tells teams exactly what to fix, and proves the fix worked by testing whether an AI can answer real questions from the page.

It served two purposes: building the business case for migrating off the iframe, and acting as the acceptance test for each migrated component.

## 2. Problem

- **Invisible content.** Figures inside iframes or rendered only by JavaScript don't reach most AI crawlers.
- **Wrong attribution.** Indexed iframe content is credited to the host domain, not the client's.
- **No shared control.** A shared iframe meant one configuration for every client; clients couldn't control their own data presentation.
- **No way to measure.** "Is our page AI-friendly?" had no objective answer, so it was hard to prioritise.

## 3. Personas

| Persona | Need |
|---|---|
| Product analyst / PM | Evidence to prioritise a migration and a way to measure progress |
| Front-end developer | A precise list of what to change on each component |
| Client IR / web team | Confidence their data shows up correctly in AI answers and search |
| QA | A pass/fail gate that can run in CI |

## 4. Goals and non-goals

**Goals**
1. Score any page (URL or file) for AI discoverability with evidence and fixes.
2. Measure outcomes, not just hygiene, through an answerability eval.
3. Run in CI with a score threshold.
4. Compare before and after for a migration.

**Non-goals**
- Rendering JavaScript (on purpose; it hides the problem we're measuring).
- Traditional SEO ranking factors (backlinks, speed, keywords).
- Monitoring actual AI assistant answers over time (possible v2).

## 5. User stories and acceptance criteria

| # | Story | Acceptance criteria |
|---|---|---|
| US-1 | As a PM, I want a single score per page so I can rank what to migrate first. | 0 to 100 score and A to F grade; checks and weights listed in the output. |
| US-2 | As a developer, I want to know exactly what to fix. | Every failing or partial check shows evidence and a concrete fix. |
| US-3 | As a PM, I want proof that migrated pages are actually answerable. | Answerability eval reports N of M questions answered correctly from crawler-visible content only. |
| US-4 | As QA, I want to block regressions. | `--fail-under N` exits non-zero below threshold. |
| US-5 | As a client, I want to know if we're blocking AI crawlers by accident. | robots.txt parsed per major AI crawler; blocked bots listed by name. |
| US-6 | As a PM, I want a before/after view for stakeholder updates. | `compare` command prints a side-by-side table with totals and answerability. |

## 6. Key decisions and trade-offs

| Decision | Alternative | Reasoning |
|---|---|---|
| No JavaScript execution | Headless browser rendering | Matches how most AI crawlers read pages; the gap is the finding |
| Weighted checklist + outcome eval | Checklist only | A page can tick boxes and still not answer the question; the eval keeps us honest |
| LLM only for answerability | LLM grades the whole page | Checks stay deterministic and explainable; the model is used where judgement is needed |
| Questions supplied by the team | Model generates questions | Real audience questions are the target; model-generated ones drift toward what the page already says |
| Robots decisions reported, not judged | Always fail if any bot blocked | Blocking can be a deliberate choice; the tool makes it visible |

## 7. Edge cases

| Case | Behaviour |
|---|---|
| Page fetch fails | Clear error; no partial score |
| No robots.txt | Treated as allow-all, check marked n/a |
| Local file | robots/llms checks n/a unless files are passed in |
| Invalid JSON-LD | Fails D1 with the parse error (search engines ignore invalid blocks entirely) |
| Tables built from divs | Flagged under T1 |
| Content partly server-rendered | Partial credit on S1 based on word count; empty JS mount points listed |

## 8. Success metrics (for the migration it supported)

| Metric | Target |
|---|---|
| Components migrated off shared iframe | All client-facing components (40+ in the original) |
| Median audit score of migrated pages | ≥ 85 |
| Answerability on the standard question set | ≥ 90% |
| Regressions caught in CI before release | Tracked |

## 9. Rollout

1. Audit the top 20 client pages to size the problem and build the business case.
2. Add the auditor as a CI gate on the new native components.
3. Migrate components in waves, highest-traffic first; report before/after per wave.
4. Offer clients a self-serve report for their own pages.
