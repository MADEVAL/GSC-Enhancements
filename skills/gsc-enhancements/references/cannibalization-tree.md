# Cannibalization Tree

More than one URL for a query is a signal, not a verdict. Walk the tree and end with exactly one action per query.

## Step 1. Is the query shared?

Group rows by query. If only one page appears, there is nothing to decide. If two or more pages appear, continue.

## Step 2. Is the intent the same?

Ask whether a searcher typing this query would be satisfied by any of the pages. If the pages serve different intents (a product page and a support article), the overlap is harmless. Mark it `not-cannibalization` and stop.

## Step 3. Who owns the query?

The owner is the page with the highest impressions for that query in the period. Ties are broken by clicks, then by the shorter URL. Name the owner explicitly; never leave it implicit.

## Step 4. Choose the action

| Condition | Action |
|---|---|
| Owner has the best intent fit and at least 50 percent of query impressions | `keep-owner`, strengthen the others' distinct angle |
| A non-owner has better intent fit but fewer impressions | `retarget`: rewrite the non-owner for its own intent |
| Two pages describe the same thing and neither is clearly stronger | `consolidate`: merge into the owner and redirect the other |
| A non-owner earns under 10 percent of the query impressions and has no unique intent | `redirect` to the owner |
| The query deserves a page that does not exist yet | `create`: one new URL, then re-check in 28 days |

## Step 5. Verify the decision

After the change, compare the same query and page pair. The expected result is a higher share for the owner and a lower, not vanished, share for the retargeted page. If the owner's position drops, the merge removed a signal rather than consolidating it.

## Guardrails

- Do not recommend `noindex` for a page that carries other queries. Check the page's full query set first.
- Do not merge pages across languages or regions. That is an hreflang decision, handled by `seo-hreflang`.
- Do not treat a query that appears with a page in a different country as cannibalization. Filter by country first.
- Do not act when total query impressions are below the impression floor. The signal is too weak.

## Output shape

| Query | Owner | Other pages | Decision | Action | Evidence |
|---|---|---|---|---|---|
| gsc export limit | /blog/gsc-limits | /docs/exports | consolidate | merge and redirect | 860 vs 140 impressions, same intent |
