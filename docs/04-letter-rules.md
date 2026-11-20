# 04 — Letter Rules

> Templates live in `templates/letter-templates.md`. Sender identity, product, and value points come from config. Fictional example: Guangzhou BrightTable Ceramics (fictional example), ceramic tableware sets.

## The structure formula

Every first-touch letter has exactly five parts, in this order:

1. **Greeting** — "Hi {first_name}," using the cleaned first name (see greeting rules below). No name you can trust: "Hi there,".
2. **One specific observation** — a single sentence about the recipient's company drawn only from public information: a public product range, a public programme, a public announcement. One observation, not a list.
3. **Who you are** — one sentence: sender company plus product (see config).
4. **One buyer-side value sentence** — what the product does for *their* business (margin, sell-through, low breakage or returns, year-round demand, one line covering several of their channels). Frame benefits from the buyer's side, never as a bare list of product features.
5. **One low-pressure call to action** — an offer to send a catalogue or a small sample set. One ask only.

Then a plain sign-off: sender name and sender company (see config), one line each. No phone number in the signature unless config explicitly includes one.

**Format limits:** plain text only, no images, no attachments, about 120 words maximum in the body.

## Fill-in template

The working template with placeholders (`{first_name}`, `{company}`, `{observation}`, `{product_value}`, `{sender_name}`, `{sender_company}`, and others) is in `templates/letter-templates.md`, together with a channel-partner variant for platforms, buying groups, and distributor networks. `scripts/letter_builder.py` fills the template and rotates subject and phrasing variants by company-domain hash, so the same company always gets the same variant and different companies do not receive byte-identical letters.

## Hard rules (a violation means rewrite)

1. **No em dashes or en dashes** anywhere in subject or body. Use commas or colons. (Automated check.)
2. **No snooping language.** Never mention trade records, bills of lading, shipment counts, or any data source the recipient did not publish for you. The observation sentence may only say what is visible from public channels, in the form "carries tableware and housewares lines", never "imported 40 containers last year". The configurable word list lives in `scripts/quality_gate.py`.
3. **Clean greeting.** Use the extracted first name only: strip titles, honorifics, bracketed notes, and role text from the contact field. Two named contacts become "A and B". No reliable name: "Hi there,". Never guess a name.
4. **No hype or pressure phrases.** No superlative pricing claims, no urgency, no generic salutations to a title instead of a person. (Automated check, word list configurable.)
5. **No unverifiable claims.** Do not claim certifications, exclusivity, stock positions, or existing-customer relationships you cannot prove. (Automated check, word list configurable.)

## Greeting extraction rules

- Input is the raw contact field, which may contain titles, notes, or two people.
- Take the first person, drop bracketed or parenthesised notes, drop leading honorifics, keep the given name (plus family name only where local convention expects it).
- If the field is empty, marked unverified, or contains no usable name, fall back to the generic greeting for the letter's language.
- `scripts/letter_builder.py` implements this as `extract_name()`; `scripts/quality_gate.py` rejects greetings that still contain brackets or title residue.

## Adding another language version

1. Duplicate the English template structure exactly: same five parts, same hard rules, same word limits.
2. Translate the observation variants and closings as a set, not sentence by sentence, so each language reads natively.
3. Add the language to the market-to-language mapping in config; choose languages by market convention (use the local business language where your sector expects it and you can write it correctly; English is the norm for import trade in many markets).
4. Run the quality gate on sample letters in the new language before its first batch. The dash, length, and greeting checks are language-independent; extend the snooping and hype word lists with the new language's equivalents.

## Quality checklist (enforced by `scripts/quality_gate.py`)

- [ ] No em dash or en dash in subject or body
- [ ] No snooping words (configurable list)
- [ ] No hype or pressure phrases (configurable list)
- [ ] No unverifiable claim phrases (configurable list)
- [ ] Greeting is a clean name or the generic fallback; no brackets, no titles
- [ ] Body at or under the word limit (default 130 words including subject headroom)
- [ ] Exactly one call to action
- [ ] Observation uses public information only
- [ ] Recipient address label is `hunter_valid` or `public_confirmed` (see `docs/03-email-verification.md`)
- [ ] Company is not blocklisted, excluded, already contacted, or an existing customer

A letter that fails any item does not join the batch. The batch report lists failures by company and reason so the template or data can be fixed before the next round.
