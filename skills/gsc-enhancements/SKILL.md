---
name: gsc-enhancements
description: Turn Google Search Console data into a prioritized fix queue with expected click upside and a verification protocol, instead of another report. Works offline on Performance exports (CSV or tab-separated) and needs no API key; the live API is an optional upgrade. Use for GSC exports, striking-distance queries, low-CTR pages, query-page cannibalization, content decay, and checking whether a change worked. Do NOT use for pulling raw Search Console, GA4, CrUX or PageSpeed data (hand off to seo-google), generating sitemaps (seo-sitemap), crawl-level technical audits (seo-technical), or rewriting copy (seo-content).
license: MIT
compatibility: any-llm
metadata:
  author: Yevhen Leonidov
  version: "0.1.0"
  languages: [en, ru]
  repository: https://github.com/MADEVAL/GSC-Enhancements
  modes: "3"
---

# GSC Enhancements

Search Console answers "what happened". This skill answers "what do I change first, and how will I know it worked".

It takes a Performance export that the user already has and returns a small, ranked queue of actions. Every row carries the evidence behind it: query, page, impressions, position, period, and source file. Anything that cannot be proven from the file is reported as unknown, never guessed.

The skill is deliberately offline first. No service account, no OAuth screen, no API key. The live Search Console API is an optional upgrade, and when the user has it, the handoff is `seo-google`.

## Prerequisites

- Python 3.10 or newer.
- One Performance export from Search Console: Queries, Pages, or Queries with Pages. CSV and tab-separated files are both accepted.
- Optional: a second export from a later period for `verify`.

If the user has no export, explain how to make one (one click in the Performance report, Export, CSV) before doing anything else. Do not ask for credentials in chat.

## When Not to Use

| Situation | Hand off to | Why |
|---|---|---|
| The user wants raw GSC, GA4, CrUX, PageSpeed or Indexing API data | `seo-google` | That skill owns authentication and API calls |
| The user needs an XML sitemap generated or validated | `seo-sitemap` | Different data source |
| The user needs a crawl-level technical audit | `seo-technical` | Requires fetching pages, not GSC rows |
| The user needs copy rewritten | `seo-content` | This skill recommends, it does not write |
| The user has no GSC data and no access | Explain the export step | Without evidence the answer would be invented |
| The question is about AI Overviews or LLM citations | `seo-geo` | Different surface |

## Modes

| Mode | Input | Output |
|---|---|---|
| `analyze` | One Performance export | Ranked queue: striking distance, snippet gaps, decay candidates |
| `cannibalization` | Export with query and page dimensions | One decision per query: keep, retarget, consolidate or redirect |
| `verify` | Before and after exports | Improved, declined, flat, too early or no data |

## Workflow

1. Confirm the evidence base. Ask which property, which date range, and whether the file came from the Performance report or the API. If the range is shorter than 28 days, say so before analysis.
2. Check the file shape. Run the analyzer with `--json` and read `limits` in the output. It reports row count, anonymized-query gap when totals are present, how many rows had a missing position, and the impression range that the upside rule applied. It also reports sample coverage when a country, device or chart export sits next to the input, or when `--totals` points to one.
3. Run one mode. Do not chain modes in a single answer unless the user asks for an audit.
4. Read the queue, not the raw rows. Keep the top 5 to 10 actions. Group the rest into a backlog count.
5. State the limits. Always name the period, the property, and the file. Never call an export "the full query list".

Commands:

```bash
python scripts/analyze_export.py analyze --input queries.csv
python scripts/analyze_export.py cannibalization --input query-page.csv
python scripts/analyze_export.py verify --before before.csv --after after.csv --weeks 4
```

Add `--json` for machine-readable output, `--limit N` to change the queue size, `--min-position` and `--max-position` to widen or narrow the striking-distance band, `--min-impressions` to override the upside rule, `--brand "term,term"` to exclude brand queries, and `--no-calibration` to use the generic curve as is.

## Decision Rules

