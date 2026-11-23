# Letter Templates

Fill-in templates for first-touch outreach. `scripts/letter_builder.py` fills these placeholders and rotates variants by company-domain hash. Sender identity, product, and value points come from config; never hard-code real values into this file.

The templates are industry-neutral on purpose. They contain exactly two content slots that carry anything specific: `{observation}`, which must come from research on that one company, and `{product_value}`, which comes from config. There is no sample observation sentence anywhere in this file, because a copied sample sentence is how a letter ends up describing the wrong business.

## Placeholders

| Placeholder | Source | Notes |
|---|---|---|
| `{first_name}` | Cleaned contact name | First name only, titles and notes stripped. Falls back to the generic greeting when no name is trusted. |
| `{company}` | Lead row | Company name as the company writes it. |
| `{company_short}` | Derived from the company name | Short name for subject lines: parenthetical notes and legal suffixes stripped, at most four words. |
| `{observation}` | Researched per company, stored on the lead row | The letter-ready personalisation for this company alone, public information only, carrying both points the letter rules require: one concrete fact about their public range, programme, or channel activity, plus one "why now" signal (adjacent category, new range, channel expansion, a fair they exhibit at). Shape: "runs a <named programme or range> for <their buyer type>" with the angle brackets replaced by what the company actually publishes. If research produced no such clause, the row is not ready and `letter_builder.py` will refuse to build the letter. |
| `{obs_first}` | First sentence of `{observation}` | Verbatim, for the three-line short skeleton only. |
| `{product}` | Config | Your product in a short phrase. |
| `{product_value}` | Config value points, chosen per company | One buyer-side value sentence, for example margin, sell-through, durability in transit and storage, year-round demand, one line covering several channels. |
| `{closing}` | Variant list below | One low-pressure call to action. |
| `{sender_name}` | Config | One line. |
| `{sender_company}` | Config | One line under the sender name. |

## Six skeletons (English)

One skeleton plus synonym rotation is not enough: hundreds of letters built that way share one structural fingerprint. The builder uses six genuinely different skeletons (paragraph order, length band, and call to action all differ), narrows the pool by buyer type, then picks one skeleton per company by a hash of the company domain, so the same company always gets the same skeleton and different companies are spread across skeletons. Inside each skeleton, phrase-level spintax blocks `{A|B|C}` vary the wording block by block, again by company-domain hash. Names, company names, and numbers never go inside a spintax block.

| # | Skeleton | Paragraph order | Length band | Call to action |
|---|---|---|---|---|
| 1 | Standard introduction | Greeting, observation, who you are, buyer value, closing | 90–130 words | Send catalogue and terms |
| 2 | Question opening | Greeting, business question, observation as background, one value sentence, low-pressure question | 60–90 words | Answer a question / point to the right person |
| 3 | Three-line short | Greeting with the observation first sentence, product plus value, one-line closing | 35–55 words | One-line ask for the price list |
| 4 | Buyer ledger | Greeting, observation, cost-of-waste paragraph, short introduction, closing | 100–130 words | Send terms and price list |
| 5 | Seasonal scenario | Greeting, seasonal hook, observation, one product sentence, year-round benefit, closing | 80–110 words | Send seasonal catalogue / samples |
| 6 | Direct supply | Greeting, direct supply statement, fit from the observation, one-word reply closing | 70–100 words | Reply with one word to receive terms |

Skeleton pools by buyer type (same company keeps its skeleton across batches and follow-ups; spread a batch across the pool, never put a whole batch on one skeleton):

- Wholesale / import / distribution / supply buyers: {1, 2, 4, 6}
- Gift buyers: {1, 2, 3, 5}
- Retail / chain / store / ecommerce buyers: {1, 2, 3, 6}
- Channel partners (platforms, buying groups, distributor networks): the partner skeleton set below, full pool {1..6}
- Anything else: {1, 2, 4, 6}

`scripts/letter_builder.py` implements these skeletons (`SKELETONS`, `PARTNER_SKELETONS`, `pick_skeleton`, `_spin`). The skeleton bodies below show the spintax option sets exactly as the code renders them.

### Skeleton 1 — Standard introduction

Subject variants (rotated, one per letter):

1. `Wholesale enquiry: {product}`
2. `{product}: a low-risk line for your range`
3. `Catalogue and wholesale terms: {product}`

Body:

```text
Hi {first_name},

I noticed {company} {observation}

{We manufacture|Our factory produces|We are a maker of} {product} for wholesale and contract buyers. {product_value} {For your buyers the practical point is|The practical side is what sells}: one line that stays sellable across seasons and across several of your channels.

{Could I send you our catalogue and wholesale terms?|Shall I send over the catalogue with the wholesale price list?|Would it help if I sent the catalogue and terms?}

Best regards,
{sender_name}
{sender_company}
```

