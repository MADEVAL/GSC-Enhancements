# Export Format

The skill works on files that Search Console can already produce. No API is required.

## Producing the export

1. Open Search Console and pick the property.
2. Open Performance, Search results.
3. Set the date range. Use a full range, not "Last 7 days", unless the user asks for a weekly pulse.
4. Choose the tab: Queries, Pages, or Queries with Pages (the last one requires the API or the UI filter workaround).
5. Click Export, then CSV.

For a query and page file, the Performance UI is not enough: it exports one dimension at a time. A combined `query,page` export comes from the Search Console API (`dimensions: [query, page]`), from the BigQuery bulk export, or from `seo-google`. Exporting pages one query at a time works for a handful of queries but does not scale and does not produce a single combined file.

`cannibalization` therefore requires a combined file. Without it, the analyzer stops with an explicit message instead of returning an empty result.

## Accepted columns

Column names are matched case-insensitively. The analyzer accepts the common UI and API spellings.

| Meaning | Accepted headers |
|---|---|
| Query | `query`, `queries`, `top queries`, `search query`, `популярные запросы`, `запросы`, `популярні запити` |
| Page | `page`, `pages`, `top pages`, `landing page`, `url`, `популярные страницы`, `страницы`, `популярні сторінки` |
| Clicks | `clicks`, `click`, `клики`, `кліки` |
| Impressions | `impressions`, `impression`, `показы`, `покази` |
| CTR | `ctr`, `click through rate`, `click-through rate`, `кликабельность` |
| Position | `position`, `average position`, `avg position`, `позиция`, `средняя позиция`, `позиція` |

Localized exports are accepted as they come from the interface. One known quirk: the Russian header for clicks sometimes uses a Latin `K` instead of Cyrillic `К`. Both spellings are matched.

A file must contain impressions and at least one of query or page. Clicks are required for the upside estimate; without them the analyzer reports upside as `unknown`.

## Value conventions

- CTR is accepted as `0.0521`, `5.21%` or `5.21`. Values above 1 are treated as percentages.
- Position is accepted as `9.4` or `9,4`. Empty, `-`, `~` and `0` are treated as missing, never as rank zero.
- Thousands separators are accepted in both styles: `1,840` and `1.840` mean one thousand eight hundred forty in integer columns.
- Decimal commas are accepted: `0,65%` and `12,5` are read as `0.65%` and `12.5`.
- Preamble lines before the header, such as `Property:` or `Period:`, are skipped.
- Summary rows such as `Total`, `Totals`, `Filtered` and `Sum` are read as totals and excluded from the rows.

## Delimiters and encoding

- Comma and tab separated files are detected by content, not by extension.
- UTF-8 with or without BOM is accepted. A BOM is stripped before parsing.
- Other encodings are rejected with an explicit message. Re-export as UTF-8 rather than guessing.

## What the file cannot tell you

- The UI export is capped at 1,000 rows. It is a sample, not the full query list.
- Anonymized queries are missing from the rows but counted in the chart totals.
- The API returns up to 25,000 rows per request but still does not guarantee every row.
- Rows carry average position for the whole period, not a live rank.

See `references/gsc-limits.md` for the full list and the exact wording to use when reporting.
