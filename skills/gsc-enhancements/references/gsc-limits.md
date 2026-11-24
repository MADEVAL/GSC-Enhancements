# GSC Limits

Every number in this skill is bounded by how Search Console collects data. State these limits in the answer instead of hiding them.

## Row caps

- UI export: 1,000 rows per table. Treat the file as a sample.
- Search Analytics API: up to 25,000 rows per request, with pagination by `startRow`. Google still does not guarantee that every impression is represented.
- BigQuery bulk export: daily dumps with no row cap, but no backfill for dates before setup.

## Anonymized queries

Queries with very few impressions are omitted from the rows but included in the property totals. The rows therefore do not add up to the totals. The difference is the anonymized gap.

How to report it: "Rows cover 93.8 percent of clicks; the remaining 6.2 percent is anonymized queries." Do not call the gap an error, and do not invent the missing queries.

## Freshness and retention

- Performance data lags by roughly 2 to 3 days. The last two days are incomplete.
- History is available for 16 months. Anything older is gone.
- Final numbers can change slightly for a few days after a row appears.

## Sampling

Large properties can receive sampled data. When sampling applies, totals and dimension rows may disagree even without anonymization. If the numbers look inconsistent, report the inconsistency rather than smoothing it.

## Position

- Position is an average across all impressions in the selected period, including impressions from devices and countries the user did not filter.
- A missing position is not position zero. It means the query was not ranked in the measured set.
- Average position mixes page one and page ten. A page can rank 4 on desktop and 14 on mobile and still show 9.4.

## Property types

- Domain property: `sc-domain:example.com`, covers every protocol and subdomain.
- URL prefix property: `https://example.com/`, covers that exact prefix only.
- The API requires the exact property string. A mismatch returns a permission error even when the user owns the site.

## Click-through rate

CTR is clicks divided by impressions for the selected rows. It is not comparable across positions without a reference curve, and it is not a quality score.

## Indexing

- `Indexing API` is for JobPosting and BroadcastEvent. It is not a general-purpose indexing shortcut.
- "Discovered - currently not indexed" is a normal state for new or low-value URLs, not proof of a bug.
- URL Inspection quota is limited per property per day. Batch inspection is slow by design.

## Reporting sentence

Use one of these instead of silence:

- "The export is capped at 1,000 rows; conclusions apply to the visible sample."
- "Totals include 4.1 percent anonymized queries that are absent from the rows."
- "The last two days are incomplete because of reporting lag."
- "Position is an average for the period, not a live rank."

## Sample coverage

A 1,000-row export is not the site. The query table can cover a small share of clicks, especially on long-tail sites.

Any dimension export sums to the same site totals: country, device, search appearance, or the chart export. The analyzer looks for such a file next to the input and reports coverage, or accepts one explicitly with `--totals`.

Rules:

- Below 50 percent of clicks, say "sample" out loud. Do not present the queue as complete.
- Below 20 percent, treat the queue as a thematic signal, not a work plan.
- Never scale click counts up to the site total; the missing rows are not a random sample.

Report it as: "The 1,000-row export covers 8.7 percent of clicks and 8.1 percent of impressions; totals come from `Страны.csv`."
