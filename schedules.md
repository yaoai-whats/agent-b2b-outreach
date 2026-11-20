# Schedules — Suggested Cadence for the Five Stages

Frequencies below are starting suggestions for a small operation sending at the cap defined in config (see `daily_send_cap`). Adjust to your market, mailbox age, and reply volume. All times should be set in the recipient markets' business hours where the stage touches sending.

| Stage | Prompt | Suggested frequency | Notes |
|---|---|---|---|
| 1. Scan | `prompts/01-scan.md` | 2 to 4 times per week | Rotate market × buyer-category combinations (see config) so coverage widens instead of repeating the same pool. |
| 2. Enrich | `prompts/02-enrich.md` | Once per week | Work the highest tiers first. Respect the paid-verification budget rules in config. |
| 3. Batch | `prompts/03-batch.md` | Each business day | Prepare and send up to `daily_send_cap` (see config), spread across recipient-local business hours. Ramp a new mailbox up gradually over 2 to 3 weeks. |
| 4. Inbox | `prompts/04-inbox.md` | Twice per business day (morning and evening) | Classify replies, bounces, and unsubscribes; run the circuit-breaker check on every pass. |
| 5. Follow-up | `prompts/05-followup.md` | Once per week | Only companies past the follow-up interval (see config) with follow-ups remaining, and only with new content ready. |
| Review | (manual) | Once per month | Re-read reply and bounce patterns, adjust scoring weights and fit signals in config, prune dead sources. |

## Ramp-up guidance

- Week 1: send at roughly one third of `daily_send_cap`.
- Week 2: roughly two thirds.
- Week 3 onwards: full cap, provided the bounce circuit breaker (see `docs/06-exclusions-and-failsafes.md`) has not triggered.
- Any breaker trigger resets the ramp: fix the cause first, then restart from the week 1 level.
