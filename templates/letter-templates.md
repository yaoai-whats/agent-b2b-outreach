# Letter Templates

Fill-in templates for first-touch outreach. `scripts/letter_builder.py` fills these placeholders and rotates variants by company-domain hash. Sender identity, product, and value points come from config; never hard-code real values into this file.

The templates are industry-neutral on purpose. They contain exactly two content slots that carry anything specific: `{observation}`, which must come from research on that one company, and `{product_value}`, which comes from config. There is no sample observation sentence anywhere in this file, because a copied sample sentence is how a letter ends up describing the wrong business.

## Placeholders

| Placeholder | Source | Notes |
|---|---|---|
| `{first_name}` | Cleaned contact name | First name only, titles and notes stripped. Falls back to the generic greeting when no name is trusted. |
| `{company}` | Lead row | Company name as the company writes it. |
| `{observation}` | Researched per company, stored on the lead row | One clause about their public range, programme, or channel activity, public information only, written for this company alone. Shape: "runs a <named programme or range> for <their buyer type>" with the angle brackets replaced by what the company actually publishes. If research produced no such clause, the row is not ready and `letter_builder.py` will refuse to build the letter. |
| `{product}` | Config | Your product in a short phrase. |
| `{product_value}` | Config value points, chosen per company | One buyer-side value sentence, for example margin, sell-through, durability in transit and storage, year-round demand, one line covering several channels. |
| `{closing}` | Variant list below | One low-pressure call to action. |
| `{sender_name}` | Config | One line. |
| `{sender_company}` | Config | One line under the sender name. |

## Main template (English)

Subject variants (rotated):

1. `Wholesale enquiry: {product}`
2. `{product}: a low-risk line for your range`
3. `Catalogue and wholesale terms: {product}`

Body:

```text
Hi {first_name},

I noticed {company} {observation}.

We make {product}. {product_value}

{closing}

Best regards,
{sender_name}
{sender_company}
```

Intro variants for the "we make" sentence (rotated):

1. `We manufacture {product} for wholesale and contract buyers.`
2. `Our factory produces {product}, supplied to importers and distributors.`
3. `We are a maker of {product} selling through wholesale channels.`

Value-sentence guidance: pick the value point (see config) that matches the observation. Good value points are stated in the buyer's terms: what it does to their margin, their breakage or returns, their shelf or range fit, their restocking risk. A value point that only describes your product's features is not finished yet.

Closing variants (rotated, exactly one per letter):

1. `Could I send you our catalogue and wholesale terms?`
2. `Shall I send over the catalogue with the wholesale price list?`
3. `Would it help if I sent the catalogue and terms?`

## Channel partner template

For platforms, buying groups, retail networks, and distributor groups, where the contact manages a range for many downstream sellers rather than buying for one store. Decision-makers to target: the people who own the range, category, or partner programme (see config for titles).

Subject: `Wholesale range proposal: {product}`

```text
Hi {first_name},

I noticed {company} {observation}.

We manufacture {product} for wholesale and contract buyers. {product_value} For a partner range, the practical points are consistent supply across the year, one line that works across several of your sellers' channels, and packaging ready for mixed-channel distribution.

{closing}

Best regards,
{sender_name}
{sender_company}
```

Partner observation pattern: name the programme or range the partner itself publishes (its partner programme, member range, or distribution network), in the partner's own terms. Public information only, same rules as the main template.

## Language versions by market

Write one language version per language in config's `language_by_market` mapping, and use the version that matches the recipient's market.

1. Copy the main template, including subject, intro, and closing variant sets.
2. Translate as a set so the result reads natively; keep the five-part structure, the word limit, and every hard rule in `docs/04-letter-rules.md`.
3. Register the language against its markets in config (`language_by_market`).
4. Extend the quality gate's snooping and hype word lists with equivalents in the new language, and gate-test three sample letters before the first batch.
5. **The first version in any new language must be confirmed by the operator before it is used in a batch.** Machine-translated or agent-translated templates go out only after that confirmation; record the confirmation in the run log.

## Worked example (slots only)

This skeleton shows the slots, not sample content. The curly-brace values are what research and config supply for one specific company; none of them is reusable text.

```text
Subject: Wholesale enquiry: {product}

Hi {first_name},

I noticed {company} {observation}.

We manufacture {product} for wholesale and contract buyers. {product_value}

{closing}

Best regards,
{sender_name}
{sender_company}
```
