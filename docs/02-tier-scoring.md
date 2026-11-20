# 02 — Tier Scoring

> Fictional example: Guangzhou BrightTable Ceramics (fictional example). All signals and weights below are examples; set your own in config (`scoring_weights`, `fit_signals`).

## Why three dimensions, not one number

A single total score hides fatal weaknesses. A company can look excellent on buying signals and still be unusable because nobody reachable works there, or because the only "evidence" is a directory snippet. Score three dimensions separately, then tier on the combination.

| Dimension | Question it answers | Example signals (0 to 5 each) |
|---|---|---|
| Fit | Would they plausibly buy this product? | Category match with your product keywords (see config); import record for your HS codes (see config); carries adjacent lines; wholesale or B2B programme present |
| Contactability | Can you reach a decision-maker? | Named decision-maker in a target role (see config); verified useful email (see `docs/03-email-verification.md`); published direct address; only a generic inbox scores low |
| Evidence | How solid is the information? | Confirmed on the company's own website or official documents scores high; a single directory listing scores mid; a search-result snippet alone scores low |

## Tier definitions

| Tier | Meaning | Requirement |
|---|---|---|
| S | Strong buying signal plus direct category fit | All three dimensions high. Fit and contactability must both be strong; evidence must come from the company's own site or official records. |
| A | Direct category fit | Fit high, contactability at least medium (a useful email exists), evidence at least medium. |
| B | Broadly related buyer (adjacent category, general wholesale) | Fit medium. Worth outreach after S and A are exhausted in that market. |
| C | Unverified or on hold | Thin evidence, unresolved competitor question, or no useful email yet. Not sent; kept for enrichment. |

## Caps and demotion rules

- **Evidence cap:** if the only source is a search snippet or an unverified directory entry, the company is capped at Tier B until its own website confirms the business.
- **Contactability cap:** no useful email means no tier above C for sending purposes, regardless of fit. The company goes to enrichment, not to a batch.
- **Accept-all cap:** a company whose only personal address sits on an accept-all domain is treated as having no verified email (see `docs/03-email-verification.md`).
- **Competitor rule:** a company that manufactures or owns a brand in your core category is not tiered at all. It goes to the intelligence pool. A reseller of similar products is a customer, not a competitor.
- **Exclusion override:** blocklist, excluded-market, and exclusion-rule matches (see config and `docs/06-exclusions-and-failsafes.md`) override any score. Excluded means excluded.

## Worked example (fictional)

A fictional importer, Harbour Table Co. (fictional example), shows 40+ import records under HS 6912 in the last year (fit 5), publishes a tableware category page and a wholesale portal (fit +), names its purchasing manager on its team page with a verifier-confirmed direct address (contactability 5), and all facts come from its own site plus trade records (evidence 5). Result: Tier S.

A fictional general wholesaler with an adjacent housewares range, a generic `info@` inbox only, and one directory listing: fit 3, contactability 2, evidence 2. Result: Tier B, enrichment candidate for a named contact before any send.

## Maintaining the weights

Weights live in config (`scoring_weights`) and come from the ICP questionnaire (Step 1, Q8 in `docs/01-methodology.md`). Change them only at the monthly review, using reply and bounce evidence from the feedback log, and note the change and the reason. Weights tuned per batch produce tiers nobody can compare across time.
