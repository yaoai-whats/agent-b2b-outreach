# 04 — Letter Rules

> Templates live in `templates/letter-templates.md`. Sender identity, product, and value points come from config. Fictional example: Guangzhou BrightTable Ceramics (fictional example), ceramic tableware sets.

## The structure formula: six skeletons, not one template

Every first-touch letter is built from one of six skeletons in `templates/letter-templates.md` (standard introduction, question opening, three-line short, buyer ledger, seasonal scenario, direct supply). The skeletons differ in paragraph order, length band, and call to action, so letters across a batch do not share one structural fingerprint. Within a skeleton, phrase-level spintax varies the wording block by block. The builder narrows the skeleton pool by buyer type, then picks one skeleton per company by a hash of the company domain: the same company always gets the same skeleton, and a batch is spread across the pool, never put on one skeleton.

Every skeleton keeps the same five parts, in an order that differs by skeleton:

1. **Greeting** — "Hi {first_name}," using the cleaned first name (see greeting rules below). No name you can trust: "Hi there,".
2. **Two-point personalisation** — the personalisation carries **two** specific points, not one: (a) one concrete fact about the recipient's company drawn only from public information (a public product range, a public programme, a public announcement), and (b) one "why you, why now" signal that makes this the moment to write — they sell an adjacent category, they just launched a new range, they are expanding channels or locations, they exhibit at a fair you attend. Both points live in the row's researched `observation` (written at enrichment time, fact clause plus signal clause); together they must be specific enough that the sentences could not be pasted into another company's letter. A row without a researched observation is not ready: the builder refuses to write the letter, and no generic filler is ever substituted. Nothing about the company may be stated that does not come from the observation or the operator's own product material — personalisation is assembled from facts, never invented.
3. **Who you are** — one sentence: sender company plus product (see config).
4. **One buyer-side value sentence, social-proof first** — what the product does for *their* business, phrased the way a comparable buyer experiences it ("home goods importers stock it because one design sells across everyday, gifting, and restocking") rather than as a list of product features. Reciting product advantages one by one is the single most penalised pattern in large-sample cold-email data; keep at most the one advantage that matters most to this recipient.
5. **One low-pressure, concrete offer as the call to action** — an offer to send something specific: the catalogue section or sample set for *their* category, with the relevant price band named. One ask only. Never ask for a meeting, a call, or "15 minutes" in a first letter — offer something instead.

Then a plain sign-off: sender name and sender company (see config), one line each. No phone number in the signature unless config explicitly includes one.

**Subject line:** 2–4 words, carrying one specific detail about their company (their range, programme, or market), never a generic pitch phrase.

**Format limits:** plain text only, no images, no attachments. First touches target **50–100 words** in 3–4 sentences with **exactly one question** in the whole letter; the hard cap is 130 words (the quality gate enforces the cap; skeleton length bands sit inside it, and the shortest skeletons are for follow-up-style brevity, not an excuse to pad a first touch).

## Fill-in template

The working skeletons with placeholders (`{first_name}`, `{company}`, `{company_short}`, `{observation}`, `{obs_first}`, `{product}`, `{product_value}`, `{sender_name}`, `{sender_company}`, and others) are in `templates/letter-templates.md`, together with a channel-partner skeleton set for platforms, buying groups, and distributor networks. `scripts/letter_builder.py` fills the skeletons and picks the skeleton and the spintax options by company-domain hash, so the same company always gets the same letter and different companies do not receive structurally identical letters.

## Hard rules (a violation means rewrite)

1. **No em dashes or en dashes** anywhere in subject or body. Use commas or colons. (Automated check.)
2. **No snooping language.** Never mention trade records, bills of lading, shipment counts, or any data source the recipient did not publish for you. The observation sentence may only say what is visible from public channels, in the form "carries tableware and housewares lines", never "imported 40 containers last year". The configurable word list lives in `scripts/quality_gate.py`.
3. **Clean greeting.** Use the extracted first name only: strip titles, honorifics, bracketed notes, and role text from the contact field. Two named contacts become "A and B". No reliable name: "Hi there,". Never guess a name.
4. **No hype or pressure phrases.** No superlative pricing claims, no urgency, no generic salutations to a title instead of a person. (Automated check, word list configurable.)
5. **No unverifiable claims.** Do not claim certifications, exclusivity, stock positions, or existing-customer relationships you cannot prove. (Automated check, word list configurable.)
6. **Personalisation comes from facts only.** Every statement about the recipient's company must trace to the row's `observation` (itself built only from what the company publishes) and every statement about your own offer to config or operator-approved material. Never invent a detail, a number, a customer, or a signal to make a letter feel personal — a fabricated "fact" is worse than a plain letter, and the profile/observation separation in `docs/01-methodology.md` exists to keep internal research out of the letter entirely.

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
- [ ] Body at or under the word limit (default 130 words including subject headroom); first touches aim for 50–100 words
- [ ] Exactly one call to action, and it is a concrete offer (their category, price band named), not a meeting or call request
- [ ] Exactly one question in the whole letter
- [ ] Subject line is 2–4 words and carries a specific detail about their company
- [ ] Personalisation has both points: one company fact and one "why now" signal, each traceable to the row's observation
- [ ] Value is carried by one social-proof or buyer-side sentence, not a recital of product features
- [ ] Observation uses public information only
- [ ] Recipient address label is `hunter_valid` or `public_confirmed` (see `docs/03-email-verification.md`)
- [ ] Company is not blocklisted, excluded, already contacted, or an existing customer

A letter that fails any item does not join the batch. The batch report lists failures by company and reason so the template or data can be fixed before the next round.
