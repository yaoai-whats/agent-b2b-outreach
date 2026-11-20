# Prompt 02 — Enrich (Stage 2: Find People, Verify Emails)

You are the executing agent running Stage 2 of the B2B Outreach System in this repository.

## Before you start

1. Read `AGENTS.md` in full.
2. Read the operator's private config (created from `config/config.example.json`): decision-maker titles, target tiers for paid verification, verification cooldown, daily enrichment limit. Where this prompt says "see config", use that file.
3. Read `docs/01-methodology.md` Steps 5 and 6, `docs/03-email-verification.md`, and `docs/06-exclusions-and-failsafes.md`.

## Inputs

- `data/leads.jsonl` — work on rows that lack a verified useful email, highest tier first, up to the per-run limit in config.
- `config/blocklist.json` — re-check before working each row.

## Task

For each selected company:

1. **Re-check exclusions.** Blocklist, excluded market, exclusion rule (see config). A match stops work on the row; record the reason.
2. **Find the decision-maker, website first.** Work the company's own site (contact, team, about, legal-notice pages, catalogue PDFs), then public professional profiles and press releases. Use local-language job titles where relevant. Target the roles in config. Record name, title, and evidence URL. Missing evidence means the contact stays unverified.
3. **Run the two domain checks.** MX present? Accept-all or not? Record both results separately; one never implies the other.
4. **Establish the email pattern.** Collect real published addresses at the domain. Two or more sharing a pattern establishes it; store it as `email_pattern` on the row.
5. **Climb the verification ladder** (`docs/03-email-verification.md`): exact public match, then syntax and MX screen, then paid verification via `scripts/hunter_pool.py` only for the tiers allowed in config. Respect the per-company cooldown for paid "no result" outcomes.
6. **Label honestly.** Set `email_status` to exactly one of `hunter_valid`, `public_confirmed`, `unverified`, `invalid`, or `accept_all_unconfirmed`. Set `useful_email` only when the address is useful per `docs/03-email-verification.md` and its label permits sending.
7. If no useful email can be verified, record the fallback routes found (contact form, phone, professional profile) and mark the row for a later enrichment round.

## Output

- Updated rows in `data/leads.jsonl` (contact, email pattern, domain check results, email labels, useful email, fallback routes).
- A run report: rows worked, newly reachable companies by tier, paid credits spent by endpoint, rows parked and why (accept-all, no result, no MX, no decision-maker found).

## Hard limits

- Never label an accept-all address as verified, and never set it as a useful email.
- Never spend paid verification credits on tiers excluded in config, and never re-check a company inside its cooldown window.
- API keys come from the environment only (see config for the variable name). Never print a key.
- Do not write or send letters in this stage.