1. A row enters the queue only when it can plausibly produce at least 3 clicks: `impressions >= 3 / ctr(target)`, with a hard minimum of 10. At position 18 that means thousands of impressions; at position 6, dozens. Report the range that was applied, and say when `--min-impressions` overrode it.
2. Average position is read per query and page, not per query alone. When the same query has several pages, the leading page is the one with the most impressions.
3. Striking distance is positions 4 to 20 by default. Below 4 the page already wins; above 20 the page is not close enough for a focused edit to be credible.
4. Expected click upside is an estimate: `impressions * (ctr(target) - ctr(current))`, with `target = max(3, round(position) - 3)`. Label it as an estimate, never as a forecast.
5. A snippet gap exists when position is 10 or better and observed CTR is below 60 percent of the curve value at that position.
6. Cannibalization is a decision, not a finding. One page keeps the query, the others get a specific action. More than one URL alone is not proof; the pages must share intent.
7. Decay needs two comparable periods of equal length. A single export cannot show a trend.
8. Verification needs at least 28 days after the change. Below that, the only honest verdict is "too early".
9. Never state search volume, difficulty or intent. If it is not a column in the file, it is not in the answer.
10. When rows do not add up to the totals, the gap is anonymized queries. Report it as a gap, not as an error.
11. The queue is sorted by estimated clicks per hour of effort, so a 30-minute snippet fix outranks a two-hour rewrite with the same gain. Say that the order is ROI-based.
12. Brand queries inflate every estimate. Ask for brand terms and pass `--brand`; if the user does not know them, note that the queue may be brand-driven.
13. Navigational and service-name queries (a ministry site, a government service, a competitor brand) can show thousands of impressions with almost no clicks by design. Check intent before recommending a snippet rewrite; drop the row when the searcher wants a different destination.
14. The curve is calibrated to the export itself, with a factor between 0.25 and 1.5. Report the factor. Use `--no-calibration` only when the user has a better baseline of their own.
15. State sample coverage. The interface caps the export at 1,000 rows, and a query export can cover a small share of site clicks. When coverage is below 50 percent, say that the queue is a sample, not the whole site.

## Output Contract

Every answer uses the same five blocks, in this order:

1. **Verdict** - one sentence: what the data supports and what it does not.
2. **Evidence base** - property, period, file, row count, impression floor or upside rule, sample coverage, known limits.
3. **Queue** - a table with priority, action, query, page, impressions, position, estimated gain, effort, and evidence. Five to ten rows. If the queue is empty, say why.
4. **Handoff** - which skill or human action comes next, if any.
5. **What would change the answer** - the missing data or period that could flip the verdict.

Estimates are marked as estimates. Unknown values are written as `unknown`, never as `0`.

## Hard Stops

Stop and ask when:

- the file has no impressions column or no query or page column;
- the export is a screenshot, a PDF, or a chart image;
- the period is shorter than 14 days;
- the user asks for a verdict on a change made less than 28 days ago;
- the property in the file cannot be identified and the user expects site-wide conclusions;
- the same file is used as both before and after.

## Constraints

- No network access by default. The analyzer reads local files only.
- No credentials, no tokens, no cookies in chat.
- Client query data stays local. Do not paste raw exports into third-party services.
- Findings must cite the row they came from.
- Recommendations must name one page and one change. "Improve content" is not an action.
- The skill does not promise rankings. It estimates click upside under an explicit CTR assumption.

## Reference Files

- `references/export-format.md` - how the export is produced and which columns are expected.
- `references/gsc-limits.md` - row caps, anonymized queries, sampling, lag and retention.
- `references/ctr-curve.md` - the illustrative CTR curve and the upside formula.
- `references/cannibalization-tree.md` - the decision tree for shared queries.
- `references/verification-protocol.md` - how to judge a change after publication.

## Example

Input: 4,812 rows, 28 days, property `sc-domain:example.com`.

Verdict: 7 actions are supported; the rest of the file is below the impression floor.

Queue (first three rows):

| Priority | Action | Query | Page | Impressions | Position | Est. gain | Effort |
|---|---|---|---|---|---|---|---|
| 1 | rewrite-snippet | seo audit checklist | /blog/seo-audit | 1840 | 9.4 | +41 | 30 min |
| 2 | strengthen-page | schema markup test | /tools/schema | 1210 | 12.1 | +28 | 2 h |
| 3 | consolidate | gsc export limit | /blog/gsc-limits | 860 | 11.6 | +17 | 1 h |

Evidence: `queries.csv`, 2026-10-27 to 2026-11-23, floor 38 impressions. Anonymized gap 6.2 percent of total clicks.

Handoff: the snippet rewrite goes to `seo-content`; the consolidation plan goes to `seo-technical` for redirect checks.
