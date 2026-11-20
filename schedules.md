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

## Registering scheduled jobs (for the executing agent)

Register schedules only after Step 0 onboarding is complete, one trial scan round has been shown to the operator, and the operator has explicitly agreed to continuous running.

- **Use your host platform's own scheduling capability** (for example Muse scheduled tasks, Codex automations, WorkBuddy scheduled tasks). Register **one job per stage**, not one combined job, so a failure in one stage never blocks the others. If your platform truly has no scheduling capability, use the fallback at the end of this section — never claim jobs exist when they do not.
- **Every job's instruction must be self-contained.** A scheduled run starts with no memory of earlier conversations, so each job text must carry everything it needs. Use this template, replacing the stage prompt and name:

  > Working directory: `<absolute path of this repository>`.
  > Read `AGENTS.md` in full, then `prompts/0X-<stage>.md`, then `config/config.json`. Credentials load automatically from the repo-root `.env` / environment; never print them.
  > Run that stage exactly as its prompt specifies, honouring every hard rule in `AGENTS.md`.
  > When finished, send the operator a short brief: what ran, the key numbers (found / stored / enriched / sent / replies / bounces), and anything that needs a human decision. If a circuit breaker or a hard rule stopped the stage, say so in the brief's first line.
  > Do not change config values, do not widen scope, and do not reply substantively to any prospect.

- **Brief every run.** The brief is how the operator supervises the system. Keep it to numbers and decisions; a run with nothing to report still sends one line saying so, unless the operator has asked for silence on empty runs.
- **Reference cadence.** The table above is a conservative starting point for a new mailbox. The deployment this system was extracted from runs Stage 1 every 4 hours, Stage 3 on business days, Stage 4 twice daily, Stage 2 weekly, and Stage 5 folded into the weekly pass — scale up towards that only after the ramp-up below completes without a breaker trip.

**Fallback when the host platform has no scheduler:** tell the operator plainly that automatic scheduling is not available in this tool, and instead leave the five stage prompts as one-line manual triggers ("run Stage 1", "run Stage 3", …) the operator can invoke at any time. Do not silently downgrade to advice, and do not describe manual triggers as scheduled jobs.

## Ramp-up guidance

- Week 1: send at roughly one third of `daily_send_cap`.
- Week 2: roughly two thirds.
- Week 3 onwards: full cap, provided the bounce circuit breaker (see `docs/06-exclusions-and-failsafes.md`) has not triggered.
- Any breaker trigger resets the ramp: fix the cause first, then restart from the week 1 level.
