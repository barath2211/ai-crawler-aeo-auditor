# Case study: making client content visible to AI answer engines

**My role:** I found the problem, designed the approach, built key parts hands-on, pitched it and led the migration.
**Setting:** A SaaS company serving financial content to many client websites through a shared, centrally hosted iframe.
**Result:** **40+ client-facing components** moved to native, per-client rendering. Clients gained control of their own data, search indexing improved, and client content started appearing in AI-generated answers.

---

## The situation

Key financial content (multi-year performance figures, charts and tables) was delivered to every client site through one shared iframe that we managed centrally. It worked in a browser. But:

- **Crawlers barely saw it.** Search engines and AI crawlers treat iframe content as a separate page, if they index it at all, and credit it to the host domain, not the client's.
- **Clients had no control.** One shared setup meant every client got the same behaviour. They couldn't manage their own data or presentation.
- **It didn't blend in.** The iframe looked bolted onto the client's site.

At the same time, more investors were getting answers from AI assistants instead of clicking through to websites. If an assistant can't read a client's figures, the client is missing from those answers.

## Making the problem measurable

"Our content isn't AI-friendly" is hard to prioritise. I needed a number and a list of fixes. So I built an audit covering the things that decide whether a crawler can read and quote a page: iframes, content that only appears with JavaScript, structured data, heading structure, semantic tables, robots rules for AI crawlers, and so on.

Then I added the check that matters most: give a model only what a crawler sees, ask it the questions an investor would ask, and see if it can answer. A page can tick every box and still fail that test.

## Key decisions

**Measure outcomes, not just hygiene.** The answerability test turned a technical debate into a simple before/after anyone could understand: "the assistant could answer 0 of 6 questions from this page; after the change, 6 of 6."

**Native rendering per client, interactivity on top.** The figures render as real HTML in the client's page, with structured data and proper tables. Interactive charts load on top as an enhancement, so nothing depends on JavaScript to be readable.

**Give each client control.** Moving off the shared iframe meant each client could manage their own data and presentation independently.

**Use the audit as the acceptance test.** Each migrated component had to pass the audit before release, so quality didn't depend on memory.

## Rollout

1. Audited representative client pages to size the problem and build the business case.
2. Presented it to management, the product manager and the VP.
3. Migrated components in waves, checking each against the audit.
4. Completed 40+ client-facing components.

## Outcome

- Clients got independent control over their own data and presentation.
- Search indexing of client pages improved.
- Client content began showing up in AI-generated answers.

These were tracked qualitatively at the time. If I did it again, I'd set up the measurement before migrating (see below).

## What I'd do differently

- **Baseline first.** Record indexing numbers and a fixed set of assistant questions per client *before* migrating, so the improvement has hard numbers.
- **Track real assistant citations over time**, not just a local test.
- **Crawl whole sites** instead of single pages, and report by page template.

## In this repo

The sample pages are fictional. `python src/cli.py compare data/fixtures/before.html data/fixtures/after.html --questions data/fixtures/questions.json --provider mock` reproduces the before/after (15 to 94, 0/6 to 6/6 answerable).
