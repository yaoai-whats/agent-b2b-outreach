# AGENTS.md — Operating Map for the Executing Agent

This file is the entry point for the executing agent. Read it first, in full, before doing any work in this repository.

> All business parameters (product, markets, sender identity, caps, rules) live in the private config file created from `config/config.example.json`. In this document and in every prompt, "see config" means: read the value from that config file. Never invent a business parameter that the config does not provide, and never hard-code one into a prompt, script run, or letter.

## Reading order

1. `AGENTS.md` (this file) — map, stage contracts, hard rules.
2. `prompts/00-onboarding.md` — if `config/config.json` does not exist yet, run Step 0 first and do nothing else until it is done.
3. `config/config.example.json` and the operator's private `config/config.json` — every business variable.
4. `docs/01-methodology.md` — the ten-step method behind the pipeline.
5. The stage prompt you are about to run (`prompts/01-scan.md` … `prompts/05-followup.md`).
6. The supporting doc for that stage (scoring: `docs/02-tier-scoring.md`; verification: `docs/03-email-verification.md`; letters: `docs/04-letter-rules.md`; follow-ups: `docs/05-followup-policy.md`; exclusions and failsafes: `docs/06-exclusions-and-failsafes.md`).

## Step 0 — Onboarding (runs once, before everything)

| Step | Prompt | Reads | Writes | Done when |
|---|---|---|---|---|
| 0. Onboarding | `prompts/00-onboarding.md` | The operator's answers (interview) | `config/config.json`, `config/blocklist.json` | Every required field holds the operator's real value (never an example value), the self-check passes, and the operator has seen the configuration checklist |

No stage runs before Step 0 is complete. Business parameters are asked, not assumed: if the operator has not provided a value, it stays empty and is reported as missing.

## Five-stage map

| Stage | Prompt | Reads | Writes | Done when |
|---|---|---|---|---|
| 1. Scan | `prompts/01-scan.md` | config, blocklist, existing `data/leads.jsonl` | New deduplicated rows in `data/leads.jsonl` | Candidates stored with source, evidence link, and initial tier inputs |
| 2. Enrich | `prompts/02-enrich.md` | Rows missing a verified contact | Decision-maker, email pattern, verification status on the same rows | Each worked row has a verified useful email, or is marked unreachable with a reason |
| 3. Batch | `prompts/03-batch.md` | Ranked reachable rows, `templates/letter-templates.md` | Letter drafts that pass `scripts/quality_gate.py`; send log entries | Batch respects `daily_send_cap` (see config), every letter passed the gate |
| 4. Inbox | `prompts/04-inbox.md` | Mailbox replies, bounces, unsubscribes | Feedback entries, lead status updates, breaker state | Every new reply and bounce is classified and written back |
| 5. Follow-up | `prompts/05-followup.md` | Sent rows with no reply | Follow-up drafts (new content only), tracker updates | No company exceeds `followup_max` (see config); interval respected (see config) |

Shared scripts:

- `scripts/_config.py` — the one config loader every other script uses. It reads `config/config.json` (falling back to `config/config.example.json`); command-line arguments override config values.
- `scripts/web_search.py` — unified search layer (see “Capability requirements” below). All discovery and exact-match verification should go through it.
- `scripts/domain_check.py` — MX lookup and accept-all probe for a domain (the two checks `docs/03-email-verification.md` requires before candidate work), pure standard library.
- `scripts/hunter_pool.py` — Hunter API calls with key rotation. Keys come from the environment variable named in config (`hunter_api_keys_env`). Never print a key.
- `scripts/quality_gate.py` — deterministic letter checks. A letter that fails the gate does not ship.
- `scripts/letter_builder.py` — builds a letter from the templates with per-company variant rotation. The observation sentence comes from the lead row's researched `observation` field; the script never invents one.
- `scripts/send_mail.py` — sends one gate-passed letter over SMTP. Credentials come from environment variables only (`SMTP_HOST`/`SMTP_PORT`/`SMTP_USER`/`SMTP_PASS`/`SMTP_FROM`); it refuses unverified recipients, enforces the daily cap and the bounce circuit breaker, and is a dry run unless `--send` is given.
- `scripts/read_inbox.py` — reads the sending mailbox over IMAP (`IMAP_HOST`/`IMAP_USER`/`IMAP_PASS`), read-only, and classifies replies, bounces, and unsubscribes into the feedback log.
- `scripts/dedupe.py` — merges duplicate lead rows on domain, merging emails and reporting conflicts; writes back only with `--write`.
- `scripts/render.py` — renders `leads.jsonl` into a ranked Markdown table.
- `scripts/build_tracker.py` — builds the follow-up tracker CSV from lead, send, and feedback state.

