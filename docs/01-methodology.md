# 01 — Methodology: The Ten-Step Method

> Fictional example: Guangzhou BrightTable Ceramics (fictional example), a fictional exporter of ceramic tableware sets. Buyer examples: tableware wholesalers, home goods importers, department store buyers, hotel supply distributors. Substitute your own offer everywhere.

The one-sentence version: **find people who are already buying, widen the net to people who plausibly buy, filter down to people you can actually reach, then feed the results back so the next round is more accurate.**

Standing rules for every step: record a source and a confidence level for each fact; mark uncertain items as unverified instead of guessing; spend paid-tool credits only where they matter most; use public information only.

## Step 1 — Write down what your ideal customer looks like (ICP)

Searching before defining the target returns hundreds of companies, half of them wrong. Answer these eight questions first; the answers become your config file.

| # | Question | Why it matters | Fictional example answer |
|---|---|---|---|
| Q1 | What do you sell? Product name plus 3 to 5 category keywords, plus HS codes if known. | Drives keywords and trade-data queries. | Ceramic tableware sets; keywords: ceramic tableware, porcelain dinnerware sets, stoneware tableware; HS 6912 |
| Q2 | Who buys from you? Importers, wholesalers, distributors, retailers, brands, end-business buyers (multi-select). | Decides where to look. Importers live in trade data; retailers live on maps. | Tableware wholesalers, home goods importers |
| Q3 | Which countries or regions do you want to sell into? | Sets the search scope. | United States, Germany, Australia, United Arab Emirates |
| Q4 | Which markets or company types are a definite no? | Excluding early is cheaper than filtering late. | See `excluded_markets` and `exclusion_rules` in config |
| Q5 | What does the ideal company look like? Size, purchase volume, product-line traits. | Judges whether a company is worth deep research. | Regular tableware importer with a wholesale catalogue and a housewares range |
| Q6 | What makes you say "this is the one"? | These become your fit signals for scoring. | A dedicated tableware category page, a B2B wholesale portal, hotel supply contracts |
| Q7 | Who do you want to reach? Owner, purchasing lead, category buyer, and so on. | Sets the people-search direction. | Owner or purchasing manager; owners decide directly in smaller firms |
| Q8 | Rate each signal 1 to 5: import record, category fit, company size, website and catalogue quality, reachable decision-maker. | Becomes the scoring weight table. No signal is first for every industry. | Import record 5, fit 5, size 3, catalogue 3, reachable contact 4 |

Output: one ICP table, stored as config. Every later step reads it instead of asking again.

## Step 2 — Start with people who are already buying (trade data)

- Where: public customs and bill-of-lading databases (for example ImportYeti for US sea freight; regional equivalents elsewhere). Free tiers are enough to start.
- How: search by HS code, then by product keyword, then reverse-lookup a company name to see what else it imports.
- Capture: company name, address, shipment count, most recent import date, tariff code, and the product description as written on the record.
- Use: rank by shipment count × description relevance. The top of that list seeds the Tier S candidate pool.
- Also use trade data as *post-validation*: re-check companies already selected in later steps. A record strengthens the tier; no record is not a penalty (many buyers import through intermediaries or by air or land).
- Note the current supplier and origin country when visible. Knowing who a buyer buys from today is legitimate public context for positioning, but it must never be quoted back to the buyer in a letter (see `docs/04-letter-rules.md`).
- Limits: coverage is partial by transport mode and region, and descriptions are written by shippers and can be wrong. Treat an import record as a strong bonus signal, never as the only standard.

## Step 3 — Widen the net: five discovery channels

Run the channels in parallel; everything lands in one store (Step 4).

- **Channel A — Maps.** Search "buyer category × city" (for example "tableware wholesaler × Chicago") with a maps scraper or manually. Captures name, address, phone, website, category. Best for local distributors and retailers, not for importers.
- **Channel B — B2B directories.** Search category keywords on trade directories for your markets. Captures name, website, business description.
- **Channel C — Trade-show exhibitor lists.** Public exhibitor lists from relevant fairs in your sector. Warning: lists mix buyers with competitors. A company that manufactures or owns a brand in your core category is a competitor: file it in an intelligence pool, never in the outreach pool.
- **Channel D — Structured web search.** Build queries as "product + country + buyer type", then verify on the company's own website that the business is genuinely related before storing anything.
- **Channel E — Competitor and adjacent-brand distribution networks.** Search for a known brand's distributors and stockists ("brand + distributor + country", brand dealer pages). Distributors already selling adjacent products are pre-validated buyers. Only a company that makes or owns a competing core product counts as a competitor; a reseller of similar products is a customer. Note exclusivity where stated: an exclusive dealer needs care, a multi-brand dealer is usually the better target.

## Step 4 — Deduplicate into one record per company

- Primary key: website domain. No website: fuzzy-match on company name plus country.
- Merge fields from all sources into the single record; when sources conflict, keep both values with their sources rather than silently picking one.
- Every later round appends and updates. There is one living database (`data/leads.jsonl`), not a new spreadsheet per batch.

## Step 5 — Find the person, check the domain, then build the email

Order matters. Do these in sequence:

