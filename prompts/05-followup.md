# Prompt 05 — Follow-Up (Stage 5: Send Earned Follow-Ups)

You are the executing agent running Stage 5 of the B2B Outreach System in this repository.

## Before you start

1. Read `AGENTS.md` in full.
2. Read the operator's private config (created from `config/config.example.json`): follow-up interval, follow-up maximum, daily send cap, sender identity. Where this prompt says "see config", use that file.
3. Read `docs/05-followup-policy.md` and `docs/04-letter-rules.md`.
4. Check the breaker state: if the circuit breaker is tripped, stop and report.

## Inputs

- `data/leads.jsonl` plus the send log, or the tracker produced by `scripts/build_tracker.py`.
- New-content material approved by the operator (new range, catalogue update, seasonal item, event invitation).

## Task

1. **Select eligible companies:** last touch at least the follow-up interval ago (see config), follow-ups sent below the maximum (see config), no reply, no unsubscribe, no hard bounce, not blocklisted or excluded on a fresh check.
2. **Re-verify each company** before drafting: still trading, not acquired or rebranded in a way that changes the contact, recipient address still labelled `hunter_valid` or `public_confirmed`.
3. **Attach genuinely new content** to every follow-up, chosen per company from the approved material: a new line relevant to their public range, a catalogue update, a seasonal item, or a specific response to something on their public site. If no relevant new content exists for a company, skip it this round. A bare reminder is not a follow-up.
4. **Build and gate** each follow-up with `scripts/letter_builder.py` and `scripts/quality_gate.py`, under the same letter rules as first touches (`docs/04-letter-rules.md`).
5. **Send with `scripts/send_mail.py --followup`** (with `--lead`, `--line`, and `--letter-file` for the drafted letter), within the shared daily cap (see config; first touches and follow-ups share the cap), spread across recipient-local business hours. The script is the send boundary for follow-ups: it re-validates eligibility at send time against the current records — no reply, unsubscribe, or bounce for the company or address, follow-ups sent below the maximum, last touch at least the interval ago — then applies the quality gate, the cap, and the breaker, and records the send in the send-state `followups` list itself. A refusal is final for that company this round; never route around it with another sending method. Afterwards write back the tracker fields on the lead row: follow-up number, date, new content used.
6. **Close out completed sequences:** companies reaching the follow-up maximum with no reply are marked sequence-complete and leave the pool permanently.

## Output

- Sent follow-ups, all gate-passed, each with recorded new content.
- A run report: eligible, sent, skipped (no new content, re-verification failed, excluded on recheck), sequences completed.

## Hard limits

- Never exceed the follow-up maximum or shorten the interval (see config), even if a company looks promising.
- Never follow up with a company that replied, unsubscribed, or hard-bounced, under any address.
- Follow-ups count toward the daily send cap and the bounce circuit breaker exactly like first touches.
- Never invent new content: product news in a follow-up must come from operator-approved material.
