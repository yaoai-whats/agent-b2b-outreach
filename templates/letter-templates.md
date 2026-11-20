# Letter Templates

Fill-in templates for first-touch outreach. `scripts/letter_builder.py` fills these placeholders and rotates variants by company-domain hash. Sender identity, product, and value points come from config; never hard-code real values into this file.

> Fictional example values in the worked example: Guangzhou BrightTable Ceramics (fictional example), ceramic tableware sets.

## Placeholders

| Placeholder | Source | Notes |
|---|---|---|
| `{first_name}` | Cleaned contact name | First name only, titles and notes stripped. Falls back to the generic greeting when no name is trusted. |
| `{company}` | Lead row | Company name as the company writes it. |
| `{observation}` | Researched per company | One clause about their public range or programme, public information only. Example pattern: "carries tableware and housewares lines for wholesale accounts" |
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

Value-sentence guidance: pick the value point (see config) that matches the observation. For the fictional ceramics example: chip-resistant stoneware that survives freight and warehouse handling, one set design that sells across everyday dining, gifting, and hospitality restocking, and stable year-round demand rather than a single season.

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

We manufacture {product} for wholesale and contract buyers. {product_value} For a partner range, the practical points are consistent supply across the year, one line that fits several of your sellers' shelves, and packaging ready for mixed-channel distribution.

{closing}

Best regards,
{sender_name}
{sender_company}
```

Partner observation pattern: name the programme or range the partner publishes, for example "runs a housewares programme for independent retailers" — public information only, same rules as the main template.

## Adding another language version

1. Copy the main template, including subject, intro, and closing variant sets.
2. Translate as a set so the result reads natively; keep the five-part structure, the word limit, and every hard rule in `docs/04-letter-rules.md`.
3. Register the language against its markets in config (`language_by_market`).
4. Extend the quality gate's snooping and hype word lists with equivalents in the new language, and gate-test three sample letters before the first batch.

## Worked example (fully fictional)

```text
Subject: Wholesale enquiry: ceramic tableware sets

Hi Maria,

I noticed Harbour Table Co. carries tableware and housewares lines for wholesale accounts.

We manufacture ceramic tableware sets for wholesale and contract buyers. The stoneware is chip-resistant, so breakage in freight and storage stays low, and one set design sells across everyday dining, gifting, and hospitality restocking.

Could I send you our catalogue and wholesale terms?

Best regards,
Alex Rivera
Guangzhou BrightTable Ceramics
```

Harbour Table Co. and its contact are fictional examples, as is the sender.
