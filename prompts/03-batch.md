# Prompt 03 — Batch (Stage 3: Build and Send a Letter Batch)

You are the executing agent running Stage 3 of the B2B Outreach System in this repository.

## Before you start

1. Read `AGENTS.md` in full.
2. Read the operator's private config (created from `config/config.example.json`): sender identity, daily send cap, value points, language mapping, bounce breaker thresholds. Where this prompt says "see config", use that file.
3. Read `docs/04-letter-rules.md`, `docs/03-email-verification.md`, and `docs/06-exclusions-and-failsafes.md`.
4. Check the breaker state: if the circuit breaker recorded in the feedback log is tripped, stop and report. Do not prepare a batch.

## Inputs

- `data/leads.jsonl` — candidates are rows that are reachable (useful email labelled `hunter_valid` or `public_confirmed`), never contacted, and not excluded.
- `templates/letter-templates.md` — the letter templates.
- `config/blocklist.json` — final check before selection.

## Task

1. **Select** up to the daily send cap (see config), highest tier first, then highest fit score. Skip and record: blocklist or exclusion matches, existing customers, companies already contacted, companies whose only address is accept-all or unverified.
2. **Write one letter per company** with `scripts/letter_builder.py` and the templates: a specific observation from public information only, one buyer-side value sentence (see config for value points), one call to action. The builder assigns one of six skeletons per company (see `templates/letter-templates.md`: pool narrows by buyer type, picked by company-domain hash, same company keeps its skeleton); spread the batch across the pool and never put a whole batch on one skeleton. A row without a researched observation is not ready: generate the observation first and write it back to the lead row, never let the builder invent one. Choose the letter language by the market mapping in config.
3. **Gate every letter** with `scripts/quality_gate.py`. A failing letter leaves the batch; list it in the report with the failure reasons. Never hand-override a gate failure.
4. **Brief before sending.** Produce a batch brief: for each letter, company, country, tier, recipient name and role, recipient address and its verification label, and the observation used. The brief informs the operator; sending then proceeds under the operator's standing instruction unless the operator stops a letter or the batch.
5. **Send** with `scripts/send_mail.py` in batch mode, spread across each recipient's local business hours, within the cap (see config). The script sends over SMTP with credentials from environment variables (`SMTP_HOST`/`SMTP_PORT`/`SMTP_USER`/`SMTP_PASS`/`SMTP_FROM`, loaded from the repo-root `.env` when present). Run the batch dry first (the default) to review every letter: `python3 scripts/send_mail.py --batch --lead data/leads.jsonl`. Then run it again with `--send`. Batch mode processes every sendable row in order (optionally narrowed to one verification label with `--to-status`), builds each letter, and re-checks the recipient's verification label, the quality gate, the daily cap, and the bounce circuit breaker for every letter; letters are spaced by `--interval` seconds (default 60) plus a random 0–30 second jitter. A failed check refuses that letter with a reason and the batch moves on; reaching the daily cap or tripping the bounce breaker stops the whole batch and prints why. A refusal is never overridden.
6. **Verify and record.** After sending, confirm each letter appears in `data/send-log.jsonl` and `data/send-state.json` (both written by `scripts/send_mail.py`), then write back to `data/leads.jsonl`: company, address, date and time, template variant, letter language.

## Output

- Sent letters, one per selected company, all gate-passed.
- Batch brief (before sending) and batch report (after): selected, sent, gate failures with reasons, skips with reasons, running bounce rate for the breaker window.

## Hard limits

- Never exceed the daily send cap (see config), and never send to an address whose label is not `hunter_valid` or `public_confirmed`.
- No em dashes, no snooping language, no hype claims, ever. The gate decides.
- If bounces during sending reach the breaker thresholds (see config), stop mid-batch and hand over to Stage 4 reporting.
- Never attach files or include pricing beyond what the operator has approved for release.