1. **Find the person, website first.** A company's own site is the highest-yield source: contact, team, about, and management pages; legal-notice pages where local law requires them (they often carry a name and address); catalogue PDFs, which often carry contact cards. Then public professional profiles and press releases. Search with local-language job titles where relevant (for example purchasing terms in the market's language), not only English titles. Target the roles from Q7. Record name, title, and an evidence link; missing any of the three means "unverified".
   Run people searches through the unified search layer (`scripts/web_search.py search`) with concrete templates: `site:linkedin.com/in "<company name>" <title>`, `"<company name>" <title>`, and `<company name> <title> <city or country>`. Prepare the title words in the market's language, not only English — the roles from Q7 govern which titles to use, translated where the market expects it (examples — German: Geschäftsführer, Einkaufsleiter, Einkäufer; French: Directeur des achats, Responsable achats, Acheteur). LinkedIn is used only through what search results expose publicly — name, title, company. Never log in to LinkedIn, and never fetch linkedin.com pages directly.
2. **Check the domain (two separate checks).** (a) MX lookup: does the domain run mail at all? No MX means no business mailbox; stop. (b) Accept-all probe: does the domain accept every address? An accept-all domain says yes to everything, so a "verified" result on it proves nothing. Having MX records tells you nothing about accept-all status; the two checks are independent.
3. **Build the email candidate last.** Use, in order: a published address; an email-finder tool (name plus domain); domain OSINT collection; and pattern inference, where a pattern counts as established only when at least two real, public addresses at the same domain share it (for example two published `first.last@` addresses). Never guess a pattern from a single example.

If no email can be found, keep the company with its fallback routes (contact form, phone, professional-network message). Small companies are often reachable through a form.

## Step 6 — Verify and label honestly

Verify with an email verifier or an SMTP-level check, and label every address in one of five states (full definitions in `docs/03-email-verification.md`):

- `hunter_valid` or equivalent: verifier says deliverable and the domain is not accept-all.
- `public_confirmed`: the exact address appears on a public page or document.
- `unverified`: inferred, not yet checked. Never send to it.
- `invalid`: confirmed undeliverable. Drop it.
- `accept_all_unconfirmed`: domain accepts everything; verification cannot confirm this specific mailbox. Do not send.

An SMTP-level accept is the strongest pre-send signal available, but it is not a delivery guarantee. Real delivery truth comes from Step 10 bounce data.

## Step 7 — Score and tier

Score three dimensions separately (fit, contactability, evidence) using the weights from Q8, then assign Tier S, A, B, or C. A company with a huge import record but only a generic inbox and no decision-maker is not Tier S. A company whose evidence comes only from a search snippet is capped below the top tier. Full rules: `docs/02-tier-scoring.md`.

## Step 8 — Human spot-check

Manually review 10 to 20 percent of Tier S before outreach: open the website, skim recent news, confirm the fit. Borderline cases (possible competitor, thin information) are decided by a human, not by the score.

## Step 9 — Write and send the first letter

- Formula: greeting with a clean first name + one specific observation drawn only from public information (their public range, a public announcement) + who you are + one buyer-side value sentence + one low-pressure call to action (an offer to send a catalogue). Plain text, at most 130 words. Letters use six skeletons plus phrase-level spintax (see `docs/04-letter-rules.md` and `templates/letter-templates.md`): the skeleton pool narrows by buyer type, one skeleton is picked per company by domain hash so the same company always gets the same skeleton, and a row without a researched observation is refused, never filled with a generic sentence.
- Hard rules and the quality gate: see `docs/04-letter-rules.md`. Every letter passes `scripts/quality_gate.py` before it can be sent.
- Choose the letter language by market convention: use the local business language where your sector expects it and you can write it correctly; use English where import trade in that market normally runs in English. Keep the same structure and hard rules in every language.
- Sending: highest-ranked uncontacted companies first, within the daily cap in config, spread across recipient-local business hours, with the bounce circuit breaker armed (see `docs/06-exclusions-and-failsafes.md`).

**Two fields, two audiences.** Every lead row carries two different company descriptions, and they must never be mixed. `profile` is the internal research note (buyer type, location, import evidence, fit judgement): it informs scoring and selection, and it is never shown to a recipient. `observation` is the letter-ready clause, written once at enrichment time in the market's letter language, using only what the company itself has published. The letter builder reads `observation` only, so trade data and internal judgements cannot leak into a letter by accident.

## Step 10 — Feed the results back

Record the outcome of every send: delivered, opened (if known), replied, unsubscribed, hard-bounced. Then:

- Hard-bounced address: blocklist it and downgrade the evidence behind it.
- Traits shared by companies that reply (a role, a category, a market): raise their weight in the Step 1 table.
- Domains where accept-all addresses keep bouncing: downgrade that pattern for everyone.
- Review monthly. This feedback loop, not any single list, is what makes the system improve.

## 附：十步速览（中文）

1. 用八问写清理想客户画像，落成配置。2. 先查贸易数据找“正在买的人”。3. 五渠道撒网：地图、目录、展会名录、结构化搜索、竞品分销网络。4. 按域名去重，一家一档。5. 先找人、再验域名、最后拼邮箱，顺序不能反。6. 验证后按五档如实标注。7. 契合度、可触达度、证据强度三维打分分档。8. 最高档抽样人工复核。9. 按公式写信，过质检门后在上限内发送。10. 把送达、退信、回复全部回写，月度复盘调权重。
