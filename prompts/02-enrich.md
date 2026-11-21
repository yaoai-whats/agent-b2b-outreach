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
   Run people searches through `scripts/web_search.py search` with concrete templates, varying the title word across the roles in config and their local-language equivalents (prepare the equivalents for the target market's language; examples — German: Geschäftsführer, Einkaufsleiter, Einkäufer; French: Directeur des achats, Responsable achats, Acheteur):
   - `site:linkedin.com/in "<company name>" <title>`
   - `"<company name>" <title>`
   - `<company name> <title> <city or country>`
   LinkedIn boundary, no exceptions: LinkedIn is used only through what search results expose publicly — name, title, company. Never log in to LinkedIn, and never fetch linkedin.com pages themselves.
3. **Fill remaining gaps with Hunter Domain Search.** If the website and search paths above still leave the decision-maker, or any published address at the domain, missing — and the company's tier is allowed paid spend in config — run `python3 scripts/hunter_pool.py domain-search <domain>`. Record the returned people (name, position) and addresses on the row with the Domain Search result as their evidence; the addresses also count as real-address samples for pattern establishment in step 5. A Domain Search return is a candidate source, not a confirmation: every returned address still climbs the ladder in step 6 before it may carry a label above `unverified`. Cost discipline: cache the result per domain, never call it again for the same domain inside the verification cooldown set in config, and never call it for tiers excluded from paid spend in config.
4. **Run the two domain checks.** MX present? Accept-all or not? Record both results separately; one never implies the other.
5. **Establish the email pattern.** Collect real published addresses at the domain (the company's own pages, catalogues, and Domain Search returns from step 3). Two or more sharing a pattern establishes it; store it as `email_pattern` on the row. `scripts/email_pattern.py detect` performs this check mechanically from known name/address pairs, and its `candidate` subcommand renders a candidate address from a name and an established pattern.
6. **Climb the verification ladder** (`docs/03-email-verification.md`): exact public match, then syntax and MX screen, then paid verification via `scripts/hunter_pool.py` only for the tiers allowed in config. Respect the per-company cooldown for paid "no result" outcomes.
7. **Label honestly.** Set `email_status` to exactly one of `hunter_valid`, `public_confirmed`, `unverified`, `invalid`, or `accept_all_unconfirmed`. Set `useful_email` only when the address is useful per `docs/03-email-verification.md` and its label permits sending.
8. If no useful email can be verified, record the fallback routes found (contact form, phone, professional profile) and mark the row for a later enrichment round.
9. **Write the observation the moment a row becomes reachable.** When this stage sets a useful email on a row that has no `observation` yet, write one and store it on the row: a single clause in the letter language for that market (see config), drawn only from what the company itself has published (its public range, programme, or channel activity) — for example "runs a dedicated tableware category with a B2B ordering portal for wholesale accounts". The letter builder consumes this field verbatim; a reachable row without an observation cannot be written to. Keep an existing observation unless it is plainly wrong.

## Output

- Updated rows in `data/leads.jsonl` (contact, email pattern, domain check results, email labels, useful email, fallback routes, observation for newly reachable rows).
- A run report: rows worked, newly reachable companies by tier, paid credits spent by endpoint, rows parked and why (accept-all, no result, no MX, no decision-maker found).

## Hard limits

- Never label an accept-all address as verified, and never set it as a useful email.
- The `profile` field is an internal research note: it may cite trade records and fit judgements and is never shown to a recipient. Never copy profile content into `observation`; the observation may only say what the company itself has published. The letter stage reads `observation` only — this separation is what keeps snooping data out of letters mechanically, not by anyone's care.
- Never spend paid verification credits on tiers excluded in config, and never re-check a company inside its cooldown window.
- API keys come from the environment only (see config for the variable name). Never print a key.
- Do not write or send letters in this stage.
