# CTR Curve

The curve converts a position into an expected click-through rate so the queue can be ranked by estimated click upside. It is an assumption, not a Google metric.

## Values used by the analyzer

| Position | CTR |
|---|---|
| 1 | 0.28 |
| 2 | 0.15 |
| 3 | 0.11 |
| 4 | 0.08 |
| 5 | 0.06 |
| 6 | 0.045 |
| 7 | 0.035 |
| 8 | 0.028 |
| 9 | 0.024 |
| 10 | 0.02 |
| 11 | 0.01 |
| 12 to 20 | 0.005 |

These are round, illustrative values in the range published by industry CTR studies. They are deliberately coarse: the goal is consistent ranking of opportunities, not a traffic forecast.

## Formula

```
target_position = max(3, round(current_position) - 3)
expected_clicks = impressions * ctr(target_position)
upside = expected_clicks - clicks
```

If `upside` is negative, report zero and keep the row only when another rule (snippet gap or cannibalization) selects it.

## Why target position 3

Most of the click value sits in the top three results. Moving a query from 11 to 3 is a different project from moving it from 11 to 8. The rule caps the ambition at position 3 to avoid promising traffic that a single page edit cannot deliver.

## Reporting rules

- Always label the upside as an estimate.
- State the assumption: "assuming the standard CTR curve and no change in impressions".
- Never sum the upside across rows and present it as projected traffic. Rows overlap, and ranking gains shift impressions between queries.
- If the user has their own CTR baseline by position, use it instead and say so. The script accepts an override file with `position,ctr` rows.

## Known distortions

- Brand queries inflate CTR at every position.
- Featured snippets and People Also Ask change the layout and the click share.
- Local packs and shopping units push organic results down without changing the reported position.
- Seasonality changes demand, not position, and can move CTR in both directions.

When a row looks implausible, check brand intent and the search result layout before trusting the estimate.

## Effort weighting

The queue is sorted by estimated clicks per hour of effort, not by raw upside. Effort values are coarse: 30 minutes for a snippet rewrite or a redirect, 1 hour for a consolidation, 2 hours for a page rewrite or a retarget. The weighting exists so that cheap, certain fixes surface before expensive ones with a similar gain.

State the weighting when presenting the queue. Do not present the score as a forecast.

## Site calibration

The generic curve assumes an average site. A site that earns 1.58 percent CTR at position 8.4 while the curve predicts 2.80 percent is not a site full of broken snippets; it is a low-CTR niche.

Before ranking, the analyzer compares the observed CTR of the whole export with the curve value at the impression-weighted average position, and scales the curve by that ratio, clamped to 0.25 through 1.5. The factor is printed with the queue and stored as `ctr_calibration` in JSON.

Report it as: "curve calibrated x0.60 to this export". When the factor hits a clamp, say that the calibration is saturated and treat the numbers as rough.

`--no-calibration` disables the scaling for users who bring their own baseline. In that case the numbers are generic again, and the answer must say so.
