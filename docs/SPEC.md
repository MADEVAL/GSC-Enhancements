# SPEC - GSC Enhancements

Status: draft, v0.1.0 implemented as a skeleton with three modes.
Owner: Yevhen Leonidov.
Created: 2026-11-24.

## Problem

Search Console gives numbers. Turning them into a decision is manual work: export, sort, filter, compare, remember what was changed and when. Agencies do this per client, per month, and the result is either a 40-page report nobody reads or three guesses.

Existing agent skills in this space stop at data access. They wrap the API, return rows, and leave the decision to the model. That is the gap this skill targets: not retrieval, but a defensible action queue.

## Positioning

One sentence: turn a Search Console export into a prioritised fix queue with evidence, estimated click upside and a verification protocol, offline and without an API key.

Three claims that must stay true in every version:

1. The skill works on a file the user already has.
2. Every recommendation cites the row that produced it.
3. The skill refuses a verdict when the data cannot support one.

## Audience

- A freelancer with 3 to 20 properties who exports GSC every month.
- A small agency that needs a repeatable first-pass triage before human review.
- An in-house SEO who wants to hand a developer a short, prioritised list.

Not the audience: enterprises on BigQuery bulk export, teams that want a dashboard, or users who expect rank tracking.

## Scope

In scope for 1.0.0:

- Parse Performance exports: CSV and tab-separated, query, page, clicks, impressions, CTR, position.
- `analyze`: adaptive impression floor, striking-distance band, snippet gap detection, estimated click upside, effort per action.
- `cannibalization`: owner selection per query, retarget, consolidate, redirect decisions.
- `verify`: before and after comparison with improved, declined, flat, too early, no data.
- Limits reporting: row count, missing positions, anonymized gap against totals.
- Sample coverage: read a sibling country, device or chart export, report what share of site clicks the sample covers, warn below 50 percent.
- JSON output stable enough to script against.
- References that explain the limits, the CTR curve, the decision tree and the verification protocol.

Planned for 1.1.0 and later:

- `decay`: two equal periods, page-level click and impression decline with a cause hypothesis.
- BigQuery export input, read-only and local.
- Brand and non-brand split with a configurable brand term list.
- Portfolio mode across several properties with consistent thresholds.
- Optional live API adapter that delegates auth to `seo-google`.

## Non-goals

- Not a rank tracker, not a dashboard, not a hosted service.
- No search volume, keyword difficulty or intent inference.
- No content rewriting. Recommendations only.
- No sitemap generation, no crawling, no Core Web Vitals fetching.
- No credential storage and no network calls by default.
- No promise of ranking or traffic outcomes.

## Data modes

| Mode | Source | Status |
|---|---|---|
| Offline export | Performance CSV or TSV | 0.1.0 |
| Offline combined export | `query,page` CSV from API, BigQuery or `seo-google` | 0.1.0, required for `cannibalization` |
| BigQuery export | `searchconsole` dataset | planned 1.1.0 |
| Live API | Search Console Search Analytics | out of scope, hand off to `seo-google` |

Offline is the default and the supported path. The Performance UI exports one dimension at a time, so `analyze` and `verify` work on a plain Queries or Pages export, while `cannibalization` needs a combined file. That limit is stated in the tool output, not hidden.

## Decision rules

| Rule | Value | Rationale |
|---|---|---|
| Queue entry | estimated upside at least 3 clicks; `impressions >= 3 / ctr(target)`, hard minimum 10 | Keeps rows where a realistic edit can produce a measurable change; scales with position instead of a fixed floor |
| Striking distance | positions 4 to 20 | Below 4 the page already wins; above 20 a focused edit is not credible |
| Target position | `max(3, round(position) - 3)` | Caps ambition at the top three results |
| Snippet gap | position <= 10 and CTR < 60 percent of curve | Separates title problems from ranking problems |
| CTR calibration | curve scaled by observed / expected at the weighted average position, factor clamped to 0.25-1.5 | A low-CTR niche would otherwise flag every row as a broken snippet |
| Navigational queries | require an intent check, never an automatic snippet rewrite | A ministry or competitor name can earn impressions with no clicks by design |
| Cannibalization owner | highest impressions, then clicks, then shorter URL | Deterministic and explainable |
| Redirect threshold | share of query impressions < 10 percent | Below that the page adds no unique value |
| Consolidate threshold | share at least 40 percent | Two comparable pages compete; merge instead of retargeting |
| Ordering | estimated clicks per hour of effort | A 30-minute fix should beat a 2-hour fix with the same gain |
| Brand filter | optional `--brand` term list, case-insensitive substring | Brand queries inflate CTR and upside |
| Verification window | at least 28 days, equal periods | Below that the data cannot separate signal from noise |
| Improved | at least +20 percent and at least +5 clicks | Prevents a 2 to 3 click move being called a win |