## Capability requirements & the search layer (important)

The executing agent needs four capabilities: web search, opening and reading web pages, running Python, and reading/writing files. If any is missing, say in the run log which stage is degraded.

- **Route all search through `scripts/web_search.py`** — finding companies, finding decision-makers, exact-match verification of candidate emails (the `exact` subcommand), and fetching pages (the `fetch` subcommand). Do not rely on the host agent's built-in search: backends differ widely in coverage, especially for local-language role keywords and small directories. The script uses the first configured provider key: `SERPER_API_KEY` (Serper, Google index — the most reliable for exact email matching) → `TAVILY_API_KEY` → `BRAVE_API_KEY`. Any one is enough; all three have free tiers.
- **If no search key is configured**, the script exits with code 3 and a FALLBACK notice. Continue with the agent's built-in search, note “search layer degraded” in the run log, and downgrade exact-search verification by one level (a snippet alone does not count as public confirmation — open the page).
- Verify customs-data sites, directories, and deep site pages (e.g. /impressum) against the original page via `web_search.py fetch` or the agent's browser; never conclude from a search snippet alone (see evidence rules in `docs/02-tier-scoring.md`).

## Hard rules (generic, always apply)

1. **Public information only.** Use what companies publish themselves. Record a source and an evidence link for every fact. Mark anything uncertain as unverified; never fabricate a name, email, or buying signal.
2. **Blocklist and exclusions first.** Before scanning, enriching, or sending, check `config/blocklist.json`, `excluded_markets`, and `exclusion_rules` (see config). A match is skipped and the reason is recorded. Never argue with an exclusion.
3. **Verification ladder, in order.** Free evidence first (public exact-match, published address), paid verification last, and only for high-value tiers (see config and `docs/03-email-verification.md`). An accept-all domain can never be treated as verified.
4. **Useful email only.** A row counts as reachable only with a useful email as defined in `docs/03-email-verification.md`. Low-value functional mailboxes do not make a company reachable.
5. **Quality gate is a gate.** No em dashes, no snooping language, no hype claims, clean greeting, length within limits. Fail means fix or drop, never override.
6. **Bounce circuit breaker.** If bounces reach the thresholds in config (default: 3 or more in one day, or 15% or more of the last 20 sends), stop all sending, report, and wait for a human. See `docs/06-exclusions-and-failsafes.md`.
7. **Sending caps and timing.** Never exceed `daily_send_cap` (see config). Spread sends across the recipient's local business hours on business days.
8. **Follow-up discipline.** Interval and maximum count come from config (defaults: 30 days, at most 2 follow-ups). Every follow-up must carry genuinely new content. A bare nudge is not a follow-up.
9. **Secrets stay in the environment.** API keys and credentials are read from environment variables only. Never write them to files, logs, letters, or chat output.
10. **Write everything back.** Every send, bounce, reply, and unsubscribe updates the lead row and the feedback log in the same run. The next round depends on it.

## Actions that always need human confirmation

The executing agent must stop and ask a human before:

- Quoting or negotiating a price, discount, or payment term in any reply.
- Promising stock availability, a delivery date, exclusivity, or a private-label commitment.
- Sending a catalogue or price list that the operator has not approved for release.
- Replying substantively to any prospect reply (classification and drafting are fine; sending the reply is not, unless the operator has explicitly enabled auto-reply for that category).
- Re-contacting a company that unsubscribed, hard-bounced, or asked not to be contacted.
- Changing config values that widen scope: new markets, higher send caps, weaker exclusion rules.
- Spending paid verification credits outside the tiers allowed in config.

## Fictional example

Examples in this repository use Guangzhou BrightTable Ceramics (fictional example), a fictional exporter of ceramic tableware sets selling to tableware wholesalers, home goods importers, department store buyers, and hotel supply distributors. Treat every example name, company, and address as fictional.
