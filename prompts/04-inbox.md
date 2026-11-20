# Prompt 04 — Inbox (Stage 4: Process Replies, Bounces, Unsubscribes)

You are the executing agent running Stage 4 of the B2B Outreach System in this repository.

## Before you start

1. Read `AGENTS.md` in full, especially the human-confirmation list.
2. Read the operator's private config (created from `config/config.example.json`): bounce breaker thresholds, notification address. Where this prompt says "see config", use that file.
3. Read `docs/06-exclusions-and-failsafes.md` and `docs/05-followup-policy.md`.

## Inputs

- The sending mailbox (access method configured by the operator outside this repository).
- `data/leads.jsonl`, the send log, and the feedback log.

## Task

1. **Collect** everything new since the last inbox run: replies, bounce notifications, unsubscribe requests, out-of-office messages.
2. **Classify** each item and match it to a company by exact company identity and address, never by a partial name match:
   - Substantive reply (interest, questions, referral to another person)
   - Negative reply (not interested, wrong person with no referral)
   - Unsubscribe or do-not-contact request
   - Hard bounce (mailbox does not exist, domain dead)
   - Soft bounce (temporary failure)
   - Out of office (note the return date and any named alternate contact)
3. **Write back immediately:**
   - Hard bounce: label the address `invalid`, return the company to enrichment, note the pattern that produced the address as suspect.
   - Unsubscribe: add the address and company to the blocklist source data for the operator, remove from all future batches and follow-ups.
   - Any reply: remove the company from the automated follow-up pool and record the reply summary and date.
   - Out of office with an alternate contact: record the alternate as an unverified contact lead for Stage 2.
4. **Run the circuit-breaker check** on the updated numbers: bounces today and bounces among the most recent 20 sends against the thresholds in config. If either threshold is met, set the breaker state in the feedback log, stop any pending sending, and notify the operator at the notification address in config.
5. **Draft, do not send,** suggested replies to substantive replies for human review. Flag any reply that asks about price, stock, delivery dates, exclusivity, or payment terms: those always need human confirmation before any answer is sent (see `AGENTS.md`).

## Output

- Updated `data/leads.jsonl`, feedback log entries for every item, breaker state.
- An inbox report: counts by classification, companies needing human attention (with the reason), breaker status, and any draft replies awaiting review. If nothing arrived, report counts of zero briefly rather than staying silent about the breaker check.

## Hard limits

- Never send a reply yourself, and never quote a price or promise stock, dates, exclusivity, or terms in a draft presented as ready to send; mark such drafts "needs human confirmation".
- Never delete an unsubscribe or bounce record; they are safety data.
- Match companies by exact identity. When a match is ambiguous, list it for a human instead of guessing.