### Skeleton 2 — Question opening

Subject variants:

1. `Quick question about your range`
2. `A question on your buying range`
3. `Who looks after buying at {company_short}?`

Body:

```text
Hi {first_name},

{How much of your seasonal range has to sell within the season before it loses value?|Who on your team looks after the lines that sit alongside your core range?|How do you handle lines that run out before the next season comes round?}

I noticed {company} {observation} We {make|produce} {product}. {product_value}

{Would it be useful if I sent a short overview with wholesale terms?|If it is not you, could you point me to the right person?|Worth a one page overview with wholesale terms?}

Best regards,
{sender_name}
{sender_company}
```

### Skeleton 3 — Three-line short

Subject variants:

1. `{product}, wholesale`
2. `A short note: {product} for your range`
3. `{product} for {company_short}`

Body:

```text
Hi {first_name}, {obs_first}

We {make|supply} {product} for wholesale buyers. {product_value} {Shall I send the price list?|Catalogue and wholesale terms, if useful?}

Best regards,
{sender_name}
{sender_company}
```

### Skeleton 4 — Buyer ledger

Subject variants:

1. `The line with no write-offs`
2. `Stock that holds its value between seasons`
3. `A range with no expiry losses`

Body:

```text
Hi {first_name},

I noticed {company} {observation}

{Seasonal stock usually carries a quiet cost|Slow lines carry a hidden cost}: whatever misses its window {gets marked down or written off|sits until the next season}. {product} {takes that line out of the ledger|carries none of that}. {product_value} One line earns across the year instead of a single season.

We manufacture {product} and supply it wholesale. {Could I send our terms and the wholesale price list?|Shall I send the terms sheet and the catalogue?}

Best regards,
{sender_name}
{sender_company}
```

### Skeleton 5 — Seasonal scenario

Subject variants:

1. `One line for the seasons your buyers plan around`
2. `For the occasions that drive repeat orders`
3. `A range that earns all year`

Body:

```text
Hi {first_name},

{The busiest buying weeks are the ones buyers plan months ahead, and the lines that earn most are the ones that keep selling once the rush is over.|Some occasions drive a rush, and the lines that earn most keep selling after it.}

I noticed {company} {observation} We make {product}. {product_value}

{Could I send the seasonal catalogue with wholesale terms?|Shall I send samples and the wholesale terms for your range review?}

Best regards,
{sender_name}
{sender_company}
```

### Skeleton 6 — Direct supply

Subject variants:

1. `Wholesale supply: {product}`
2. `{product}: wholesale supply`

Body:

```text
Hi {first_name},

{Straight to the point|Short version}: we {manufacture|make} {product} and supply it wholesale to {importers and distributors|distributors and retail buyers}.

I noticed {company} {observation} The fit is simple: {product_value}

{Reply with the word catalogue and I will send the range and price list over.|If you reply with pricing, I will send wholesale terms and the catalogue.}

Best regards,
{sender_name}
{sender_company}
```

## Channel partner skeletons

For platforms, buying groups, retail networks, and distributor groups, where the contact manages a range for many downstream sellers rather than buying for one store. Decision-makers to target: the people who own the range, category, or partner programme (see config for titles). The partner set mirrors the six skeletons above with a partner angle: consistent supply across the year, one line that works across several of the partner's sellers' channels, and packaging ready for mixed-channel distribution. Full partner skeleton texts live in `scripts/letter_builder.py` (`PARTNER_SKELETONS`).

Partner observation pattern: name the programme or range the partner itself publishes (its partner programme, member range, or distribution network), in the partner's own terms. Public information only, same rules as the main skeletons.

## Language versions by market

Write one language version per language in config's `language_by_market` mapping, and use the version that matches the recipient's market.

1. Copy the skeleton set, including subject, intro, and closing variant sets.
2. Translate as a set so the result reads natively; keep the skeleton structures, the word limits, and every hard rule in `docs/04-letter-rules.md`.
3. Register the language against its markets in config (`language_by_market`).
4. Extend the quality gate's snooping and hype word lists with equivalents in the new language, and gate-test three sample letters before the first batch.
5. **The first version in any new language must be confirmed by the operator before it is used in a batch.** Machine-translated or agent-translated templates go out only after that confirmation; record the confirmation in the run log.

## Worked example (slots only)

This skeleton shows the slots, not sample content. The curly-brace values are what research and config supply for one specific company; none of them is reusable text. Skeleton 1 shown, one spintax option per block.

```text
Subject: Wholesale enquiry: {product}

Hi {first_name},

I noticed {company} {observation}

We manufacture {product} for wholesale and contract buyers. {product_value} For your buyers the practical point is: one line that stays sellable across seasons and across several of your channels.

Could I send you our catalogue and wholesale terms?

Best regards,
{sender_name}
{sender_company}
```
