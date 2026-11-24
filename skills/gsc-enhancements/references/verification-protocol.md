# Verification Protocol

A change is a hypothesis. Verification is how the hypothesis gets a fair test.

## Minimum conditions

- At least 28 days between publication and the after export.
- Before and after periods of equal length.
- Same property, same filters (country, device, search type).
- The changed page had enough impressions to detect movement: at least the impression floor used in the original analysis.
- No other major change on the same page in the same window: no template update, no migration, no redirect.

If any condition fails, the verdict is `too early` or `not verifiable`. Both are valid answers.

## Comparing

Match rows by query and page. Do not compare site totals; a single page is too small a share.

For each pair compute:

```
delta_clicks = after_clicks - before_clicks
delta_impressions = after_impressions - before_impressions
click_change = delta_clicks / max(before_clicks, 1)
```

## Verdicts

| Condition | Verdict |
|---|---|
| Fewer than 28 days | `too early` |
| Before and after both zero clicks | `no data` |
| Click change at least +20 percent and at least +5 clicks | `improved` |
| Click change at most -20 percent and at least -5 clicks | `declined` |
| Anything else | `flat` |

The absolute minimum protects against a page moving from 2 clicks to 3 being called a win.

## Confounders to check before reporting

- Seasonality: compare with the same weeks a year earlier if the data exists.
- SERP layout changes: new snippets, packs or shopping units alter CTR without touching the page.
- Tracking changes: consent mode, tag manager, or analytics edits break click continuity.
- Site-wide changes: navigation, internal linking or a migration can lift or sink every page.
- Query mix: impressions can shift to a different query on the same page.

## Reporting

Always include:

1. the before and after periods with dates;
2. the pair that was compared;
3. the verdict from the table;
4. one confounder that was ruled out, and one that could not be ruled out;
5. the next check date.

Never say "the change worked" from position alone. Position can improve while clicks fall, for example when a snippet loses a rich result.

## When the verdict is `flat`

Flat is information. Options:

- keep the change if it reduced effort or improved clarity for users;
- revert if the change added complexity for no measured gain;
- run a larger change, then verify again with the same protocol.

Do not stack three changes in one week and then try to attribute the result.
