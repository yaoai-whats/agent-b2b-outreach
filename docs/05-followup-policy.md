# 05 — Follow-Up Policy

Defaults below are the shipped policy. The operative values live in config (`followup_interval_days`, `followup_max`); change them there, not in letters or prompts.

## The policy in one paragraph

Wait **30 days** after the previous touch before following up with a company that has not replied. Send **at most 2 follow-ups** (the first letter plus up to 2 follow-ups is the whole sequence, roughly three months). Every follow-up must carry **genuinely new content**. After the second follow-up with no reply, stop permanently and mark the company accordingly.

## Rules

1. **Interval: 30 days.** Shorter intervals read as pressure and train spam filters and recipients alike to ignore you. Count from the last actual send date (first letter or previous follow-up), in the tracker's send log.
2. **Maximum: 2 follow-ups.** `followup_max` in config. The tracker (`scripts/build_tracker.py`) flags any company at the maximum as "sequence complete, do not contact".
3. **New content, every time.** Acceptable new content: a new product line or range extension with a photo or catalogue update, a concrete seasonal or market-relevant item, a specific answer to something on the recipient's public site, a relevant trade-show presence with an invitation to meet. Not acceptable: a bare reminder, a restatement of the first letter, or "just checking in" with nothing attached.
4. **Same thread discipline, fresh check first.** Before drafting, re-check the company: still in business, not acquired or rebranded, no reply or unsubscribe recorded since, not newly blocklisted or excluded. Any of those stops the follow-up.
5. **Replies end the sequence.** Any reply, positive, negative, or out-of-office with a named alternate, moves the company out of the automated follow-up pool. Substantive replies are handled by a human (see the confirmation list in `AGENTS.md`).
6. **Unsubscribes and hard bounces end everything.** No follow-up, no re-entry under a different address at the same company unless a human explicitly decides otherwise after a genuine business change.
7. **Follow-ups pass the same quality gate.** Same letter rules as first touches (`docs/04-letter-rules.md`), same recipient-label requirement (`docs/03-email-verification.md`), and they count toward the daily send cap (see config).
8. **Platform and partner contacts follow the same policy.** Channel partners are not an exception channel for extra touches.

## Tracker fields

The follow-up tracker (`scripts/build_tracker.py`) computes, per company: last touch date, follow-ups sent, next eligible date (last touch + interval from config), sequence status (in sequence, eligible, complete, stopped), and the reason for any stop. Trust the tracker over memory or inbox impressions.
