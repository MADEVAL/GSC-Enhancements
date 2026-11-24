# GSC Enhancements

[![version](https://img.shields.io/badge/version-0.1.0-blue)](CHANGELOG.md)
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)

Turn Google Search Console data into a ranked fix queue with evidence, estimated click upside and a verification protocol, instead of another report.

Most GSC tools answer "what happened". This skill answers "what do I change first, and how will I know it worked". It works on the export you already have, offline, with no API key.

## What it does

| Mode | Input | Output |
|---|---|---|
| `analyze` | One Performance export | Ranked queue: striking distance, snippet gaps, refresh candidates |
| `cannibalization` | Export with query and page dimensions | One decision per query: keep, retarget, consolidate or redirect |
| `verify` | Before and after exports | Improved, declined, flat, too early or no data |

Every row carries its evidence: query, page, impressions, position and source file. Unknown values are reported as `unknown`, never as `0`, and a row only enters the queue when it can plausibly produce at least 3 clicks. The queue is ordered by estimated clicks per hour of effort.

## Why it is different

- **Offline first.** No service account, no OAuth screen, no API key. CSV and tab-separated files are both accepted.
- **Decisions, not a data dump.** Five to ten actions, each with one page and one change.
- **Limits are stated.** The 1,000-row export cap, anonymized queries, sampling, reporting lag and 16-month history are in the answer, not hidden.
- **Verification is built in.** A change is only "improved" after 28 days, equal periods and a minimum click delta.
- **Calibrated to your data.** The CTR curve is scaled to the export's own CTR, so a low-CTR niche does not turn into a queue of five hundred "broken snippets".
- **Honest about coverage.** If a country, device or chart export sits next to the file, the skill reports what share of site clicks the sample covers and warns when it is under half.

## Install

```bash
python install.py --target opencode
python install.py --list
python install.py --target project --dry-run
python install.py --target opencode --check
```

Targets: `claude`, `opencode`, `agents`, `codex`, `project`, `all` (default). Requires Python 3.10 or newer; CI runs 3.12.

## Use

```bash
python skills/gsc-enhancements/scripts/analyze_export.py analyze --input queries.csv
python skills/gsc-enhancements/scripts/analyze_export.py cannibalization --input query-page.tsv --json
python skills/gsc-enhancements/scripts/analyze_export.py verify --before before.csv --after after.csv --weeks 4
```

Options: `--limit`, `--min-impressions`, `--min-position`, `--max-position`, `--brand`, `--curve`, `--no-calibration`, `--totals`, `--json`.

Coverage is detected automatically from a sibling country, device or chart export. Pass it explicitly when the files are in different folders:

```bash
python skills/gsc-enhancements/scripts/analyze_export.py analyze --input queries.csv --totals countries.csv
```

`cannibalization` needs a combined `query,page` file. The Performance UI exports one dimension at a time, so use the Search Console API, the BigQuery bulk export, or `seo-google`.

Text output is a Markdown table. JSON output is stable enough to script against.

JSON fields: `mode`, `input`, `rows_read`, `missing_position`, `anonymized_gap`, `totals_inconsistent`, `impression_floor`, `min_upside_clicks`, `row_floor_range`, `brand_excluded`, `ctr_calibration`, `coverage`, `rows_matched`, and `rows[]` with per-row evidence. Unknown numbers are `null`, never `0`.

## Test

```bash
python tests/validate_skill.py
python tests/run_tests.py
```

The suite includes a deliberately broken fixture, so a passing run proves the validator can fail.

## Limits

- Position is an average for the period, not a live rank.
- The UI export is capped at 1,000 rows; it is a sample.
- Expected click upside is an estimate under an explicit CTR curve.
- No search volume, difficulty or intent is inferred.
- The skill does not promise rankings and does not rewrite copy.

## Related skills

- `seo-google` for raw GSC, GA4, CrUX and PageSpeed data.
- `seo-sitemap` for sitemap work.
- `seo-technical` for crawl-level audits.
- `seo-content` for rewriting.

## License

MIT. See [LICENSE](LICENSE).