Rules are implemented in `skills/gsc-enhancements/scripts/analyze_export.py` and documented in `references/`.

## Architecture

```
skills/gsc-enhancements/
  SKILL.md            routing, modes, output contract, hard stops
  agents/openai.yaml  interface metadata
  references/         limits, formats, curve, decision tree, verification
  scripts/            analyze_export.py, stdlib only, no network
tests/                validator, unit tests, fixtures, negative fixture
docs/                 this specification
```

The script is deliberately boring: one file, standard library, no dependencies, deterministic output. That keeps installation to a copy and makes the numbers reproducible by a human with a spreadsheet.

## Roadmap

| Version | Content | Exit criterion |
|---|---|---|
| 0.1.0 | analyze, cannibalization, verify, references, validator, CI | Tests pass, validator has a failing fixture |
| 0.2.0 | decay, brand split, portfolio thresholds | Three real exports produce sane queues |
| 0.5.0 | BigQuery input, curve override workflow | One warehouse export parsed without manual edits |
| 1.0.0 | docs, both READMEs, manifests, topics, publication | Checklist in `DEVELOP.md` p. 45 complete |

## Acceptance Criteria

The skill is acceptable when all of the following hold:

1. `python tests/validate_skill.py` passes on the repository and fails on `tests/fixtures/bad-skill`.
2. `python tests/run_tests.py` passes. CI runs Python 3.12; the code avoids syntax newer than 3.10 and imports only the standard library.
3. `analyze` on the fixture returns only rows that pass the upside rule, never returns a position below the minimum band, and honours `--min-impressions` when given.
4. `cannibalization` names exactly one owner per query and one action per other page.
5. `verify` returns `too early` for any window under 28 days.
6. Every answer states the period, the property, the row count and the filter that was applied (upside rule or explicit impression floor).
7. No em dash, no en dash, UTF-8 without BOM, LF endings in every tracked text file.
8. Version is identical in `SKILL.md`, `CHANGELOG.md`, both READMEs and three manifests.
9. `install.py` copies only the payload and `LICENSE`; `docs/`, `tests/` and `evals/` stay out.
10. The skill states its limits and never invents volume, difficulty or intent.
11. When a totals export is available, coverage is reported in clicks and impressions, and any share below 50 percent is labelled as a sample.

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| GSC data is lossy (cap, anonymization, sampling) | False confidence | Limits are reported in every answer; tests cover the gap field |
| CTR curve is generic | Upside estimate is wrong in absolute terms | Curve is explicit, override is supported, estimate is always labelled |
| SEO niche is saturated | Low adoption | Position as a decision tool and a lead magnet, not as another data wrapper |
| Overlap with `seo-google` | Confusing handoff | API access is explicitly out of scope, handoff is documented in `SKILL.md` |
| Client exports contain private queries | Data leak | Local-only processing, no network, exports ignored by git |

## Publication

Checklist for 1.0.0:

1. Repository description: one line, same as the positioning sentence.
2. Topics: `google-search-console`, `gsc`, `seo`, `search-analytics`, `cannibalization`, `agent-skills`, `opencode`, `claude-code`.
3. Verify with `gh repo view MADEVAL/GSC-Enhancements --json visibility,description,repositoryTopics`.
4. Publish to skills.sh via the public repository, then check indexing.
5. Pull requests to two awesome lists.
6. Distribution page: https://www.skills.sh/madeval

## Competition

| Project | Strength | Gap this skill targets |
|---|---|---|
| `judicael-s/google-search-console-skill` | MCP packaging, quick wins | Requires an MCP server and credentials |
| `coffeegrind123/search-console-skill` | Honest limits, nine recipes | No offline mode, no verification protocol |
| `Horan0990/ga4-gsc-seo-skill` | GA4 plus GSC, action cards | Requires OAuth desktop client, no negative-result discipline |
| `skills.ws` search-console | Broad workflow coverage | API and BigQuery oriented |
| GSC PAP, QuerySail, blogr.ai | Polished SaaS | Paid, hosted, data leaves the machine |

Differentiation: offline input, explicit evidence, decisions instead of reports, verification as a first-class mode.
