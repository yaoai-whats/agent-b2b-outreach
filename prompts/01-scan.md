# Prompt 01 — Scan (Stage 1: Find Candidate Companies)

You are the executing agent running Stage 1 of the B2B Outreach System in this repository.

## Before you start

1. Read `AGENTS.md` in full.
2. Read the operator's private config (created from `config/config.example.json`). Every business parameter for this run comes from there: product, product keywords, HS codes, buyer categories, target markets, excluded markets, exclusion rules, fit signals. Where this prompt says "see config", use that file. Do not invent parameters.
3. Read `docs/01-methodology.md` Steps 1 to 4 and `docs/06-exclusions-and-failsafes.md`.

## Inputs

- Private config (see above)
- `config/blocklist.json` (operator's private blocklist)
- `data/leads.jsonl` (existing database; may be empty on the first run)

## Task

1. Pick the market × buyer-category combinations for this run from config, rotating away from combinations covered in recent runs (check `source` and `added_at` in the existing data).
2. Start with buyers who are already buying: query public trade data by the HS codes and product keywords in config. Record shipment counts, recency, and the product description as written.
3. Widen the net through the five channels in `docs/01-methodology.md` Step 3: maps, B2B directories, trade-show exhibitor lists, structured web search, and competitor or adjacent-brand distribution networks. **Run all searching and page reading through `scripts/web_search.py` (`search` / `exact` / `fetch`); if no search API key is configured, follow the fallback rules in AGENTS.md and note the degradation in the run log.**
4. Classify every company found as customer, competitor, or undecided. Competitors (they manufacture or own a brand in the core category, see config) go to an intelligence list in your report only, never into `data/leads.jsonl` as outreach candidates. Resellers of similar products are customers.
5. Apply all three exclusion layers before storing anything: blocklist, excluded markets, exclusion rules (see config). Record the reason for every skip in your report.
6. Deduplicate by website domain (fallback: company name plus country) against the existing database and within this run. Merge new facts into the existing row instead of creating a duplicate.
7. For each stored company, capture: company name, domain, country, buyer category, business profile in one or two sentences, source channel, source URL, discovery date, import signal if any, and the raw inputs the scoring step needs.

## Output

- Appended and merged rows in `data/leads.jsonl`, following the field reference in `data/README.md`.
- A run report: combinations covered, companies found per channel, stored, merged, skipped (with reasons by layer), competitors set aside, and any combination that returned nothing.

## Hard limits

- Public information only. Verify business relevance on the company's own website before storing a web-search or directory result.
- Never store a company from an excluded market or matching an exclusion rule (see config).
- Do not look for personal emails in this stage; that is Stage 2.
- Do not send anything.
